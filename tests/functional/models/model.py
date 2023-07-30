import pyvirtualdisplay
from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import tag
from django.urls import reverse
from django.utils import translation
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from osis_common.tests.functional.models.report import TestClassReport, TestFunctionReport, StaticReportHAndler, \
    TestAppReport


@tag("selenium")
class FunctionalTestCase(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = settings.FUNCT_TESTS_CONFIG if hasattr(settings, 'FUNCT_TESTS_CONFIG') else None
        super(FunctionalTestCase, cls).setUpClass()
        if cls.config.get('VIRTUAL_DISPLAY'):
            cls.virtual_display = pyvirtualdisplay.Display(size=(cls.config.get('DISPLAY_WIDTH'),
                                                                 cls.config.get('DISPLAY_HEIGHT')))
            cls.virtual_display.start()

        if cls.config.get('BROWSER') == 'FIREFOX':
            from selenium.webdriver.firefox.webdriver import WebDriver
            cls.selenium = WebDriver(executable_path=cls.config.get('GECKO_DRIVER'))

        cls.selenium.implicitly_wait(cls.config.get('DEFAULT_WAITING_TIME'))

        cls.selenium.set_window_size(cls.config.get('DISPLAY_WIDTH'), cls.config.get('DISPLAY_HEIGHT'))

        if cls.config.get('HTML_REPORTS'):
            cls.test_class_report = TestClassReport(name=cls.__name__)
            cls.test_class_report.doc = cls.__doc__
            cls.app_name = cls.__module__.split('.')[0].title()
            if not StaticReportHAndler.current_app_report:
                StaticReportHAndler.current_app_report = TestAppReport(cls.app_name)
            elif StaticReportHAndler.current_app_report.name != cls.app_name:
                StaticReportHAndler.current_app_report.succeeded = all(r.succeeded for r in StaticReportHAndler.current_app_report.test_class_reports)
                StaticReportHAndler.ran_tests.append(StaticReportHAndler.current_app_report)
                StaticReportHAndler.current_app_report = TestAppReport(cls.app_name)

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        if cls.config.get('VIRTUAL_DISPLAY'):
            cls.virtual_display.stop()
        if cls.config.get('HTML_REPORTS'):
            cls.test_class_report.succeeded = all(r.succeeded for r in cls.test_class_report.test_function_reports)
            StaticReportHAndler.current_app_report.test_class_reports.append(cls.test_class_report)
        super(FunctionalTestCase, cls).tearDownClass()

    @staticmethod
    def get_localized_message(message, language):
        cur_language = translation.get_language()
        translation.activate(language)
        translated_message = translation.gettext(message)
        translation.activate(cur_language)
        return translated_message

    def tearDown(self):
        super(FunctionalTestCase, self).tearDown()
        if self.config.get('HTML_REPORTS'):
            self.add_function_to_class_report()

    def setUp(self):
        super(FunctionalTestCase, self).setUp()
        self.function_report = TestFunctionReport()

    def add_function_to_class_report(self):
        self.test_class_report.test_function_reports.append(self.function_report)

    def open_url_by_name(self, url_name, kwargs=None):
        self.selenium.get(self.get_link_href_by_url_name(url_name, kwargs=kwargs))

    def get_link_href_by_url_name(self, url_name, kwargs=None):
        if not kwargs:
            kwargs = {}
        return self.live_server_url + reverse(url_name, kwargs=kwargs)

    def fill_element_by_id(self, element_id, value):
        element = self.selenium.find_element_by_id(element_id)
        element.clear()
        element.send_keys(value)

    def click_element_by_id(self, element_id):
        element = self.selenium.find_element_by_id(element_id)
        element.click()

    def login(self, username, password=None, login_page_name='login'):
        if password is None:
            password = "password123"
        self.open_url_by_name(login_page_name)
        self.fill_element_by_id('id_username', username)
        self.fill_element_by_id('id_password', password)
        self.click_element_by_id('post_login_btn')

    def check_page_title(self, expected_title):
        self.assertEqual(self.selenium.title, expected_title)

    def check_page_contains_string(self, expected_string):
        self.assertTrue(expected_string in self.selenium.page_source)

    def check_page_not_contains_string(self, expected_string):
        self.assertFalse(expected_string in self.selenium.page_source)

    def check_page_contains_links(self, expected_links_ref):
        for link_ref in expected_links_ref:
            self.selenium.find_element_by_css_selector('[href^={}'.format(link_ref))

    def check_page_contains_ids(self, ids):
        for id in ids:
                self.selenium.find_element_by_id(id)

    def check_page_not_contains_ids(self, ids):
        for id in ids:
            with self.assertRaises(NoSuchElementException):
                self.selenium.find_element_by_id(id)

    def wait_until_element_appear(self, element_id, timeout=10):
        WebDriverWait(self.selenium, timeout).until(EC.presence_of_element_located((By.ID, element_id)))

    def wait_until_tabs_open(self, count_tabs=2, timeout=10):
        WebDriverWait(self.selenium, timeout).until(EC.number_of_windows_to_be(count_tabs))

    def wait_until_title_is(self, title, timeout=10):
        WebDriverWait(self.selenium, timeout).until(EC.title_is(title))
