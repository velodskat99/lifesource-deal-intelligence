"""Entry point: python -m lifesource.daily runs the daily scraping job."""
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

from lifesource.daily.job import run_daily_job


def main():
    result = run_daily_job()
    print(
        f"Daily job complete: {result['deals_found']} deals found, "
        f"{result['deals_above_threshold']} above threshold"
    )
    if result["errors"]:
        print(f"Errors: {result['errors']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
