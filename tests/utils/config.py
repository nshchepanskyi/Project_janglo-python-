"""Runtime configuration for Selenium UI tests."""
import os
from urllib.parse import urlparse
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
BROWSER = os.getenv("BROWSER", "chrome").lower()
HEADLESS = os.getenv("HEADLESS", "false").lower() in {"1", "true", "yes", "on"}
WAIT_SECONDS = int(os.getenv("WAIT_SECONDS", "60"))
ALLOW_MUTATING_TESTS = os.getenv("ALLOW_MUTATING_TESTS", "false").lower() in {
    "1", "true", "yes", "on"
}


def is_known_production_url(url=BASE_URL):
    return (urlparse(url).hostname or "").lower() in {
        "grandstay.top", "www.grandstay.top"
    }
