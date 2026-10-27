import os
import http.client
from urllib.parse import urlsplit

import pytest
import pytest_html
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService

from utils.config import BASE_URL, BROWSER, HEADLESS, WAIT_SECONDS


def pytest_addoption(parser):
    parser.addoption("--base-url", default=None, help="Override BASE_URL")


@pytest.fixture(scope="session")
def base_url(request):
    value = request.config.getoption("--base-url") or BASE_URL
    deadline = __import__("time").monotonic() + int(os.getenv("STARTUP_TIMEOUT", "90"))
    last_error = None
    parsed = urlsplit(value)
    connection_type = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    while __import__("time").monotonic() < deadline:
        connection = connection_type(parsed.hostname, port, timeout=3)
        try:
            connection.request("GET", (parsed.path.rstrip("/") + "/") or "/")
            response = connection.getresponse()
            response.read()
            if response.status < 500:
                return value
            last_error = f"HTTP {response.status}"
        except OSError as exc:
            last_error = exc
        finally:
            connection.close()
        __import__("time").sleep(2)
    pytest.exit(
        f"GrandStay is not responding at {value} after the bounded startup wait. "
        f"Last error: {last_error}", returncode=2
    )


@pytest.fixture
def driver(request, base_url):
    browser = BROWSER
    if browser == "chrome":
        options = ChromeOptions()
        # UI readiness is checked with explicit waits; do not block on media
        # or other nonessential resources during navigation.
        options.page_load_strategy = "eager"
        if HEADLESS:
            options.add_argument("--headless=new")
        options.add_argument("--window-size=1365,1000")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        path = os.getenv("CHROMEDRIVER_PATH")
        instance = webdriver.Chrome(service=ChromeService(path) if path else None,
                                    options=options)
    elif browser == "firefox":
        options = FirefoxOptions()
        options.page_load_strategy = "eager"
        if HEADLESS:
            options.add_argument("-headless")
        path = os.getenv("GECKODRIVER_PATH")
        instance = webdriver.Firefox(service=FirefoxService(path) if path else None,
                                     options=options)
    else:
        pytest.fail(f"Unsupported BROWSER={browser!r}; use chrome or firefox")
    instance.set_page_load_timeout(WAIT_SECONDS)
    request.node._selenium_driver = instance
    yield instance
    instance.quit()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    case_marker = item.get_closest_marker("case_id")
    if case_marker:
        case_id = str(case_marker.args[0])
        case_title = getattr(item.module, "CASE_TITLE", "(title unavailable)")
        report.sections.append(("Excel test case", f"{case_id} — {case_title}"))
    if report.when == "call" and report.failed:
        driver = getattr(item, "_selenium_driver", None)
        if driver:
            path = os.path.abspath(os.path.join("tests", "reports", "screenshots",
                                                 item.name + ".png"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            try:
                driver.save_screenshot(path)
                report.sections.append(("Failure screenshot", path))
                report.extras = getattr(report, "extras", [])
                report.extras.append(pytest_html.extras.image(path, name="Failure screenshot"))
            except Exception as exc:  # browser may already be gone
                report.sections.append(("Screenshot error", str(exc)))


def pytest_html_report_title(report):
    report.title = "GrandStay Selenium UI test report"
