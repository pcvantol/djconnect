"""Precision-preserving authored date presentation; original source stays immutable."""
import unittest
from importlib import import_module
from tests import test_session_runtime as runtime_fixture


class SpeechDateExpressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        runtime_fixture.SessionRuntimeManagerTest.setUpClass()
        cls.expression = import_module("custom_components.djconnect.context_expression")

    @classmethod
    def tearDownClass(cls):
        runtime_fixture.SessionRuntimeManagerTest.tearDownClass()

    def test_year_month_day_are_localized_without_inventing_precision(self):
        expected = {
            "en": ("2001", "April 2001", "2 April 2001", "on 2 April 2001"),
            "nl": ("2001", "april 2001", "2 april 2001", "op 2 april 2001"),
            "de": ("2001", "April 2001", "2. April 2001", "am 2. April 2001"),
            "fr": ("2001", "avril 2001", "2 avril 2001", "le 2 avril 2001"),
            "es": ("2001", "abril de 2001", "2 de abril de 2001", "el 2 de abril de 2001"),
        }
        for language, values in expected.items():
            with self.subTest(language=language):
                actual = [self.expression.human_date(value, precision, language)
                          for value, precision in (("2001", "year"), ("2001-04", "month"), ("2001-04-02", "day"))]
                self.assertEqual(actual, list(values[:3]))
                self.assertEqual(self.expression.date_phrase("2001-04-02", "day", language), values[3])
        self.assertEqual(self.expression.human_date("2001-04-01", "day", "fr"), "1er avril 2001")

    def test_bad_dates_precision_mismatch_and_unsupported_locale_fail_closed(self):
        for value, precision, language in (("2001", "day", "en"), ("2001-04-02", "year", "nl"),
                                           ("2001-02-29", "day", "en"), ("2001-13", "month", "fr"),
                                           ("2001", "year", "it")):
            self.assertIsNone(self.expression.human_date(value, precision, language))
