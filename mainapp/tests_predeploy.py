"""Serverga chiqishdan oldingi tuzatishlar: valyuta o'zgarishi, doimiy to'lovning ikki marta yozilishi,
ovozdagi "3 marta" va summadan keyingi son"""
from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from . import voice_parse as vp
from .models import Expense, ExpenseCategory, RecurringPayment, SavingsGoal, User, Wallet
from .recurring import process_due
from .tests_voice import API as VOICE_API

API = "/api/v1"


class BaseCase(TestCase):
    def setUp(self):
        cache.clear()
        offline = mock.patch("mainapp.currency._fetch_cbu", side_effect=OSError("testlarda internet ishlatilmaydi"))
        offline.start()
        self.addCleanup(offline.stop)
        self.user = User.objects.create_user(username="ali", password="Parol-12345")
        self.api = APIClient()
        self.api.force_authenticate(self.user)
        self.wallet = Wallet.objects.create(user=self.user, name="Karta", summa=Decimal("1000000"))
        self.category = ExpenseCategory.objects.create(name="Kutilmagan xarajatlar")

    def recurring(self, **extra):
        payload = {"kind": "expense", "name": "Ijara", "wallet": self.wallet.id, "summa": "100",
                   "expense_category": self.category.id, "frequency": "monthly",
                   "start_date": timezone.localdate().isoformat(), **extra}
        res = self.api.post(f"{API}/recurring/", payload, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        return RecurringPayment.objects.get(pk=res.json()["id"])


class WalletCurrencyLockTests(BaseCase):
    def change_currency(self):
        return self.api.patch(f"{API}/wallets/{self.wallet.id}/", {"currency": "USD"}, format="json")

    def test_locked_by_recurring_payment(self):
        self.recurring(start_date=(timezone.localdate() + timedelta(days=5)).isoformat())
        self.assertEqual(self.change_currency().status_code, 400)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.currency, "UZS")

    def test_locked_by_savings_goal(self):
        SavingsGoal.objects.create(user=self.user, name="Mashina", target=Decimal("5000"), wallet=self.wallet)
        self.assertEqual(self.change_currency().status_code, 400)

    def test_free_after_recurring_payment_is_deleted(self):
        payment = self.recurring(start_date=(timezone.localdate() + timedelta(days=5)).isoformat())
        RecurringPayment.objects.filter(pk=payment.pk).update(status=False)
        self.assertEqual(self.change_currency().status_code, 200)


class RecurringScheduleChangeTests(BaseCase):
    def count(self):
        return Expense.objects.filter(status=True).count()

    def test_changing_frequency_does_not_write_todays_payment_twice(self):
        payment = self.recurring()
        self.assertEqual(process_due(self.user), 1)

        res = self.api.patch(f"{API}/recurring/{payment.id}/", {"frequency": "weekly"}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        payment.refresh_from_db()
        self.assertEqual(payment.next_date, timezone.localdate() + timedelta(days=7))
        self.assertEqual(process_due(self.user), 0)
        self.assertEqual(self.count(), 1)

    def test_unpaid_due_today_stays_today(self):
        # Pul yetmagani uchun bugungi to'lov yozilmagan: jadval o'zgarsa ham bugun qoladi
        payment = self.recurring(summa="5000000")
        self.assertEqual(process_due(self.user), 0)
        self.api.patch(f"{API}/recurring/{payment.id}/", {"frequency": "weekly"}, format="json")
        payment.refresh_from_db()
        self.assertEqual(payment.next_date, timezone.localdate())


class VoiceParseTests(TestCase):
    today = date(2026, 10, 30)

    def amount(self, text):
        return vp.best_amount(vp.find_amounts(vp.loose(text).split()))["value"]

    def day(self, text):
        return vp.find_date(vp.loose(text), self.today)[0]

    def test_marta_is_not_march(self):
        self.assertIsNone(self.day("taksiga 3 marta 15 ming sarfladim"))
        self.assertEqual(self.amount("taksiga 3 marta 15 ming sarfladim"), 15000)

    def test_real_month_forms_still_work(self):
        self.assertEqual(self.day("3 mart"), date(2026, 3, 3))
        self.assertEqual(self.day("3 martda"), date(2026, 3, 3))
        self.assertEqual(self.day("5 oktabrdagi"), date(2026, 10, 5))
        self.assertEqual(self.day("12 sentyabrda"), date(2026, 9, 12))
        self.assertEqual(self.day("1 mayda"), date(2026, 5, 1))

    def test_number_after_amount_is_not_added(self):
        self.assertEqual(self.amount("taksiga 20 ming 2 kishiga"), 20000)
        self.assertEqual(self.amount("45 ming 2 ta non"), 45000)
        self.assertEqual(self.amount("20 ming 2"), 20000)

    def test_compound_amounts_still_work(self):
        self.assertEqual(self.amount("45 ming 500"), 45500)
        self.assertEqual(self.amount("2 million 500 ming"), 2500000)
        self.assertEqual(self.amount("2 million 5 ming"), 2005000)
        self.assertEqual(self.amount("yigirma ming besh yuz"), 20500)
        self.assertEqual(self.amount("bir million ikki yuz ming"), 1200000)

    def test_days_ago(self):
        self.assertEqual(self.day("3 kun oldin"), date(2026, 10, 27))
        self.assertEqual(self.day("ikki hafta avval"), date(2026, 10, 16))
        self.assertIsNone(self.day("3 kun"))


class VoiceEndToEndTests(BaseCase):
    def say(self, text):
        res = self.api.post(VOICE_API, {"text": text}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        return res.json()

    def test_marta_records_todays_expense_with_right_amount(self):
        out = self.say("taksiga 3 marta 15 ming sarfladim")
        self.assertEqual(out["status"], "done", out)
        expense = Expense.objects.get()
        self.assertEqual(expense.summa, Decimal("15000"))
        self.assertEqual(timezone.localtime(expense.date).date(), timezone.localdate())

    def test_days_ago_amount_and_date(self):
        out = self.say("taksiga 20 ming 3 kun oldin sarfladim")
        self.assertEqual(out["status"], "done", out)
        expense = Expense.objects.get()
        self.assertEqual(expense.summa, Decimal("20000"))
        self.assertEqual(timezone.localtime(expense.date).date(), timezone.localdate() - timedelta(days=3))
