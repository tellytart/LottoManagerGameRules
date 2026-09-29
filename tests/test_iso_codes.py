"""Tests for scripts/iso_codes.py: the ISO 4217 currency and ISO 3166-1 country tables.

The currency table must match the app's Core table (ISOCurrency.swift in the LottoManager
repo) code for code and exponent for exponent, so these tests pin its shape and a few
known entries. The country table is the officially assigned ISO 3166-1 alpha-2 codes.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import iso_codes  # noqa: E402  (path set up just above)


class CurrencyTableTests(unittest.TestCase):
    def test_every_exponent_is_0_2_or_3(self):
        self.assertEqual(set(iso_codes.CURRENCY_EXPONENTS.values()), {0, 2, 3})

    def test_known_exponents(self):
        for code, exponent in (("GBP", 2), ("EUR", 2), ("USD", 2), ("JPY", 0), ("KRW", 0),
                               ("KWD", 3), ("BHD", 3), ("TND", 3)):
            with self.subTest(code=code):
                self.assertEqual(iso_codes.CURRENCY_EXPONENTS[code], exponent)

    def test_funds_metals_testing_and_no_currency_codes_are_left_out(self):
        # As in the app's table: no lottery is played in these, and CLF and UYW have exponent 4.
        for code in ("CLF", "UYW", "XAU", "XAG", "XTS", "XXX", "XDR", "USN", "BOV"):
            with self.subTest(code=code):
                self.assertNotIn(code, iso_codes.CURRENCY_EXPONENTS)

    def test_codes_are_three_upper_case_letters(self):
        for code in iso_codes.CURRENCY_EXPONENTS:
            self.assertRegex(code, r"^[A-Z]{3}$")


class CountryTableTests(unittest.TestCase):
    def test_holds_the_249_officially_assigned_codes(self):
        self.assertEqual(len(iso_codes.COUNTRY_CODES), 249)
        for code in iso_codes.COUNTRY_CODES:
            self.assertRegex(code, r"^[A-Z]{2}$")

    def test_real_countries_are_in(self):
        for code in ("GB", "IE", "US", "JP", "DE", "AX", "SS", "BQ"):
            with self.subTest(code=code):
                self.assertIn(code, iso_codes.COUNTRY_CODES)

    def test_reserved_and_user_assigned_codes_are_out(self):
        # UK is only "exceptionally reserved" (the code is GB); EU likewise; XK (Kosovo) is
        # user-assigned; AN (Netherlands Antilles) was withdrawn.
        for code in ("UK", "EU", "XK", "AN", "ZZ"):
            with self.subTest(code=code):
                self.assertNotIn(code, iso_codes.COUNTRY_CODES)


if __name__ == "__main__":
    unittest.main()
