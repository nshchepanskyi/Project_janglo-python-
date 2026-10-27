import os

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from pages.auth_page import AuthPage
from utils.config import WAIT_SECONDS


CASE_ID = "GRNDST-0003"
CASE_TITLE = "Authorization with valid credentials"


@pytest.mark.case_id(CASE_ID)
def test_grndst_0003_authorization_with_valid_credentials(driver, base_url):
    email = os.getenv("TEST_LOGIN_USERNAME")
    password = os.getenv("TEST_LOGIN_PASSWORD")
    if not email or not password:
        pytest.skip("Set TEST_LOGIN_USERNAME and TEST_LOGIN_PASSWORD in tests/.env.")

    auth = AuthPage(driver, base_url, WAIT_SECONDS)
    auth.open("/")
    WebDriverWait(driver, WAIT_SECONDS).until(EC.title_contains("Find your next stay"))
    assert "Find your next stay" in driver.title, (
        f"Expected home page title for {CASE_ID}; actual title: {driver.title!r}"
    )
    auth.click_and_continue((By.LINK_TEXT, "Sign In"))
    login_heading = auth.visible((By.CSS_SELECTOR, ".login-card h1"))
    assert "Welcome back" in login_heading.text, (
        f"Expected login page after Sign In for {CASE_ID}; URL: {driver.current_url}"
    )
    auth.visible((By.NAME, "login")).send_keys(email)
    auth.visible((By.NAME, "password")).send_keys(password)
    auth.click_and_continue((By.CSS_SELECTOR, "form button[type='submit']"))
    WebDriverWait(driver, WAIT_SECONDS).until(EC.visibility_of_element_located(
        (By.CSS_SELECTOR, ".profile-account-email")
    ))
    profile_email = driver.find_element(By.CSS_SELECTOR, ".profile-account-email").text.strip()
    assert profile_email.lower() == email.lower(), (
        f"Expected signed-in profile for {email} ({CASE_ID}); "
        f"actual profile email: {profile_email!r}, URL: {driver.current_url}"
    )
