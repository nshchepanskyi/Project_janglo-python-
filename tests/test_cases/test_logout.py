import os
import re

import pytest
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from pages.auth_page import AuthPage
from utils.config import WAIT_SECONDS


CASE_ID = "GRNDST-0002"
CASE_TITLE = "Signing out from the webpage"
LOGOUT_BUTTON = (By.CSS_SELECTOR, "form[action$='/logout/'] button")
LOGIN_HEADING = (By.CSS_SELECTOR, ".login-card h1")


def visible_heading_containing(text):
    def find_heading(driver):
        return next(
            (
                heading
                for heading in driver.find_elements(By.TAG_NAME, "h1")
                if heading.is_displayed() and text in heading.text
            ),
            False,
        )

    return find_heading


def logout_result(driver):
    try:
        if any(heading.is_displayed() for heading in driver.find_elements(*LOGIN_HEADING)):
            return "login", None
        body = driver.find_element(By.TAG_NAME, "body").text
    except WebDriverException:
        return "browser_closed", None

    if "502 bad gateway" in body.lower() or "http error 502" in body.lower():
        match = re.search(r"Request ID:\s*([A-Za-z0-9-]+)", body, re.IGNORECASE)
        return "gateway_502", match.group(1) if match else None
    return False


@pytest.mark.case_id(CASE_ID)
def test_grndst_0002_sign_out_and_browser_back_stays_logged_out(driver, base_url):
    username = os.getenv("TEST_LOGIN_USERNAME")
    password = os.getenv("TEST_LOGIN_PASSWORD")
    if not username or not password:
        pytest.skip(
            "Set TEST_LOGIN_USERNAME and TEST_LOGIN_PASSWORD in tests/.env "
            "to use a dedicated test account."
        )

    auth = AuthPage(driver, base_url, WAIT_SECONDS)
    auth.login(username, password)
    WebDriverWait(driver, WAIT_SECONDS).until(
        EC.presence_of_element_located(LOGOUT_BUTTON),
        message=f"Login did not establish an authenticated session for {CASE_ID}",
    )

    # Excel precondition: the authenticated user is on the home page.
    auth.open("/")
    home_heading = WebDriverWait(driver, WAIT_SECONDS).until(
        visible_heading_containing("Find your next stay")
    )
    assert "Find your next stay" in home_heading.text, (
        f"Expected the home page before logout for {CASE_ID}; URL: {driver.current_url}"
    )

    logout_button = WebDriverWait(driver, WAIT_SECONDS).until(
        EC.element_to_be_clickable(LOGOUT_BUTTON)
    )
    assert logout_button.text.strip() == "Logout", (
        f"Expected Logout control for {CASE_ID}; found {logout_button.text!r}"
    )
    auth.click_and_continue(LOGOUT_BUTTON)

    result, request_id = WebDriverWait(driver, WAIT_SECONDS).until(
        logout_result,
        message=f"Logout did not display the login page for {CASE_ID}",
    )
    if result == "gateway_502":
        pytest.fail(
            "Render returned 502 after Logout; check the web-service logs"
            + (f" (Request ID: {request_id})" if request_id else ".")
        )
    if result == "browser_closed":
        pytest.fail(f"Browser window closed before the logout redirect completed for {CASE_ID}")

    login_heading = driver.find_element(*LOGIN_HEADING)
    assert "Welcome back" in login_heading.text, (
        f"Expected the login page after logout for {CASE_ID}; URL: {driver.current_url}"
    )
    assert not driver.find_elements(*LOGOUT_BUTTON), (
        f"Logout should remove authenticated controls for {CASE_ID}; URL: {driver.current_url}"
    )

    # Also verify that public navigation and browser Back stay anonymous.
    auth.click_and_continue((By.LINK_TEXT, "Home"))
    home_heading = WebDriverWait(driver, WAIT_SECONDS).until(
        visible_heading_containing("Find your next stay")
    )
    assert "Find your next stay" in home_heading.text, (
        f"Home should remain public after logout for {CASE_ID}; URL: {driver.current_url}"
    )
    assert driver.find_elements(By.LINK_TEXT, "Sign In"), (
        f"Anonymous home should show Sign In for {CASE_ID}; URL: {driver.current_url}"
    )
    assert not driver.find_elements(*LOGOUT_BUTTON), (
        f"Home restored authenticated controls after logout for {CASE_ID}; "
        f"URL: {driver.current_url}"
    )

    auth.back()
    WebDriverWait(driver, WAIT_SECONDS).until(
        EC.visibility_of_element_located(LOGIN_HEADING),
        message=f"Browser Back should return to the anonymous login page for {CASE_ID}",
    )
    assert not driver.find_elements(*LOGOUT_BUTTON), (
        f"Browser Back restored authenticated controls for {CASE_ID}; URL: {driver.current_url}"
    )
