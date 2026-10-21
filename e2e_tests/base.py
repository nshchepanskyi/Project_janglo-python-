"""
Спільна база для E2E-тестів на Selenium.

Піднімає живий сервер Django (`LiveServerTestCase`) і відкриває в ньому
справжній Chrome через Selenium. Усі E2E-кейси наслідують `SeleniumLiveTestCase`
і користуються готовими помічниками (ввід полів, очікування сторінок тощо).
"""
import os
import tempfile
from datetime import date, timedelta

from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.test import LiveServerTestCase

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

# 1×1 GIF — фото номера для E2E «Add Room»
TEST_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff"
    b"!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00"
    b"\x00\x02\x02D\x01\x00;"
)

# Анімації появи (fadeUp) роблять елементи «невидимими» для Selenium
# одразу після переходу, тож вимикаємо їх у вкладці — тест стає детермінованим.
DISABLE_ANIMATIONS_JS = """
(() => {
  const css = '*,*::before,*::after{animation:none !important;transition:none !important}';
  const inject = () => {
    const root = document.head || document.documentElement;
    if (!root) return false;
    const s = document.createElement('style');
    s.textContent = css;
    root.appendChild(s);
    return true;
  };
  if (!inject()) {
    new MutationObserver((_, obs) => {
      if (inject()) obs.disconnect();
    }).observe(document, {childList: true, subtree: true});
  }
})();
"""


