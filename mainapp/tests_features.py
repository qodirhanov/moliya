"""Yangi imkoniyatlar: o'chirilgan amalni qaytarish, doimiy to'lovlar, jamg'arma maqsadlari va
ikki bosqichli himoya (elektron pochta kod). Tarmoq har doim mock: haqiqiy cbu.uz ga murojaat qilinmaydi."""
import re
from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Category, Expense, ExpenseCategory, Income, LoginCode, RecurringPayment, User, Wallet, add_months
from .recurring import process_due

API = "/api/v1"
PASSWORD = "Parol-12345"


class FeatureTestCase(TestCase):
    def setUp(self):
        cache.clear()
        offline = mock.patch("mainapp.currency._fetch_cbu", side_effect=OSError("testlarda internet ishlatilmaydi"))
        offline.start()
        self.addCleanup(offline.stop)
        self.user = User.objects.create_user(username="ali", password=PASSWORD, email="ali@example.com")
        self.api = APIClient()
        self.api.force_authenticate(self.user)
        self.wallet = Wallet.objects.create(user=self.user, name="Karta", summa=Decimal("1000"))
        self.exp_cat = ExpenseCategory.objects.create(name="Ijara")
        self.inc_cat = Category.objects.create(name="Maosh")

    def balance(self):
        self.wallet.refresh_from_db()
        return self.wallet.summa


class RestoreTests(FeatureTestCase):
    def test_deleted_expense_is_restored_with_balance(self):
        res = self.api.post(f"{API}/expenses/", {"wallet": self.wallet.id, "summa": "300", "category": self.exp_cat.id}, format="json")
        pk = res.json()["id"]
        self.api.delete(f"{API}/expenses/{pk}/")
        self.assertEqual(self.balance(), Decimal("1000"))

        res = self.api.post(f"{API}/expenses/{pk}/restore/")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(self.balance(), Decimal("700"))
        self.assertTrue(Expense.objects.get(pk=pk).status)

    def test_restore_fails_cleanly_when_money_was_spent(self):
        res = self.api.post(f"{API}/expenses/", {"wallet": self.wallet.id, "summa": "800", "category": self.exp_cat.id}, format="json")
        pk = res.json()["id"]
        self.api.delete(f"{API}/expenses/{pk}/")
        self.api.post(f"{API}/expenses/", {"wallet": self.wallet.id, "summa": "900", "category": self.exp_cat.id}, format="json")

        res = self.api.post(f"{API}/expenses/{pk}/restore/")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(self.balance(), Decimal("100"))
        self.assertFalse(Expense.objects.get(pk=pk).status)

    def test_cannot_restore_other_users_or_active_record(self):
        other = User.objects.create_user(username="vali", password=PASSWORD)
        other_wallet = Wallet.objects.create(user=other, name="X", summa=0)
        foreign = Income.objects.create(user=other, wallet=other_wallet, summa=5, category=self.inc_cat)
        foreign.delete()
        self.assertEqual(self.api.post(f"{API}/incomes/{foreign.pk}/restore/").status_code, 404)
        active = Income.objects.create(user=self.user, wallet=self.wallet, summa=5, category=self.inc_cat)
        self.assertEqual(self.api.post(f"{API}/incomes/{active.pk}/restore/").status_code, 404)


