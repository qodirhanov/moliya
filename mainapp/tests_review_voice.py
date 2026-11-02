"""Ovozli yordamchi (voice*, stt, tts, assistant, support) bo'yicha ko'rib chiqishda topilgan xatolar uchun regressiya testlari"""
from datetime import date
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from . import voice_parse as vp
from .models import Category, Expense, ExpenseCategory, User, Wallet

API = "/api/v1/voice/"


class ReviewParseTests(TestCase):
    def test_huge_future_period_does_not_overflow(self):
        today = date(2026, 11, 1)
        for text in ("99999999999999999999 kun keyin", "9999999999 yil ichida"):
            d, _ = vp.find_date(vp.loose(text), today, future=True)
            self.assertTrue(d is None or d >= today)

    def test_huge_past_period_does_not_overflow(self):
        d, _ = vp.find_date(vp.loose("99999999999999999999 kun oldin"), date(2026, 11, 1))
        self.assertIsNone(d)


class ReviewApiTests(TestCase):
    def setUp(self):
        cache.clear()
        offline = mock.patch("mainapp.currency._fetch_cbu", side_effect=OSError("offline"))
        offline.start()
        self.addCleanup(offline.stop)
        self.user = User.objects.create_user(username="rv", first_name="Rv", password="Parol-12345")
        self.api = APIClient()
        self.api.force_authenticate(self.user)
        self.naqd = Wallet.objects.create(user=self.user, name="Naqd pul", summa=Decimal("1000000"))
        ExpenseCategory.objects.create(name="Oziq-ovqat va bozor")
        ExpenseCategory.objects.create(name="Kutilmagan xarajatlar")
        Category.objects.create(name="Oylik maosh")

    def post(self, payload, **kw):
        return self.api.post(API, payload, format="json", **kw)

    def test_non_dict_json_body_is_400_not_500(self):
        for body in ([], ["x"], "salom", 5):
            res = self.post(body)
            self.assertEqual(res.status_code, 400, (body, res.content))

    def test_non_string_text_is_not_500(self):
        for body in ({"text": ["a"]}, {"text": {"a": 1}}, {"text": 12}):
            self.assertLess(self.post(body).status_code, 500, body)

    def test_huge_amount_does_not_500_or_create_record(self):
        for text in ("99999999999999 ming sarfladim", "ming milliard milliard sarfladim naqddan tushlikka",
                     "tushlikka 1000000000000000 naqddan sarfladim"):
            res = self.post({"text": text})
            self.assertLess(res.status_code, 500, (text, res.content))
        self.assertEqual(Expense.objects.count(), 0)

    def test_huge_period_in_text_does_not_500(self):
        res = self.post({"text": "Akmalga 100 ming qarz berdim 99999999999999999999 kundan keyin"})
        self.assertLess(res.status_code, 500, res.content)

    def test_number_words_beyond_table_does_not_crash(self):
        self.assertEqual(vp.number_words(10 ** 12), str(10 ** 12))
        self.assertEqual(vp.number_words(999_999_999_999)[:3], "to'")
        self.assertIn("1000000000000", vp.spell_numbers("Summa 1000000000000 so'm"))
