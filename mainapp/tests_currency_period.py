"""№4 (ro'yxatda yo'q valyuta kodi keshi) va №12 (?year=² / ?month=² 500 xato) testlari.
Tarmoq har doim mock: haqiqiy cbu.uz ga murojaat qilinmaydi."""
from datetime import datetime
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from . import currency
from .models import ExchangeRate, Expense, Income, Transfer, User, Wallet

API = "/api/v1"
FAKE_RATES = {"USD": (Decimal("12000"), "08.10.2026"), "EUR": (Decimal("13000"), "08.10.2026")}


class CurrencyTestCase(TestCase):
    def setUp(self):
        cache.clear()
        patcher = mock.patch("mainapp.currency._fetch_cbu", return_value=FAKE_RATES)
        self.fetch = patcher.start()
        self.addCleanup(patcher.stop)
        self.user = User.objects.create_user(username="ali", password="Parol-12345")
        self.api = APIClient()
        self.api.force_authenticate(self.user)


class MissingCodeCacheTests(CurrencyTestCase):
    def test_unknown_code_is_not_refetched_every_time(self):
        for _ in range(3):
            with self.assertRaises(currency.CurrencyRateError):
                currency.get_rate_to_uzs("XYZ")
        self.assertEqual(self.fetch.call_count, 1)

    def test_second_call_does_not_rewrite_rates(self):
        with self.assertRaises(currency.CurrencyRateError):
            currency.get_rate_to_uzs("XYZ")
        before = ExchangeRate.objects.get(currency="USD").updated_at
        with self.assertRaises(currency.CurrencyRateError):
            currency.get_rate_to_uzs("XYZ")
        self.assertEqual(ExchangeRate.objects.get(currency="USD").updated_at, before)

    def test_known_codes_keep_working_after_a_miss(self):
        with self.assertRaises(currency.CurrencyRateError):
            currency.get_rate_to_uzs("XYZ")
        self.assertEqual(currency.get_rate_to_uzs("usd"), Decimal("12000"))
        self.assertIsNone(cache.get(currency._MISSING_CODE_KEY + "USD"))
        self.assertEqual(self.fetch.call_count, 1)

    def test_miss_is_remembered_per_code(self):
        with self.assertRaises(currency.CurrencyRateError):
            currency.get_rate_to_uzs("XYZ")
        with self.assertRaises(currency.CurrencyRateError):
            currency.get_rate_to_uzs("QQQ")  # boshqa kod — o'zining yagona so'rovi
        self.assertEqual(self.fetch.call_count, 2)

    def test_miss_expires(self):
        with self.assertRaises(currency.CurrencyRateError):
            currency.get_rate_to_uzs("XYZ")
        cache.delete(currency._MISSING_CODE_KEY + "XYZ")  # muddat tugadi
        with self.assertRaises(currency.CurrencyRateError):
            currency.get_rate_to_uzs("XYZ")
        self.assertEqual(self.fetch.call_count, 2)

    def test_miss_is_stored_with_ttl(self):
        with mock.patch("mainapp.currency.cache") as fake_cache:
            fake_cache.get.return_value = None
            with self.assertRaises(currency.CurrencyRateError):
                currency.get_rate_to_uzs("XYZ")
        fake_cache.set.assert_called_once_with(currency._MISSING_CODE_KEY + "XYZ", True, currency.MISSING_CODE_SECONDS)

    def test_failed_refresh_is_not_a_missing_code(self):
        self.fetch.side_effect = OSError("internet yo'q")
        with self.assertLogs("mainapp.currency", "WARNING"), self.assertRaises(currency.CurrencyRateError):
            currency.get_rate_to_uzs("XYZ")
        self.assertIsNone(cache.get(currency._MISSING_CODE_KEY + "XYZ"))
        self.assertTrue(cache.get(currency._REFRESH_FAILED_KEY))  # qayta urinish baribir REFRESH_RETRY_SECONDS ga cheklangan

    def test_code_added_later_by_any_refresh_is_found(self):
        with self.assertRaises(currency.CurrencyRateError):
            currency.get_rate_to_uzs("XYZ")
        # Boshqa yangilanish XYZ ni ham olib keldi: saqlangan kurs "yo'q" belgisidan ustun
        ExchangeRate.objects.create(currency="XYZ", rate=Decimal("7"))
        self.assertEqual(currency.get_rate_to_uzs("XYZ"), Decimal("7"))

    def test_non_iso_name_never_touches_network_or_cache(self):
        cache_set = mock.patch.object(cache, "set", wraps=cache.set)
        with cache_set as spy, self.assertRaises(currency.CurrencyRateError):
            currency.get_rate_to_uzs("dollar")
        self.fetch.assert_not_called()
        spy.assert_not_called()

    def test_stale_code_dropped_by_central_bank_is_not_refetched(self):
        ExchangeRate.objects.create(currency="XYZ", rate=Decimal("7"))
        ExchangeRate.objects.filter(currency="XYZ").update(updated_at=timezone.now() - currency.RATES_TTL * 2)
        for _ in range(3):
            self.assertEqual(currency.get_rate_to_uzs("XYZ"), Decimal("7"))  # oxirgi saqlangan kurs bilan javob
        self.assertEqual(self.fetch.call_count, 1)

    def test_try_refresh_marks_only_unlisted_code(self):
        self.assertTrue(currency._try_refresh("USD"))
        self.assertIsNone(cache.get(currency._MISSING_CODE_KEY + "USD"))
        self.assertTrue(currency._try_refresh("XYZ"))
        self.assertTrue(cache.get(currency._MISSING_CODE_KEY + "XYZ"))
        self.assertTrue(currency._try_refresh())  # kodsiz chaqiruv — hech narsa belgilanmaydi

    @override_settings(CURRENCY_BACKGROUND_REFRESH=True)
    def test_background_refresh_is_skipped_for_known_missing_code(self):
        ExchangeRate.objects.create(currency="XYZ", rate=Decimal("7"))
        ExchangeRate.objects.filter(currency="XYZ").update(updated_at=timezone.now() - currency.RATES_TTL * 2)
        self.addCleanup(lambda: currency._refresh_lock.locked() and currency._refresh_lock.release())
        with mock.patch("mainapp.currency.threading.Thread") as thread:
            currency.get_rate_to_uzs("XYZ")
            self.assertEqual(thread.call_count, 1)  # belgi yo'q: fonda bir marta yangilanadi
            cache.set(currency._MISSING_CODE_KEY + "XYZ", True, 60)
            currency._refresh_lock.release()
            self.assertEqual(currency.get_rate_to_uzs("XYZ"), Decimal("7"))
            self.assertEqual(thread.call_count, 1)  # belgi bor: fon oqimi ishga tushmaydi
        self.fetch.assert_not_called()

    def test_summary_endpoint_does_not_refetch_for_unknown_code(self):
        wallet = Wallet.objects.create(user=self.user, name="Noma'lum", summa=5, currency="XYZ")
        Income.objects.bulk_create([Income(user=self.user, wallet=wallet, summa=5)])  # balans mantig'isiz
        for _ in range(3):
            res = self.api.get(f"{API}/wallets/summary/")
            self.assertEqual(res.status_code, 200, res.content)
            self.assertEqual(res.json()["missing_rates"], ["XYZ"])
        self.assertEqual(self.fetch.call_count, 1)

    def test_convert_endpoint_does_not_refetch_for_unknown_code(self):
        with self.assertLogs("django.request", "ERROR"):  # 503 javobi django.request ga yoziladi
            for _ in range(3):
                res = self.api.get(f"{API}/rates/convert/", {"from": "XYZ", "to": "UZS", "amount": 5})
                self.assertEqual(res.status_code, 503, res.content)
        self.assertEqual(self.fetch.call_count, 1)

    def test_convert_endpoint_non_iso_name_skips_network(self):
        with self.assertLogs("django.request", "ERROR"):
            res = self.api.get(f"{API}/rates/convert/", {"from": "dollar", "to": "UZS", "amount": 5})
        self.assertEqual(res.status_code, 503, res.content)
        self.fetch.assert_not_called()


