"""Gas price fetcher using GasBuddy data."""
import logging
import re

from bs4 import BeautifulSoup

from lifesource.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# Example zone. Override with your own GasBuddy city URL for real use.
DEFAULT_ZONES = {
    "example": "https://www.gasbuddy.com/gasprices",
}


class GasStation:
    def __init__(self, name: str, address: str, regular_price: float,
                 lat: float = 0, lng: float = 0, zone: str = "example"):
        self.name = name
        self.address = address
        self.regular_price = regular_price
        self.lat = lat
        self.lng = lng
        self.zone = zone


class GasBuddyScraper(BaseScraper):
    store_name = "gasbuddy"

    def __init__(self, zones: dict[str, str] | None = None, **kwargs):
        super().__init__(**kwargs)
        self.zones = zones or DEFAULT_ZONES

    def get_url(self) -> str:
        return list(self.zones.values())[0]

    def scrape_all_zones(self) -> list[GasStation]:
        """Scrape gas prices for all configured zones."""
        all_stations = []
        for zone_name, url in self.zones.items():
            try:
                html = self.fetch(url)
                stations = self.parse_stations(html, zone_name)
                all_stations.extend(stations)
                logger.info(f"[gasbuddy] {zone_name}: {len(stations)} stations")
            except Exception as e:
                logger.warning(f"[gasbuddy] Failed to fetch {zone_name}: {e}")
        return all_stations

    def parse(self, html: str) -> list:
        """Parse is not used directly -- use parse_stations instead."""
        return []

    def parse_stations(self, html: str, zone: str = "example") -> list[GasStation]:
        """Parse GasBuddy page to extract gas station prices."""
        soup = BeautifulSoup(html, "html.parser")
        stations = []

        # GasBuddy uses various CSS classes for station listings
        # Look for price/station patterns in the HTML
        for container in soup.find_all(["div", "li"], class_=re.compile(
            r"station|GenericStationListItem|StationDisplay", re.IGNORECASE
        )):
            name_el = container.find(class_=re.compile(r"StationName|header__Station|name", re.I))
            price_el = container.find(class_=re.compile(r"Price|price|StationPri", re.I))
            addr_el = container.find(class_=re.compile(r"address|Address|location", re.I))

            if not price_el:
                continue

            name = name_el.get_text(strip=True) if name_el else "Unknown"
            address = addr_el.get_text(strip=True) if addr_el else ""

            # Extract price (format: $X.XX or X.XX)
            price_text = price_el.get_text(strip=True)
            price_match = re.search(r'\$?(\d+\.\d{2})', price_text)
            if not price_match:
                continue

            price = float(price_match.group(1))

            stations.append(GasStation(
                name=name,
                address=address,
                regular_price=price,
                zone=zone,
            ))

        # Fallback: search for price patterns in text
        if not stations:
            for text_block in soup.find_all(string=re.compile(r'\$\d+\.\d{2}')):
                parent = text_block.parent
                if parent:
                    price_match = re.search(r'\$(\d+\.\d{2})', str(text_block))
                    if price_match:
                        stations.append(GasStation(
                            name="Station",
                            address="",
                            regular_price=float(price_match.group(1)),
                            zone=zone,
                        ))

        return stations[:20]  # Limit to 20 stations per zone