class RecurringTests(FeatureTestCase):
    def create(self, **extra):
        payload = {"kind": "expense", "name": "Ijara", "wallet": self.wallet.id, "summa": "100",
                   "expense_category": self.exp_cat.id, "frequency": "monthly",
                   "start_date": timezone.localdate().isoformat(), **extra}
        res = self.api.post(f"{API}/recurring/", payload, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        return RecurringPayment.objects.get(pk=res.json()["id"])

    def test_due_today_is_written_once(self):
        payment = self.create()
        self.assertEqual(process_due(self.user), 1)
        self.assertEqual(process_due(self.user), 0)  # ikkinchi chaqiruv qayta yozmaydi
        self.assertEqual(self.balance(), Decimal("900"))
        payment.refresh_from_db()
        self.assertEqual(payment.next_date, add_months(timezone.localdate(), 1, timezone.localdate().day))
        self.assertTrue(Expense.objects.filter(description="Doimiy: Ijara").exists())

    def test_past_start_date_is_not_backfilled(self):
        payment = self.create(start_date=(timezone.localdate() - timedelta(days=40)).isoformat(), frequency="weekly")
        self.assertGreaterEqual(payment.next_date, timezone.localdate())
        self.assertLess(payment.next_date, timezone.localdate() + timedelta(days=7))

    def test_missed_days_are_caught_up(self):
        payment = self.create(frequency="daily")
        RecurringPayment.objects.filter(pk=payment.pk).update(next_date=timezone.localdate() - timedelta(days=2))
        self.assertEqual(process_due(self.user), 3)
        self.assertEqual(self.balance(), Decimal("700"))

    def test_insufficient_funds_keeps_date_and_records_error(self):
        payment = self.create(summa="5000")
        self.assertEqual(process_due(self.user), 0)
        payment.refresh_from_db()
        self.assertEqual(payment.next_date, timezone.localdate())
        self.assertIn("yetarli", payment.last_error)
        self.assertEqual(self.balance(), Decimal("1000"))

    def test_income_kind_requires_income_category(self):
        res = self.api.post(f"{API}/recurring/", {"kind": "income", "name": "Maosh", "wallet": self.wallet.id,
                                                   "summa": "100", "frequency": "monthly",
                                                   "start_date": timezone.localdate().isoformat()}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("income_category", res.json())

    def test_end_date_stops_payments(self):
        payment = self.create(frequency="daily", end_date=timezone.localdate().isoformat())
        RecurringPayment.objects.filter(pk=payment.pk).update(next_date=timezone.localdate() - timedelta(days=1))
        self.assertEqual(process_due(self.user), 2)
        self.assertEqual(process_due(self.user), 0)

    def test_month_end_anchor(self):
        self.assertEqual(add_months(date(2026, 1, 31), 1, 31), date(2026, 2, 28))
        self.assertEqual(add_months(date(2026, 2, 28), 1, 31), date(2026, 3, 31))
        self.assertEqual(add_months(date(2026, 12, 15), 1, 15), date(2027, 1, 15))


class GoalTests(FeatureTestCase):
    """Yangi maqsadga o'z hamyoni ochiladi: undan pul chiqmaydi, unga faqat O'tkazma tushadi"""

    def create_goal(self, **extra):
        res = self.api.post(f"{API}/goals/", {"name": "Mashina", "target": "5000", **extra}, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        return res.json()

    def test_goal_opens_own_wallet(self):
        data = self.create_goal(currency="usd")
        wallet = Wallet.objects.get(pk=data["wallet"])
        self.assertTrue(wallet.is_goal)
        self.assertEqual((wallet.name, wallet.currency, wallet.summa), ("Mashina", "USD", Decimal("0")))
        self.assertEqual(Decimal(data["saved"]), Decimal("0"))
        self.assertTrue(data["wallet_is_goal"])

    def test_wallet_cannot_be_chosen_or_changed(self):
        # Mavjud hamyon ID si e'tiborsiz qoldiriladi — har doim yangi hamyon ochiladi
        data = self.create_goal(wallet=self.wallet.id)
        self.assertNotEqual(data["wallet"], self.wallet.id)
        res = self.api.patch(f"{API}/goals/{data['id']}/", {"wallet": self.wallet.id, "name": "Uy"}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["wallet"], data["wallet"])
        # Maqsad nomi o'zgarsa hamyon ham qayta nomlanadi
        self.assertEqual(Wallet.objects.get(pk=data["wallet"]).name, "Uy")

    def test_transfer_in_counts_as_progress(self):
        data = self.create_goal()
        res = self.api.post(f"{API}/transfers/", {"from_wallet": self.wallet.id, "to_wallet": data["wallet"], "summa": "300"}, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(Decimal(self.api.get(f"{API}/goals/").json()[0]["saved"]), Decimal("300"))

    def test_goal_wallet_blocks_money_out_and_income(self):
        goal_wallet = Wallet.objects.get(pk=self.create_goal()["wallet"])
        self.api.post(f"{API}/transfers/", {"from_wallet": self.wallet.id, "to_wallet": goal_wallet.id, "summa": "300"}, format="json")
        attempts = {
            "expenses": {"wallet": goal_wallet.id, "summa": "10", "category": self.exp_cat.id},
            "incomes": {"wallet": goal_wallet.id, "summa": "10", "category": self.inc_cat.id},
            "transfers": {"from_wallet": goal_wallet.id, "to_wallet": self.wallet.id, "summa": "10"},
            "debts": {"person_name": "Vali", "debt_type": "give", "summa": "10", "wallet": goal_wallet.id},
        }
        for endpoint, payload in attempts.items():
            res = self.api.post(f"{API}/{endpoint}/", payload, format="json")
            self.assertEqual(res.status_code, 400, (endpoint, res.content))
        goal_wallet.refresh_from_db()
        self.assertEqual(goal_wallet.summa, Decimal("300"))
        # Hamyonni to'g'ridan-to'g'ri tahrirlash va o'chirish ham yopiq
        self.assertEqual(self.api.patch(f"{API}/wallets/{goal_wallet.id}/", {"name": "X"}, format="json").status_code, 400)
        self.assertEqual(self.api.delete(f"{API}/wallets/{goal_wallet.id}/").status_code, 400)

    def test_deleting_goal_moves_money_and_deletes_wallet(self):
        data = self.create_goal()
        self.api.post(f"{API}/transfers/", {"from_wallet": self.wallet.id, "to_wallet": data["wallet"], "summa": "300"}, format="json")
        # Pul bor — qaysi hamyonga o'tkazilishi aytilmasa rad etiladi, hech narsa o'zgarmaydi
        res = self.api.delete(f"{API}/goals/{data['id']}/")
        self.assertEqual(res.status_code, 400)
        self.assertTrue(Wallet.objects.get(pk=data["wallet"]).status)

        res = self.api.delete(f"{API}/goals/{data['id']}/", {"to_wallet": self.wallet.id}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        goal_wallet = Wallet.objects.get(pk=data["wallet"])
        self.assertFalse(goal_wallet.status)
        self.assertEqual(goal_wallet.summa, Decimal("0"))
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.summa, Decimal("1000"))  # 1000 - 300 + 300
        self.assertEqual(self.api.get(f"{API}/goals/").json(), [])

    def test_deleting_empty_goal_deletes_wallet(self):
        data = self.create_goal()
        self.assertEqual(self.api.delete(f"{API}/goals/{data['id']}/").status_code, 200)
        self.assertFalse(Wallet.objects.get(pk=data["wallet"]).status)

    def test_goal_money_cannot_go_to_foreign_or_goal_wallet(self):
        data = self.create_goal()
        other_goal = self.create_goal()
        self.api.post(f"{API}/transfers/", {"from_wallet": self.wallet.id, "to_wallet": data["wallet"], "summa": "300"}, format="json")
        foreign = Wallet.objects.create(user=User.objects.create_user(username="vali", password=PASSWORD), name="X")
        for target in (foreign.id, other_goal["wallet"], data["wallet"]):
            res = self.api.delete(f"{API}/goals/{data['id']}/", {"to_wallet": target}, format="json")
            self.assertEqual(res.status_code, 400, target)
        self.assertEqual(Wallet.objects.get(pk=data["wallet"]).summa, Decimal("300"))

    def test_deleting_goal_converts_currency(self):
        data = self.create_goal(currency="USD")
        usd = Wallet.objects.create(user=self.user, name="Dollar", summa=Decimal("50"), currency="USD")
        self.api.post(f"{API}/transfers/", {"from_wallet": usd.id, "to_wallet": data["wallet"], "summa": "20"}, format="json")
        with mock.patch("mainapp.views.convert", return_value=(Decimal("250000"), Decimal("12500"))):
            res = self.api.delete(f"{API}/goals/{data['id']}/", {"to_wallet": self.wallet.id}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.summa, Decimal("251000"))

    def test_legacy_goal_keeps_its_wallet(self):
        from .models import SavingsGoal
        goal = SavingsGoal.objects.create(user=self.user, name="Eski", target=Decimal("5000"), wallet=self.wallet)
        self.assertEqual(self.api.delete(f"{API}/goals/{goal.id}/").status_code, 200)
        self.wallet.refresh_from_db()
        self.assertTrue(self.wallet.status)
        self.assertEqual(self.wallet.summa, Decimal("1000"))

    def test_bad_currency_rejected(self):
        res = self.api.post(f"{API}/goals/", {"name": "M", "target": "5", "currency": "12"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertFalse(Wallet.objects.filter(is_goal=True).exists())


class TwoFactorTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="ali", password=PASSWORD, email="ali@example.com")
        self.client = APIClient(enforce_csrf_checks=False)

    def last_code(self):
        return re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)

    def enable(self):
        self.client.force_authenticate(self.user)
        res = self.client.post(f"{API}/auth/two-factor/", {"enabled": True, "password": PASSWORD}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        res = self.client.post(f"{API}/auth/two-factor/confirm/", {"token": res.json()["token"], "code": self.last_code()}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.client.force_authenticate(None)
        self.user.refresh_from_db()
        self.assertTrue(self.user.two_factor_enabled)

    def test_login_requires_code_when_enabled(self):
        self.enable()
        res = self.client.post(f"{API}/auth/login/", {"username": "ali", "password": PASSWORD}, format="json")
        self.assertTrue(res.json()["two_factor"])
        self.assertFalse(self.client.get(f"{API}/auth/me/").json()["authenticated"])

        token = res.json()["token"]
        wrong = self.client.post(f"{API}/auth/login/verify/", {"token": token, "code": "000000" if self.last_code() != "000000" else "111111"}, format="json")
        self.assertEqual(wrong.status_code, 400)
        ok = self.client.post(f"{API}/auth/login/verify/", {"token": token, "code": self.last_code()}, format="json")
        self.assertEqual(ok.status_code, 200, ok.content)
        self.assertTrue(self.client.get(f"{API}/auth/me/").json()["authenticated"])
        # Kod ikkinchi marta ishlamaydi
        again = APIClient().post(f"{API}/auth/login/verify/", {"token": token, "code": self.last_code()}, format="json")
        self.assertEqual(again.status_code, 400)

    def test_code_locks_after_max_attempts(self):
        self.enable()
        token = self.client.post(f"{API}/auth/login/", {"username": "ali", "password": PASSWORD}, format="json").json()["token"]
        code = self.last_code()
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(LoginCode.MAX_ATTEMPTS):
            self.client.post(f"{API}/auth/login/verify/", {"token": token, "code": wrong}, format="json")
        res = self.client.post(f"{API}/auth/login/verify/", {"token": token, "code": code}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_enable_needs_password_and_email(self):
        self.client.force_authenticate(self.user)
        res = self.client.post(f"{API}/auth/two-factor/", {"enabled": True, "password": "xato"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.user.email = ""
        self.user.save()
        res = self.client.post(f"{API}/auth/two-factor/", {"enabled": True, "password": PASSWORD}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_email_cannot_be_cleared_while_enabled(self):
        self.enable()
        self.client.force_authenticate(self.user)
        res = self.client.patch(f"{API}/auth/profile/", {"email": "", "password": PASSWORD}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("Ikki bosqichli", res.json()["email"])
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "ali@example.com")

    def test_login_without_2fa_unchanged(self):
        res = self.client.post(f"{API}/auth/login/", {"username": "ali", "password": PASSWORD}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("two_factor", res.json())
        self.assertTrue(self.client.get(f"{API}/auth/me/").json()["authenticated"])