class PeriodParamTests(CurrencyTestCase):
    def setUp(self):
        super().setUp()
        wallet = Wallet.objects.create(user=self.user, name="Naqd", summa=0, currency="UZS")
        other = Wallet.objects.create(user=self.user, name="Karta", summa=0, currency="UZS")
        self.oct_2026 = timezone.make_aware(datetime(2026, 10, 5, 12))
        self.sep_2025 = timezone.make_aware(datetime(2025, 9, 5, 12))
        # bulk_create: save() dagi balans mantig'ini chetlab o'tadi — bu testlar faqat davr filtrini tekshiradi
        for date in (self.oct_2026, self.sep_2025):
            Expense.objects.bulk_create([Expense(user=self.user, wallet=wallet, summa=100, date=date)])
            Income.objects.bulk_create([Income(user=self.user, wallet=wallet, summa=100, date=date)])
            Transfer.objects.bulk_create([
                Transfer(user=self.user, from_wallet=wallet, to_wallet=other, summa=10, to_summa=10, date=date)
            ])

    def count(self, resource, **params):
        res = self.api.get(f"{API}/{resource}/", params)
        self.assertEqual(res.status_code, 200, res.content)
        data = res.json()
        return len(data["results"] if isinstance(data, dict) else data)

    def test_superscript_year_or_month_is_ignored_not_500(self):
        for resource in ("expenses", "incomes", "transfers"):
            for params in ({"year": "²"}, {"month": "²"}, {"year": "²", "month": "³"}, {"year": "2026", "month": "²"}):
                with self.subTest(resource=resource, params=params):
                    expected = 1 if params.get("year") == "2026" else 2
                    self.assertEqual(self.count(resource, **params), expected)

    def test_other_unicode_digits_are_ignored(self):
        for value in ("٢٠٢٦", "２０２６", "²⁰²⁶"):  # arab-hind, to'liq kenglikdagi, yuqori indeks
            with self.subTest(value=value):
                self.assertEqual(self.count("expenses", year=value), 2)

    def test_huge_number_is_ignored_not_500(self):
        self.assertEqual(self.count("expenses", year="9" * 5000), 2)
        self.assertEqual(self.count("expenses", month="9" * 5000), 2)

    def test_valid_year_and_month_still_filter(self):
        self.assertEqual(self.count("expenses", year="2026"), 1)
        self.assertEqual(self.count("expenses", year="2025", month="9"), 1)
        self.assertEqual(self.count("expenses", year="2025", month="10"), 0)
        self.assertEqual(self.count("expenses", month="9"), 1)
        self.assertEqual(self.count("incomes", year="2026", month="10"), 1)
        self.assertEqual(self.count("transfers", year="2025"), 1)

    def test_out_of_range_values_are_ignored(self):
        self.assertEqual(self.count("expenses", year="1800"), 2)
        self.assertEqual(self.count("expenses", month="13"), 2)
        self.assertEqual(self.count("expenses", year="abc", month="-1"), 2)

    def test_monthly_stats_survive_superscript(self):
        res = self.api.get(f"{API}/stats/monthly/", {"year": "²", "month": "²"})
        self.assertEqual(res.status_code, 200, res.content)
