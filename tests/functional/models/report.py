import datetime
import os
import traceback
from functools import wraps

from django.conf import settings
from django.template.loader import render_to_string

config = settings.FUNCT_TESTS_CONFIG if hasattr(settings, 'FUNCT_TESTS_CONFIG') else None


class StaticReportHAndler:
    succeeded = True
    ran_tests = []
    current_app_report = None


class TestAppReport:
    def __init__(self, name=None):
        self.name = name
        self.succeeded = True
        self.test_class_reports = []
        self.doc = None


class TestClassReport:
    def __init__(self, name=None):
        self.name = name
        self.succeeded = True
        self.test_function_reports = []
        self.doc = None


class TestFunctionReport:

    def __init__(self, name=None):
        self.name = name
        self.succeeded = True
        self.reason = None
        self.traceback = None
        self.screenshot = None
        self.doc = None


def can_be_reported(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if config and config.get('HTML_REPORTS'):
            self.function_report.name = func.__name__
            self.function_report.doc = func.__doc__
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            if config and config.get('HTML_REPORTS'):
                StaticReportHAndler.succeeded = False
                self.function_report.succeeded = False
                self.function_report.reason = '{} - {}'.format(type(e).__name__, str(e))
                self.function_report.traceback = traceback.format_exc()
            if config and config.get('TAKE_SCREENSHOTS'):
                self.function_report.screenshot = __take_screenshot(self.selenium, func.__name__)
            raise
    return wrapper


def __take_screenshot(selenium_driver, name):
    date_str = "{:%d_%m_%Y_%H_%M}".format(datetime.datetime.today())
    complete_path = "{screenshot_dir}/{name}_{date}.png".format(screenshot_dir=config.get('SCREENSHOTS_DIR'),
                                                                name="".join(name.replace("'", "").split()),
                                                                date=date_str)
    selenium_driver.save_screenshot(complete_path)
    return complete_path


def make_html_report():
    if StaticReportHAndler.current_app_report:
        StaticReportHAndler.current_app_report.succeeded = all(r.succeeded for r in StaticReportHAndler.current_app_report.test_class_reports)
        StaticReportHAndler.ran_tests.append(StaticReportHAndler.current_app_report)
    StaticReportHAndler.succeeded = all(r.succeeded for r in StaticReportHAndler.ran_tests)
    now = datetime.datetime.today()
    data = {
        'static_dir': config.get('HTML_REPORTS_STATIC_DIR'),
        'date_time': '{:%d-%m-%Y %H:%M}'.format(now),
        'tested_apps': StaticReportHAndler.ran_tests
    }

    content = render_to_string('functional_tests_report.html', data)
    file_name = '.'.join(['TestsResults', '{:%d_%m_%Y_%H_%M}'.format(now), 'html'])
    file_path = os.path.join(config.get('HTML_REPORTS_DIR'), file_name)
    with open(file_path, 'w') as file:
        file.write(content)
