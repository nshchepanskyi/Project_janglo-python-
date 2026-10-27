from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class BasePage:
    def __init__(self, driver, base_url, timeout):
        self.driver = driver
        self.base_url = base_url
        self.wait = WebDriverWait(driver, timeout)

    def open(self, path="/"):
        try:
            self.driver.get(f"{self.base_url}{path}")
        except TimeoutException:
            self.driver.execute_script("window.stop()")
        return self

    def back(self):
        try:
            self.driver.back()
        except TimeoutException:
            self.driver.execute_script("window.stop()")
        return self

    def visible(self, locator):
        return self.wait.until(EC.visibility_of_element_located(locator))

    def clickable(self, locator):
        return self.wait.until(EC.element_to_be_clickable(locator))

    def click_and_continue(self, locator):
        try:
            self.clickable(locator).click()
        except TimeoutException:
            self.driver.execute_script("window.stop()")
        return self
