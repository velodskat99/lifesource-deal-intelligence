import html as html_lib
import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from urllib.parse import unquote_plus, urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup


HMART_TEXAS_WEEKLY_AD_URL = "https://www.hmart.com/weekly-ads-texas#/"
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WeeklyAdInspection:
    source_url: str
    fingerprint: str
    assets: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class HmartTexasWeeklyAdSource:
    store = "hmart"
    region = "texas"
    source_type = "weekly_ad"
    source_url = HMART_TEXAS_WEEKLY_AD_URL

    def __init__(self, client: httpx.Client | None = None):
        self.client = client or httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            },
        )

    def fetch_html(self) -> str:
        response = self.client.get(self.source_url)
        response.raise_for_status()
        return response.text

    def check(self) -> WeeklyAdInspection:
        inspection = self.inspect_html(self.fetch_html())
        if inspection.assets:
            return inspection

        rendered_html = self.fetch_rendered_html()
        if not rendered_html:
            return inspection

        rendered = self.inspect_html(rendered_html)
        if not rendered.assets:
            return inspection
        return WeeklyAdInspection(
            source_url=rendered.source_url,
            fingerprint=rendered.fingerprint,
            assets=rendered.assets,
            metadata={
                **rendered.metadata,
                "strategy": "rendered_weekly_ad_assets",
            },
            warnings=[],
        )

    def fetch_rendered_html(self) -> str | None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return None

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 2200})
                page.goto(self.source_url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(5000)
                html = page.content()
                browser.close()
            return html
        except Exception as exc:
            logger.warning("[hmart-weekly] Rendered page fetch failed: %s", exc)
            return None

    def inspect_html(self, html: str) -> WeeklyAdInspection:
        soup = BeautifulSoup(html, "html.parser")
        assets = self._extract_assets(soup, html)
        date_labels = self._extract_date_labels(soup.get_text(" ", strip=True))

        if assets:
            strategy = "weekly_ad_assets"
            fingerprint_parts = [*assets, *date_labels]
            warnings: list[str] = []
        else:
            strategy = "raw_html"
            fingerprint_parts = [self._normalize_text(html)]
            warnings = ["No weekly-ad assets found; fingerprint uses raw HTML."]

        return WeeklyAdInspection(
            source_url=self.source_url,
            fingerprint=self.fingerprint(fingerprint_parts),
            assets=assets,
            metadata={
                "strategy": strategy,
                "date_labels": date_labels,
            },
            warnings=warnings,
        )

    def fingerprint(self, parts: list[str]) -> str:
        payload = json.dumps(parts, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _extract_assets(self, soup: BeautifulSoup, html: str) -> list[str]:
        candidates: list[str] = []
        for tag in soup.find_all(["a", "img", "script", "source"]):
            for attr in ("href", "src", "data-src", "data-original", "content"):
                value = tag.get(attr)
                if value:
                    candidates.append((value, tag))

        candidates.extend(
            (match.group(0), None)
            for match in re.finditer(
                r"https?://[^\s\"']+(?:weekly-ads|weekly|ads)[^\s\"']+",
                html,
                re.IGNORECASE,
            )
        )

        normalized = []
        seen = set()
        for candidate, tag in candidates:
            candidate = html_lib.unescape(candidate)
            if not self._looks_like_weekly_ad_asset(candidate, tag=tag):
                continue
            url = urljoin("https://www.hmart.com", candidate)
            if url not in seen:
                seen.add(url)
                normalized.append(url)
        return normalized

    def _looks_like_weekly_ad_asset(self, value: str, tag=None) -> bool:
        lower = unquote_plus(value.lower())
        split = urlsplit(lower)
        path = split.path
        host = split.netloc
        blocked_tokens = (
            "assets-builder",
            "/footer/",
            "logo",
            "icon-",
            "bt-app",
            "instagram",
            "tiktok",
            "threads",
        )
        if any(token in lower for token in blocked_tokens):
            return False
        if self._tag_identifies_weekly_ad(tag) and self._is_allowed_file_manager_asset(host, path):
            return True

        weekly_path_tokens = (
            "/weekly-ads/",
            "/weekly-ad/",
            "/weekly_ads/",
            "/weekly/",
            "/media/weekly-ads/",
        )
        if not any(token in path for token in weekly_path_tokens):
            return False

        return any(path.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".pdf"))

    def _tag_identifies_weekly_ad(self, tag) -> bool:
        if tag is None:
            return False
        text = " ".join(
            str(tag.get(attr, ""))
            for attr in ("alt", "aria-label", "title")
        ).lower()
        return "weekly ad" in text or "weekly sales" in text

    def _is_allowed_file_manager_asset(self, host: str, path: str) -> bool:
        allowed_hosts = ("hmart.com", "www.hmart.com", "hmartus.vtexassets.com")
        if host not in allowed_hosts:
            return False
        if "vtex.file-manager-graphql/images/" not in path:
            return False
        return any(path.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".pdf"))

    def _extract_date_labels(self, text: str) -> list[str]:
        labels = re.findall(
            r"(?:Valid|Sale|Sales)?\s*[A-Z][a-z]{2,8}\s+\d{1,2}\s*[-–]\s*[A-Z]?[a-z]*\s*\d{1,2},?\s*\d{4}",
            text,
        )
        return [self._normalize_text(label) for label in labels]

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()
