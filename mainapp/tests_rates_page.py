"""Navbar → Kurs sahifasi: /api/v1/rates/ (Markaziy bank kurslari, kunlik o'zgarish, kesh va internetsiz holat).
Tarmoq har doim mock: haqiqiy cbu.uz ga murojaat qilinmaydi."""
import json
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from . import currency
from .models import ExchangeRate, User

API = "/api/v1"
FAKE_RATES = {
    "USD": (Decimal("12000"), "23.10.2026", Decimal("-15.5")),
    "EUR": (Decimal("13000.25"), "23.10.2026", Decimal("20")),
    "RUB": (Decimal("150.5"), "23.10.2026", None),
}


class RatesApiTests(TestCase):
    def setUp(self):
        cache.clear()
        patcher = mock.patch("mainapp.currency._fetch_cbu", return_value=FAKE_RATES)
        self.fetch = patcher.start()
        self.addCleanup(patcher.stop)
        self.user = User.objects.create_user(username="ali", password="Parol-12345")
        self.api = APIClient()
        self.api.force_authenticate(self.user)

    def test_requires_login(self):
        self.assertIn(APIClient().get(f"{API}/rates/").status_code, (401, 403))

    def test_returns_rates_with_daily_change(self):
        res = self.api.get(f"{API}/rates/")
        self.assertEqual(res.status_code, 200, res.content)
        data = res.json()
        self.assertEqual(data["base"], "UZS")
        self.assertEqual(data["date"], "23.10.2026")
        by_code = {r["currency"]: r for r in data["rates"]}
        self.assertEqual(by_code["USD"], {"currency": "USD", "rate": "12000", "diff": "-15.5", "date": "23.10.2026"})
        self.assertEqual(by_code["EUR"]["rate"], "13000.25")
        self.assertIsNone(by_code["RUB"]["diff"])

    def test_rates_are_cached_between_requests(self):
        self.api.get(f"{API}/rates/")
        self.api.get(f"{API}/rates/")
        self.assertEqual(self.fetch.call_count, 1)

    def test_offline_returns_last_saved_rates(self):
        ExchangeRate.objects.create(currency="USD", rate=Decimal("11500"), rate_date="20.10.2026")
        ExchangeRate.objects.filter(currency="USD").update(updated_at=timezone.now() - timedelta(days=2))
        self.fetch.side_effect = OSError("internet yo'q")
        res = self.api.get(f"{API}/rates/")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["rates"][0]["rate"], "11500")

    def test_offline_without_saved_rates_is_503(self):
        self.fetch.side_effect = OSError("internet yo'q")
        res = self.api.get(f"{API}/rates/")
        self.assertEqual(res.status_code, 503)
        self.assertIn("error", res.json())


class FetchCbuDiffTests(TestCase):
    def test_diff_is_parsed_per_unit(self):
        payload = [
            {"Ccy": "USD", "Rate": "12000.50", "Nominal": "1", "Diff": "-12.30", "Date": "23.10.2026"},
            {"Ccy": "KRW", "Rate": "85.00", "Nominal": "10", "Diff": "0.50", "Date": "23.10.2026"},
            {"Ccy": "XXX", "Rate": "5", "Nominal": "1", "Diff": "", "Date": "23.10.2026"},
        ]
        resp = mock.MagicMock()
        resp.__enter__.return_value.read.return_value = json.dumps(payload).encode()
        with mock.patch("mainapp.currency.urllib.request.urlopen", return_value=resp):
            rates = currency._fetch_cbu()
        self.assertEqual(rates["USD"], (Decimal("12000.50"), "23.10.2026", Decimal("-12.30")))
        self.assertEqual(rates["KRW"][0], Decimal("8.5"))
        self.assertEqual(rates["KRW"][2], Decimal("0.05"))
        self.assertIsNone(rates["XXX"][2])