class SeleniumLiveTestCase(LiveServerTestCase):
    """
    База для E2E: живий сервер Django + справжній браузер Chrome.

    Браузер відкривається **видимо** — тест сам заходить потрібні сторінки
    й клікає по кнопках, тож увесь сценарій видно на екрані.

    Налаштування через змінні оточення:
        SELENIUM_HEADLESS=1   — без вікна (CI, сервер без GUI)
        CHROMEDRIVER_PATH=... — шлях до chromedriver.exe, якщо Selenium Manager
                                не може завантажити драйвер сам
    """

    TIMEOUT = 15

    # Живий сервер віддає CSS/JS через staticfiles-finders (без collectstatic),
    # тож E2E перевіряє саме той фронтенд, який бачить користувач.
    static_handler = StaticFilesHandler

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        options = Options()
        if cls.headless():
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1440,1200")
        options.add_argument("--window-position=40,40")
        options.add_argument("--lang=en-US")
        options.add_argument("--start-maximized")

        driver_path = os.environ.get("CHROMEDRIVER_PATH")
        if driver_path:
            cls.driver = webdriver.Chrome(
                service=Service(executable_path=driver_path), options=options,
            )
        else:
            # Selenium Manager сам знаходить/качає відповідний chromedriver
            cls.driver = webdriver.Chrome(options=options)

        cls.driver.implicitly_wait(2)
        cls.wait = WebDriverWait(cls.driver, cls.TIMEOUT)
        cls.driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument", {"source": DISABLE_ANIMATIONS_JS},
        )
        # app.js «докручує» KPI-лічильники від нуля (requestAnimationFrame),
        # тож без reduced-motion тест читав би 0 замість підсумку.
        cls.driver.execute_cdp_cmd("Emulation.setEmulatedMedia", {
            "features": [{"name": "prefers-reduced-motion", "value": "reduce"}],
        })

        # Тимчасовий файл-фото для форми «Add Room»
        cls.photo_path = os.path.join(tempfile.gettempdir(), "grandstay_e2e_room.gif")
        with open(cls.photo_path, "wb") as fh:
            fh.write(TEST_GIF)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.driver.quit()
        finally:
            if getattr(cls, "photo_path", None) and os.path.exists(cls.photo_path):
                os.remove(cls.photo_path)
            super().tearDownClass()

    def setUp(self):
        super().setUp()
        # кожен тест стартує з чистою сесією браузера
        self.driver.delete_all_cookies()
        self.driver.get("about:blank")

    def run(self, result=None):
        """Обертаємо тест, щоб на падінні зберегти скріншот браузера.

        `unittest` у різних версіях Python повідомляє про помилку по-різному
        (result.addError / _Outcome), тож надійніше перехопити виняток
        прямо в обгортці тестового методу.
        """
        result = result if result is not None else self.defaultTestResult()
        original = getattr(self, self._testMethodName)

        def wrapped(*args, **kwargs):
            try:
                return original(*args, **kwargs)
            except BaseException:
                self._screenshot_on_failure()
                raise

        setattr(self, self._testMethodName, wrapped)
        try:
            return super().run(result)
        finally:
            setattr(self, self._testMethodName, original)

    def _screenshot_on_failure(self):
        """Зберігає скріншот поточного стану браузера у tmp."""
        path = os.path.join(
            tempfile.gettempdir(),
            f"grandstay_e2e_fail_{self.__class__.__name__}.png",
        )
        try:
            self.driver.save_screenshot(path)
        except WebDriverException:
            return
        print(f"\n[E2E] Скріншот падіння: {path}")

    # ---------- службові помічники ----------

    @staticmethod
    def headless():
        """Headless-режим лише за явного прохання (CI без GUI)."""
        return os.environ.get("SELENIUM_HEADLESS", "0").lower() in (
            "1", "true", "yes", "on",
        )

    def url(self, path=""):
        return f"{self.live_server_url}{path}"

    def open(self, path=""):
        """Відкриває сторінку застосунку в браузері."""
        self.driver.get(self.url(path))
        return self.driver

    def element(self, locator, timeout=None):
        wait = WebDriverWait(self.driver, timeout) if timeout else self.wait
        return wait.until(EC.presence_of_element_located(locator))

    def click(self, locator):
        el = self.wait.until(EC.element_to_be_clickable(locator))
        el.click()
        return el

    def fill(self, name, value):
        """Заповнює текстове поле імені name."""
        el = self.element((By.NAME, name))
        el.clear()
        el.send_keys(value)
        return el

    def set_date(self, name, value):
        """Ставить дату (ISO «YYYY-MM-DD») у поле input[type=date].

        Нативне поле дат Chromium приймає лише текст у локалі браузера
        (en-US → MM/DD/YYYY), тому значення ставимо через DOM — так тест
        не залежить від locale. Якщо підвантажиться кастомний календар
        (cal.js), він ховає нативне поле, але саме value з нього
        потрапляє у форму — тож сервер отримає правильні дати.
        """
        el = self.element((By.NAME, name))
        self.driver.execute_script(
            "arguments[0].value = arguments[1];"
            "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
            el, value,
        )
        return el

    def select(self, name, value):
        """Вибирає значення у списку (select) за іменем поля."""
        Select(self.element((By.NAME, name))).select_by_value(value)
        return self.element((By.NAME, name))

    def wait_for_url(self, fragment, timeout=None):
        """Чекає, поки адреса сторінки міститиме fragment."""
        wait = WebDriverWait(self.driver, timeout) if timeout else self.wait
        return wait.until(EC.url_contains(fragment))

    def wait_for_body(self, fragment, timeout=None):
        """Чекає, поки на сторінці зʼявиться потрібний текст.

        Найнадійніший спосіб зачекати на нову сторінку після переходу:
        орієнтир на контент, а не на URL чи readyState.
        """
        wait = WebDriverWait(self.driver, timeout) if timeout else self.wait

        def _check(driver):
            try:
                return fragment in driver.find_element(By.TAG_NAME, "body").text
            except WebDriverException:
                return False

        return wait.until(_check)

    def body_text(self):
        return self.driver.find_element(By.TAG_NAME, "body").text

    def wait_for_kpi(self, index, expected):
        """Чекає, поки KPI-показник (зліва) дорівнює очікуваному числу."""
        def _check(driver):
            els = driver.find_elements(By.CSS_SELECTOR, ".kpi.mini .kpi-value")
            if len(els) <= index:
                return False
            return els[index] if els[index].text.strip() == expected else False

        return self.wait.until(_check)

    def success_message(self):
        """Текст останнього успішного повідомлення (cls .msg.success)."""
        el = self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".msg.success"))
        )
        return el.text

    def login(self, username, password):
        """Входить через форму /login/."""
        self.open("/login/")
        self.fill("login", username)
        self.fill("password", password)
        self.click((By.CSS_SELECTOR, "form button[type=submit]"))

    # ---------- дрібні фіксури ----------

    @staticmethod
    def future_dates(nights=3, offset=14):
        """Повертає (check_in, check_out) у майбутньому — щоб не наштовхуватись
        на правило «минулі дати заблоковані» в календарі."""
        start = date.today() + timedelta(days=offset)
        return start, start + timedelta(days=nights)
