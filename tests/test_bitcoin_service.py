import unittest
from unittest.mock import patch
import requests

from core.services import BitcoinAPIService


class FakeResp:
    def __init__(self, json_data=None, status=200):
        self._json = json_data or {}
        self.status = status

    def raise_for_status(self):
        if self.status >= 400:
            raise requests.exceptions.HTTPError('err')

    def json(self):
        return self._json


class BitcoinAPIServiceTests(unittest.TestCase):
    def test_get_price_success(self):
        svc = BitcoinAPIService()

        def fake_get(url, params=None, timeout=None):
            return FakeResp({'bitcoin': {'eur': 60000.5}}, 200)

        orig = requests.get
        try:
            requests.get = fake_get
            res = svc.get_price()
            self.assertTrue(res.is_success)
            self.assertEqual(res.data, 60000.5)
        finally:
            requests.get = orig

    def test_fallback_after_http_error_or_timeout(self):
        for failure in (FakeResp(status=403), FakeResp(status=429),
                        requests.exceptions.Timeout("timeout")):
            with self.subTest(failure=failure), patch(
                "core.services.requests.get",
                side_effect=[failure, FakeResp({"data": {"amount": "60001.25", "currency": "EUR"}})],
            ) as get:
                result = BitcoinAPIService().get_price()
                self.assertTrue(result.is_success)
                self.assertEqual(result.data, 60001.25)
                self.assertIn("Coinbase", result.message)
                self.assertEqual(get.call_args.args[0], "https://api.coinbase.com/v2/prices/BTC-EUR/spot")
                self.assertEqual(get.call_args.kwargs["timeout"], 10)

    def test_invalid_primary_price_uses_fallback(self):
        for price in (None, True, 0, -1, "NaN", "Infinity", [], "invalid"):
            with self.subTest(price=price), patch(
                "core.services.requests.get",
                side_effect=[FakeResp({"bitcoin": {"eur": price}}),
                             FakeResp({"data": {"amount": "60000", "currency": "EUR"}})],
            ):
                result = BitcoinAPIService().get_price()
                self.assertTrue(result.is_success)
                self.assertEqual(result.data, 60000)

    def test_invalid_json_uses_fallback(self):
        with patch("core.services.requests.get", side_effect=[
            requests.exceptions.JSONDecodeError("invalid", "x", 0),
            FakeResp({"data": {"amount": "60000", "currency": "EUR"}}),
        ]):
            self.assertTrue(BitcoinAPIService().get_price().is_success)

    def test_rejects_wrong_currency_and_invalid_fallback(self):
        for quote in ({"amount": "60000", "currency": "USD"},
                      {"amount": "NaN", "currency": "EUR"}, {}, None):
            with self.subTest(quote=quote), patch("core.services.requests.get", side_effect=[
                FakeResp(status=403), FakeResp({"data": quote}),
            ]):
                result = BitcoinAPIService().get_price()
                self.assertFalse(result.is_success)
                self.assertIn("CoinGecko, Coinbase", result.error)

    def test_get_price_missing_field(self):
        svc = BitcoinAPIService()

        def fake_get(url, params=None, timeout=None):
            return FakeResp({'btc': {}}, 200)

        orig = requests.get
        try:
            requests.get = fake_get
            res = svc.get_price()
            self.assertFalse(res.is_success)
        finally:
            requests.get = orig

    def test_get_price_network_error(self):
        svc = BitcoinAPIService()

        def fake_get(url, params=None, timeout=None):
            raise requests.exceptions.RequestException('net')

        orig = requests.get
        try:
            requests.get = fake_get
            res = svc.get_price()
            self.assertFalse(res.is_success)
        finally:
            requests.get = orig


if __name__ == '__main__':
    unittest.main()
