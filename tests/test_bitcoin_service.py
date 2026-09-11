import unittest
import requests

from core.services import BitcoinAPIService
from core.data_models import Result


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
