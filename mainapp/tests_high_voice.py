"""Ovozli yordamchi xatolari: maqsad hamyoni gapdagi nomi bilan tanlangan hamyondan ustun chiqmasin va
"45.000" 45 emas, 45000 o'qilsin"""
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from . import voice_parse as vp
from .models import Expense, ExpenseCategory, Income, Category, Transfer, User, Wallet
from .tests_voice import API


class ThousandsGroupingTests(TestCase):
    def amount(self, text):
        a = vp.best_amount(vp.find_amounts(vp.loose(text).split()))
        return a and a["value"]

    def test_grouped_integers(self):
        self.assertEqual(self.amount("45.000"), 45000)
        self.assertEqual(self.amount("45,000"), 45000)
        self.assertEqual(self.amount("1.200.000"), 1200000)
        self.assertEqual(self.amount("1,500,000"), 1500000)
        self.assertEqual(self.amount("tushlikka 45.000 so'm"), 45000)

    def test_decimals_stay_decimals(self):
        self.assertEqual(self.amount("1,5 mln"), 1500000)
        self.assertEqual(self.amount("1.5"), Decimal("1.5"))
        self.assertEqual(self.amount("2.50"), Decimal("2.50"))
        self.assertEqual(self.amount("12.5k"), 12500)


class GoalWalletPickTests(TestCase):
    def setUp(self):
        cache.clear()
        offline = mock.patch("mainapp.currency._fetch_cbu", side_effect=OSError("testlarda internet ishlatilmaydi"))
        offline.start()
        self.addCleanup(offline.stop)
        self.user = User.objects.create_user(username="abdurahmon", password="Parol-12345")
        self.api = APIClient()
        self.api.force_authenticate(self.user)
        self.naqd = Wallet.objects.create(user=self.user, name="Naqd", summa=Decimal("1000000"))
        self.karta = Wallet.objects.create(user=self.user, name="Karta", summa=Decimal("2000000"))
        self.goal = Wallet.objects.create(user=self.user, name="Telefon", summa=Decimal("0"), is_goal=True)
        self.food = ExpenseCategory.objects.create(name="Oziq-ovqat va bozor")
        self.other = ExpenseCategory.objects.create(name="Kutilmagan xarajatlar")
        self.other_inc = Category.objects.create(name="Boshqa daromadlar")

    def say(self, text):
        res = self.api.post(API, {"text": text}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        return res.json()

    def test_expense_ignores_goal_name(self):
        out = self.say("telefonga 50 ming sarfladim kartadan")
        self.assertEqual(out["status"], "done", out)
        self.assertEqual(Expense.objects.get().wallet, self.karta)

    def test_income_with_goal_name_does_not_fail(self):
        out = self.say("telefon sotdim 3 million tushdi naqdga")
        self.assertEqual(out["status"], "done", out)
        self.assertEqual(Income.objects.get().wallet, self.naqd)

    def test_ask_wallet_options_exclude_goal(self):
        out = self.say("telefonga 50 ming sarfladim")
        self.assertEqual(out["status"], "ask", out)
        self.assertNotIn("Telefon", out["text"])
        # javobda goal nomi aytilsa ham qabul qilinmaydi
        out = self.say("telefon")
        self.assertEqual(Expense.objects.count(), 0, out)

    def test_transfer_to_goal_still_works(self):
        out = self.say("kartadan telefonga 100 ming o'tkaz")
        self.assertEqual(out["status"], "done", out)
        tr = Transfer.objects.get()
        self.assertEqual((tr.from_wallet, tr.to_wallet, tr.summa), (self.karta, self.goal, Decimal("100000")))
