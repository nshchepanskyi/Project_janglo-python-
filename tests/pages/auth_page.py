from selenium.webdriver.common.by import By

from .base_page import BasePage


class AuthPage(BasePage):
    LOGIN = (By.NAME, "login")
    PASSWORD = (By.NAME, "password")
    USERNAME = (By.NAME, "username")
    EMAIL = (By.NAME, "email")
    CONFIRM = (By.NAME, "confirm")
    CODE = (By.NAME, "code")

    def login(self, username, password):
        self.open("/login/")
        self.visible(self.LOGIN).send_keys(username)
        self.visible(self.PASSWORD).send_keys(password)
        self.click_and_continue((By.CSS_SELECTOR, "form button[type='submit']"))

    def register(self, username, email, password):
        self.open("/register/")
        for locator, value in ((self.USERNAME, username), (self.EMAIL, email),
                               (self.PASSWORD, password), (self.CONFIRM, password)):
            self.visible(locator).send_keys(value)
        self.click_and_continue((By.CSS_SELECTOR, "form button[type='submit']"))
