import io
import re
import time
import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest import mock

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import Permission
from django.contrib.auth.password_validation import validate_password
from django.core import mail
from django.core.cache import cache, caches
from django.core.cache.backends.db import BaseDatabaseCache
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from . import currency
from .backends import LOGIN_MAX_FAILS, _bump_counter, _login_keys, is_login_locked, refund_limit
from .throttles import client_ip
from .models import (
    MAX_AMOUNT, Category, Debt, ExchangeRate, Expense, ExpenseCategory, Income, Member, PasswordResetCode, Transfer, User,
    Wallet,
)

API = "/api/v1"
PASSWORD = "Parol-12345"


def make_user(username, **extra):
    return User.objects.create_user(username=username, password=PASSWORD, **extra)


def make_wallet(user, summa=0, name="Hamyon"):
    return Wallet.objects.create(user=user, name=name, summa=summa, currency="UZS")


def rows(response):
    data = response.json()
    return data.get("results", data) if isinstance(data, dict) else data


class APITestCase(TestCase):
    def setUp(self):
        # DRF sorovlar cheklovi hisoblagichi testlar orasida tolib qolmasin
        cache.clear()
        # Testlar hech qachon haqiqiy Markaziy bankka murojaat qilmasin (kerakli testlar o'zi mock qiladi)
        offline = mock.patch("mainapp.currency._fetch_cbu", side_effect=OSError("testlarda internet ishlatilmaydi"))
        offline.start()
        self.addCleanup(offline.stop)
        self.api = APIClient()

    def login_as(self, user):
        self.api.force_authenticate(user)


class PasswordValidatorTests(TestCase):
    def check(self, password, username="ali"):
        validate_password(password, user=User(username=username))

    def test_rejects_password_equal_to_username(self):
        with self.assertRaises(ValidationError):
            self.check("MyLogin123", username="mylogin123")

    def test_rejects_one_or_two_distinct_characters(self):
        for weak in ("aaaaaaaa", "abababab", "AaAaAaAa"):
            with self.subTest(weak=weak), self.assertRaises(ValidationError):
                self.check(weak)

    def test_rejects_common_passwords(self):
        for common in ("password", "qwerty12", "iloveyou"):
            with self.subTest(common=common), self.assertRaises(ValidationError):
                self.check(common)

    def test_allows_uncommon_varied_password(self):
        self.check(PASSWORD)

    def test_still_rejects_short_and_numeric_only(self):
        for bad in ("abc123", "12345678"):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                self.check(bad)


class AuthTests(APITestCase):
    def register(self, username="ali", password=PASSWORD):
        return self.api.post(f"{API}/auth/register/", {"username": username, "password": password}, format="json")

    def test_register_creates_user_wallet_and_session(self):
        res = self.register()
        self.assertEqual(res.status_code, 201)
        user = User.objects.get(username="ali")
        self.assertEqual(user.wallets.count(), 1)
        self.assertTrue(self.api.get(f"{API}/auth/me/").json()["authenticated"])

    def test_register_rejects_weak_password(self):
        res = self.register(password="aaaaaaaa")
        self.assertEqual(res.status_code, 400)
        self.assertIn("oddiy", res.json()["error"])
        self.assertFalse(User.objects.filter(username="ali").exists())

    def test_register_rejects_duplicate_username(self):
        make_user("ali")
        self.assertEqual(self.register().status_code, 400)

    def test_register_rejects_case_insensitive_duplicate_and_bad_chars(self):
        make_user("ali")
        self.assertEqual(self.register(username="ALI").status_code, 400)
        self.assertEqual(self.register(username="a li!").status_code, 400)

    def test_register_with_non_string_fields_does_not_crash(self):
        res = self.api.post(f"{API}/auth/register/", {"username": 123, "password": PASSWORD, "phone": 5}, format="json")
        self.assertIn(res.status_code, (201, 400))

    def test_login_wrong_password(self):
        make_user("ali")
        res = self.api.post(f"{API}/auth/login/", {"username": "ali", "password": "Notogri-1"}, format="json")
        self.assertEqual(res.status_code, 401)

    def test_change_password(self):
        user = make_user("ali")
        self.login_as(user)
        bad = self.api.post(f"{API}/auth/change-password/", {"old_password": "xato", "new_password": "Yangi-Parol-9"}, format="json")
        self.assertEqual(bad.status_code, 400)
        ok = self.api.post(f"{API}/auth/change-password/", {"old_password": PASSWORD, "new_password": "Yangi-Parol-9"}, format="json")
        self.assertEqual(ok.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.check_password("Yangi-Parol-9"))


class CategoryTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.ali = make_user("ali")
        self.vali = make_user("vali")
        self.global_cat = ExpenseCategory.objects.create(name="Oziq-ovqat")

    def test_anonymous_sees_only_global_categories(self):
        ExpenseCategory.objects.create(name="Shaxsiy", user=self.ali)
        names = [c["name"] for c in rows(self.api.get(f"{API}/expense-categories/"))]
        self.assertEqual(names, ["Oziq-ovqat"])

    def test_anonymous_cannot_create(self):
        res = self.api.post(f"{API}/expense-categories/", {"name": "X"}, format="json")
        self.assertEqual(res.status_code, 401)

    def test_user_creates_private_category(self):
        self.login_as(self.ali)
        res = self.api.post(f"{API}/expense-categories/", {"name": "Mening turkumim"}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(ExpenseCategory.objects.get(name="Mening turkumim").user, self.ali)
        self.login_as(self.vali)
        names = [c["name"] for c in rows(self.api.get(f"{API}/expense-categories/"))]
        self.assertNotIn("Mening turkumim", names)
        self.assertIn("Oziq-ovqat", names)

    def test_other_user_cannot_edit_or_delete_private_category(self):
        cat = ExpenseCategory.objects.create(name="Shaxsiy", user=self.ali)
        self.login_as(self.vali)
        res = self.api.patch(f"{API}/expense-categories/{cat.id}/", {"name": "Buzildi"}, format="json")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(self.api.delete(f"{API}/expense-categories/{cat.id}/").status_code, 404)
        cat.refresh_from_db()
        self.assertEqual(cat.name, "Shaxsiy")

    def test_owner_can_edit_and_delete_own_category(self):
        cat = ExpenseCategory.objects.create(name="Shaxsiy", user=self.ali)
        self.login_as(self.ali)
        res = self.api.patch(f"{API}/expense-categories/{cat.id}/", {"name": "Yangi"}, format="json")
        self.assertEqual(res.status_code, 200)

    def ids(self, path):
        return [c["id"] for c in rows(self.api.get(f"{API}/{path}/"))]

    def test_rename_rejects_existing_name_but_allows_changing_case_of_own(self):
        cat = ExpenseCategory.objects.create(name="Shaxsiy", user=self.ali)
        self.login_as(self.ali)
        url = f"{API}/expense-categories/{cat.id}/"
        self.assertEqual(self.api.patch(url, {"name": "oziq-ovqat"}, format="json").status_code, 400)
        self.assertEqual(self.api.patch(url, {"name": "   "}, format="json").status_code, 400)
        self.assertEqual(self.api.patch(url, {"name": "SHAXSIY"}, format="json").status_code, 200)
        cat.refresh_from_db()
        self.assertEqual(cat.name, "SHAXSIY")

    def test_rename_is_visible_in_old_expenses(self):
        cat = ExpenseCategory.objects.create(name="Eski nom", user=self.ali)
        wallet = make_wallet(self.ali, 50000)
        self.login_as(self.ali)
        expense = self.api.post(f"{API}/expenses/", {"wallet": wallet.id, "category": cat.id, "summa": 1000}, format="json").json()
        self.api.patch(f"{API}/expense-categories/{cat.id}/", {"name": "Yangi nom"}, format="json")
        row = next(e for e in rows(self.api.get(f"{API}/expenses/")) if e["id"] == expense["id"])
        self.assertEqual(row["category_name"], "Yangi nom")

    def test_renaming_global_category_makes_personal_copy_without_touching_others(self):
        ali_wallet, vali_wallet = make_wallet(self.ali, 50000), make_wallet(self.vali, 50000)
        ali_exp = Expense.objects.create(user=self.ali, wallet=ali_wallet, category=self.global_cat, summa=1000)
        vali_exp = Expense.objects.create(user=self.vali, wallet=vali_wallet, category=self.global_cat, summa=2000)
        self.login_as(self.ali)
        res = self.api.patch(f"{API}/expense-categories/{self.global_cat.id}/", {"name": "Ovqatlar"}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertTrue(res.json()["is_custom"])
        copy_id = res.json()["id"]

        # Umumiy toifa hamma uchun o'zgarmagan, faqat Alining ro'yxatidan yashirilgan
        self.global_cat.refresh_from_db()
        self.assertEqual(self.global_cat.name, "Oziq-ovqat")
        names = [c["name"] for c in rows(self.api.get(f"{API}/expense-categories/"))]
        self.assertIn("Ovqatlar", names)
        self.assertNotIn("Oziq-ovqat", names)
        # Alining eski harajati yangi nom bilan ko'rinadi, balans o'zgarmagan
        ali_exp.refresh_from_db()
        self.assertEqual(ali_exp.category_id, copy_id)
        ali_wallet.refresh_from_db()
        self.assertEqual(ali_wallet.summa, 49000)

        # Asl toifa "o'chirilganlar" ro'yxatida ham chiqmaydi — u o'chirilmagan, nomi o'zgargan
        all_ids = [c["id"] for c in rows(self.api.get(f"{API}/expense-categories/?include_hidden=1"))]
        self.assertNotIn(self.global_cat.id, all_ids)

        self.login_as(self.vali)
        self.assertIn("Oziq-ovqat", [c["name"] for c in rows(self.api.get(f"{API}/expense-categories/"))])
        vali_exp.refresh_from_db()
        self.assertEqual(vali_exp.category_id, self.global_cat.id)

    def test_deleting_personal_copy_offers_original_back(self):
        self.login_as(self.ali)
        copy_id = self.api.patch(f"{API}/expense-categories/{self.global_cat.id}/", {"name": "Ovqatlar"}, format="json").json()["id"]
        self.assertEqual(self.api.delete(f"{API}/expense-categories/{copy_id}/").status_code, 204)
        listed = {c["id"]: c["hidden"] for c in rows(self.api.get(f"{API}/expense-categories/?include_hidden=1"))}
        self.assertIs(listed.get(self.global_cat.id), True)
        self.assertEqual(self.api.post(f"{API}/expense-categories/{self.global_cat.id}/restore/").status_code, 200)
        self.assertIn("Oziq-ovqat", [c["name"] for c in rows(self.api.get(f"{API}/expense-categories/"))])

    def test_renaming_global_category_checks_names(self):
        ExpenseCategory.objects.create(name="Transport")
        self.login_as(self.ali)
        url = f"{API}/expense-categories/{self.global_cat.id}/"
        self.assertEqual(self.api.patch(url, {"name": "transport"}, format="json").status_code, 400)
        self.assertEqual(self.api.patch(url, {"name": "  "}, format="json").status_code, 400)
        # Faqat harf katta-kichikligini o'zgartirish ham mumkin; nom o'zgarmasa nusxa yaratilmaydi
        self.assertEqual(self.api.patch(url, {"name": "Oziq-ovqat"}, format="json").status_code, 200)
        self.assertEqual(ExpenseCategory.objects.filter(user=self.ali).count(), 0)
        self.assertEqual(self.api.patch(url, {"name": "OZIQ-OVQAT"}, format="json").status_code, 200)
        self.assertEqual(ExpenseCategory.objects.get(user=self.ali).name, "OZIQ-OVQAT")

    def test_renaming_global_income_category_moves_my_incomes(self):
        salary = Category.objects.create(name="Oylik")
        wallet = make_wallet(self.ali)
        income = Income.objects.create(user=self.ali, wallet=wallet, category=salary, summa=500)
        self.login_as(self.ali)
        res = self.api.patch(f"{API}/categories/{salary.id}/", {"name": "Maosh"}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        income.refresh_from_db()
        self.assertEqual(income.category.name, "Maosh")
        self.assertEqual(Category.objects.get(pk=salary.pk).name, "Oylik")

    def test_deleting_own_category_keeps_history(self):
        cat = ExpenseCategory.objects.create(name="Shaxsiy", user=self.ali)
        wallet = make_wallet(self.ali, 50000)
        self.login_as(self.ali)
        payload = {"wallet": wallet.id, "category": cat.id, "summa": 1000}
        expense = self.api.post(f"{API}/expenses/", payload, format="json").json()
        self.assertEqual(self.api.delete(f"{API}/expense-categories/{cat.id}/").status_code, 204)
        cat.refresh_from_db()
        self.assertFalse(cat.status)
        self.assertNotIn(cat.id, self.ids("expense-categories"))
        self.assertEqual(Expense.objects.get(pk=expense["id"]).category_id, cat.id)

    def test_deleting_global_category_only_hides_it_for_that_user(self):
        self.login_as(self.ali)
        self.assertEqual(self.api.delete(f"{API}/expense-categories/{self.global_cat.id}/").status_code, 204)
        self.global_cat.refresh_from_db()
        self.assertTrue(self.global_cat.status)
        self.assertNotIn(self.global_cat.id, self.ids("expense-categories"))
        self.login_as(self.vali)
        self.assertIn(self.global_cat.id, self.ids("expense-categories"))

    def test_hidden_category_is_flagged_and_can_be_restored(self):
        self.ali.hidden_expense_categories.add(self.global_cat)
        self.login_as(self.ali)
        everything = rows(self.api.get(f"{API}/expense-categories/?include_hidden=1"))
        row = next(c for c in everything if c["id"] == self.global_cat.id)
        self.assertTrue(row["hidden"])
        self.assertFalse(row["is_custom"])
        self.assertEqual(self.api.post(f"{API}/expense-categories/{self.global_cat.id}/restore/").status_code, 200)
        self.assertIn(self.global_cat.id, self.ids("expense-categories"))

    def test_cannot_delete_or_restore_other_users_private_category(self):
        private = ExpenseCategory.objects.create(name="Shaxsiy", user=self.ali)
        self.login_as(self.vali)
        self.assertEqual(self.api.post(f"{API}/expense-categories/{private.id}/restore/").status_code, 404)
        self.assertEqual(self.api.delete(f"{API}/expense-categories/{private.id}/").status_code, 404)
        private.refresh_from_db()
        self.assertTrue(private.status)

    def test_duplicate_category_name_is_rejected(self):
        self.login_as(self.ali)
        res = self.api.post(f"{API}/expense-categories/", {"name": "oziq-OVQAT"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("allaqachon", res.json()["name"][0])

    def test_name_of_a_category_hidden_by_me_can_be_reused(self):
        self.ali.hidden_expense_categories.add(self.global_cat)
        self.login_as(self.ali)
        res = self.api.post(f"{API}/expense-categories/", {"name": "Oziq-ovqat"}, format="json")
        self.assertEqual(res.status_code, 201)

    def test_anonymous_cannot_delete_or_restore(self):
        self.assertIn(self.api.delete(f"{API}/expense-categories/{self.global_cat.id}/").status_code, (401, 403))
        self.assertIn(self.api.post(f"{API}/expense-categories/{self.global_cat.id}/restore/").status_code, (401, 403))

    def test_income_categories_can_be_hidden_and_restored(self):
        cat = Category.objects.create(name="Oylik")
        self.login_as(self.ali)
        self.assertEqual(self.api.delete(f"{API}/categories/{cat.id}/").status_code, 204)
        self.assertEqual(self.ids("categories"), [])
        self.assertEqual(self.api.post(f"{API}/categories/{cat.id}/restore/").status_code, 200)
        self.assertEqual(self.ids("categories"), [cat.id])

    def test_staff_can_modify_global_category(self):
        self.login_as(make_user("admin", is_staff=True))
        res = self.api.patch(f"{API}/expense-categories/{self.global_cat.id}/", {"name": "Yangilandi"}, format="json")
        self.assertEqual(res.status_code, 200)

    def test_income_categories_are_scoped_too(self):
        Category.objects.create(name="Oylik")
        Category.objects.create(name="Shaxsiy daromad", user=self.ali)
        self.login_as(self.vali)
        self.assertEqual([c["name"] for c in rows(self.api.get(f"{API}/categories/"))], ["Oylik"])

    def test_cannot_use_other_users_private_category(self):
        private = ExpenseCategory.objects.create(name="Shaxsiy", user=self.ali)
        wallet = make_wallet(self.vali, 100000)
        self.login_as(self.vali)
        res = self.api.post(f"{API}/expenses/", {"wallet": wallet.id, "category": private.id, "summa": 1000}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Expense.objects.count(), 0)


class OwnershipTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.victim = make_user("qurbon")
        self.thief = make_user("ogri")
        self.victim_wallet = make_wallet(self.victim, 1_000_000)
        self.thief_wallet = make_wallet(self.thief, 0)
        self.exp_cat = ExpenseCategory.objects.create(name="Turkum")
        self.inc_cat = Category.objects.create(name="Manba")
        self.login_as(self.thief)

    def balance(self, wallet):
        wallet.refresh_from_db()
        return wallet.summa

    def test_wallet_list_and_detail_are_private(self):
        self.assertEqual([w["id"] for w in rows(self.api.get(f"{API}/wallets/"))], [self.thief_wallet.id])
        self.assertEqual(self.api.get(f"{API}/wallets/{self.victim_wallet.id}/").status_code, 404)

    def test_cannot_spend_from_other_wallet(self):
        payload = {"wallet": self.victim_wallet.id, "category": self.exp_cat.id, "summa": 5000}
        self.assertEqual(self.api.post(f"{API}/expenses/", payload, format="json").status_code, 400)
        self.assertEqual(self.balance(self.victim_wallet), 1_000_000)

    def test_cannot_add_income_to_other_wallet(self):
        payload = {"wallet": self.victim_wallet.id, "category": self.inc_cat.id, "summa": 5000}
        self.assertEqual(self.api.post(f"{API}/incomes/", payload, format="json").status_code, 400)
        self.assertEqual(self.balance(self.victim_wallet), 1_000_000)

    def test_cannot_transfer_from_other_wallet(self):
        payload = {"from_wallet": self.victim_wallet.id, "to_wallet": self.thief_wallet.id, "summa": 300000}
        self.assertEqual(self.api.post(f"{API}/transfers/", payload, format="json").status_code, 400)
        self.assertEqual(self.balance(self.victim_wallet), 1_000_000)
        self.assertEqual(self.balance(self.thief_wallet), 0)

    def test_cannot_lend_from_other_wallet(self):
        payload = {"person_name": "X", "debt_type": "give", "summa": 100000, "wallet": self.victim_wallet.id}
        self.assertEqual(self.api.post(f"{API}/debts/", payload, format="json").status_code, 400)
        self.assertEqual(self.balance(self.victim_wallet), 1_000_000)

    def test_cannot_see_or_delete_other_users_records(self):
        expense = Expense.objects.create(user=self.victim, wallet=self.victim_wallet, category=self.exp_cat, summa=1000)
        self.assertEqual(rows(self.api.get(f"{API}/expenses/")), [])
        self.assertEqual(self.api.delete(f"{API}/expenses/{expense.id}/").status_code, 404)


class BalanceTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user("ali")
        self.wallet = make_wallet(self.user, 100000)
        self.other = make_wallet(self.user, 0, name="Ikkinchi")
        self.exp_cat = ExpenseCategory.objects.create(name="Turkum")
        self.inc_cat = Category.objects.create(name="Manba")
        self.login_as(self.user)

    def balance(self, wallet):
        wallet.refresh_from_db()
        return wallet.summa

    def test_income_increases_balance(self):
        payload = {"wallet": self.wallet.id, "category": self.inc_cat.id, "summa": 50000}
        self.assertEqual(self.api.post(f"{API}/incomes/", payload, format="json").status_code, 201)
        self.assertEqual(self.balance(self.wallet), 150000)

    def test_expense_decreases_balance_and_delete_refunds(self):
        payload = {"wallet": self.wallet.id, "category": self.exp_cat.id, "summa": 30000}
        res = self.api.post(f"{API}/expenses/", payload, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(self.balance(self.wallet), 70000)
        self.assertEqual(self.api.delete(f"{API}/expenses/{res.json()['id']}/").status_code, 200)
        self.assertEqual(self.balance(self.wallet), 100000)

    def test_expense_over_balance_is_rejected(self):
        payload = {"wallet": self.wallet.id, "category": self.exp_cat.id, "summa": 100001}
        self.assertEqual(self.api.post(f"{API}/expenses/", payload, format="json").status_code, 400)
        self.assertEqual(self.balance(self.wallet), 100000)
        self.assertEqual(Expense.objects.count(), 0)

    def test_transfer_moves_money(self):
        payload = {"from_wallet": self.wallet.id, "to_wallet": self.other.id, "summa": 40000}
        self.assertEqual(self.api.post(f"{API}/transfers/", payload, format="json").status_code, 201)
        self.assertEqual((self.balance(self.wallet), self.balance(self.other)), (60000, 40000))

    def test_transfer_to_same_wallet_is_rejected(self):
        payload = {"from_wallet": self.wallet.id, "to_wallet": self.wallet.id, "summa": 1000}
        self.assertEqual(self.api.post(f"{API}/transfers/", payload, format="json").status_code, 400)

    def test_negative_or_zero_amount_is_rejected(self):
        for summa in (0, -500):
            with self.subTest(summa=summa):
                payload = {"wallet": self.wallet.id, "category": self.exp_cat.id, "summa": summa}
                self.assertEqual(self.api.post(f"{API}/expenses/", payload, format="json").status_code, 400)
        self.assertEqual(self.balance(self.wallet), 100000)


class DebtTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user("ali")
        self.wallet = make_wallet(self.user, summa=1_000_000)
        self.login_as(self.user)

    def create_debt(self, summa, debt_type="take"):
        res = self.api.post(f"{API}/debts/", {"person_name": "Rustam", "debt_type": debt_type, "summa": summa,
                                              "wallet": self.wallet.id}, format="json")
        return res.json()

    def balance(self):
        self.wallet.refresh_from_db()
        return self.wallet.summa

    def test_debt_without_wallet_is_rejected(self):
        base = {"person_name": "Rustam", "debt_type": "take", "summa": 1000}
        for payload in (base, {**base, "wallet": None}):
            with self.subTest(payload=payload):
                self.assertEqual(self.api.post(f"{API}/debts/", payload, format="json").status_code, 400)
        self.assertFalse(Debt.objects.exists())

    def test_given_debt_leaves_wallet_and_taken_debt_enters_it(self):
        self.create_debt(300_000, debt_type="give")
        self.assertEqual(self.balance(), 700_000)
        self.create_debt(500_000, debt_type="take")
        self.assertEqual(self.balance(), 1_200_000)

    def test_partial_then_full_repayment_settles_debt(self):
        debt = self.create_debt(500000)
        self.assertEqual(self.api.post(f"{API}/debts/{debt['id']}/repay/", {"amount": 200000, "wallet": self.wallet.id}, format="json").status_code, 200)
        self.assertFalse(Debt.objects.get(pk=debt["id"]).is_settled)
        self.assertEqual(self.api.post(f"{API}/debts/{debt['id']}/repay/", {"amount": 300000, "wallet": self.wallet.id}, format="json").status_code, 200)
        self.assertTrue(Debt.objects.get(pk=debt["id"]).is_settled)

    def test_overpayment_is_rejected(self):
        debt = self.create_debt(1000)
        res = self.api.post(f"{API}/debts/{debt['id']}/repay/", {"amount": 1001}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Debt.objects.get(pk=debt["id"]).paid_summa, 0)

    def test_debt_status_and_paid_summa_are_not_writable(self):
        debt = self.create_debt(1000)
        url = f"{API}/debts/{debt['id']}/"
        self.api.patch(url, {"status": False, "paid_summa": 1000, "is_settled": True}, format="json")
        obj = Debt.objects.get(pk=debt["id"])
        self.assertTrue(obj.status)
        self.assertEqual(obj.paid_summa, 0)
        self.assertFalse(obj.is_settled)

    def test_expense_list_ignores_invalid_year_month(self):
        res = self.api.get(f"{API}/expenses/", {"year": "abc", "month": "99"})
        self.assertEqual(res.status_code, 200)

    def test_monthly_stats_handles_extreme_year(self):
        res = self.api.get(f"{API}/stats/monthly/", {"year": "99999", "month": "1"})
        self.assertNotEqual(res.status_code, 500)

    def test_debt_requires_positive_amount(self):
        res = self.api.post(f"{API}/debts/", {"person_name": "X", "debt_type": "take", "summa": 0,
                                              "wallet": self.wallet.id}, format="json")
        self.assertEqual(res.status_code, 400)


class AccountDeletionTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user("ali", first_name="Ali", last_name="Valiyev", email="ali@example.com", phone="+998901234567")
        self.wallet = make_wallet(self.user, 50000)
        category = ExpenseCategory.objects.create(name="T")
        self.expense = Expense.objects.create(user=self.user, wallet=self.wallet, category=category, summa=1000)
        self.login_as(self.user)

    def delete_account(self, password):
        return self.api.post(f"{API}/auth/delete-account/", {"password": password}, format="json")

    def test_wrong_or_empty_password_keeps_account(self):
        self.assertEqual(self.delete_account("xato-parol").status_code, 400)
        self.assertEqual(self.delete_account("").status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertEqual(self.user.username, "ali")

    def test_requires_authentication(self):
        self.api.force_authenticate(None)
        self.assertIn(self.delete_account(PASSWORD).status_code, (401, 403))

    def test_deleted_account_is_removed_completely(self):
        self.assertEqual(self.delete_account(PASSWORD).status_code, 200)
        # Qator ham, email/ism/telefon ham bazada qolmaydi
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        self.assertFalse(User.objects.filter(username="ali").exists())

        res = APIClient().post(f"{API}/auth/login/", {"username": "ali", "password": PASSWORD}, format="json")
        self.assertEqual(res.status_code, 401)

    def test_username_is_freed_for_reuse(self):
        self.delete_account(PASSWORD)
        res = APIClient().post(f"{API}/auth/register/", {"username": "ali", "password": PASSWORD}, format="json")
        self.assertEqual(res.status_code, 201)

    def test_financial_history_is_removed_too(self):
        self.delete_account(PASSWORD)
        self.assertFalse(Expense.objects.filter(pk=self.expense.pk).exists())
        self.assertFalse(Wallet.objects.filter(pk=self.wallet.pk).exists())


class WalletEditTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user("ali")
        self.wallet = make_wallet(self.user, 75000, name="Eski nom")
        self.login_as(self.user)

    def patch(self, payload, wallet=None):
        return self.api.patch(f"{API}/wallets/{(wallet or self.wallet).id}/", payload, format="json")

    def test_can_rename_and_change_currency(self):
        res = self.patch({"name": "Yangi nom", "currency": "usd"})
        self.assertEqual(res.status_code, 200)
        self.wallet.refresh_from_db()
        self.assertEqual((self.wallet.name, self.wallet.currency), ("Yangi nom", "USD"))
        self.assertEqual(self.wallet.summa, 75000)

    def test_balance_can_be_edited_directly(self):
        # Foydalanuvchi qarori (2026-10-28): qoldiq tahrirda shunchaki almashtiriladi, kirim/chiqim yozilmaydi
        self.assertEqual(self.patch({"summa": "1250.50"}).status_code, 200)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.summa, Decimal("1250.50"))
        self.assertFalse(self.wallet.incomes.exists() or self.wallet.expenses.exists())

    def test_balance_edit_rejects_negative_and_huge(self):
        for value in ("-1", "1000000000001"):
            self.assertEqual(self.patch({"summa": value}).status_code, 400, value)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.summa, 75000)

    def test_blank_name_or_currency_is_rejected_with_readable_message(self):
        res = self.patch({"name": ""})
        self.assertEqual(res.status_code, 400)
        self.assertIn("bo'sh", res.json()["name"][0])
        self.assertEqual(self.patch({"currency": ""}).status_code, 400)
        self.assertEqual(self.patch({"currency": "X" * 11}).status_code, 400)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.name, "Eski nom")

    def test_other_user_cannot_edit_wallet(self):
        self.login_as(make_user("vali"))
        self.assertEqual(self.patch({"name": "Buzildi"}).status_code, 404)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.name, "Eski nom")


class WalletOperationsFilterTests(APITestCase):
    """Hamyon sahifasi shu so'rovlarga tayanadi: har bir turdagi yozuvlar hamyon bo'yicha filtrlanadi"""

    def setUp(self):
        super().setUp()
        self.user = make_user("ali")
        self.a = make_wallet(self.user, 1_000_000, name="A")
        self.b = make_wallet(self.user, 1_000_000, name="B")
        self.exp_cat = ExpenseCategory.objects.create(name="Turkum")
        self.inc_cat = Category.objects.create(name="Manba")
        self.login_as(self.user)

    def post(self, path, payload):
        res = self.api.post(f"{API}/{path}/", payload, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        return res.json()

    def ids(self, path):
        return sorted(row["id"] for row in rows(self.api.get(f"{API}/{path}")))

    def test_each_resource_filters_by_wallet(self):
        inc_a = self.post("incomes", {"wallet": self.a.id, "category": self.inc_cat.id, "summa": 1000})
        inc_b = self.post("incomes", {"wallet": self.b.id, "category": self.inc_cat.id, "summa": 2000})
        exp_a = self.post("expenses", {"wallet": self.a.id, "category": self.exp_cat.id, "summa": 3000})
        exp_b = self.post("expenses", {"wallet": self.b.id, "category": self.exp_cat.id, "summa": 4000})
        out_a = self.post("transfers", {"from_wallet": self.a.id, "to_wallet": self.b.id, "summa": 5000})
        in_a = self.post("transfers", {"from_wallet": self.b.id, "to_wallet": self.a.id, "summa": 6000})
        debt_a = self.post("debts", {"person_name": "X", "debt_type": "take", "summa": 7000, "wallet": self.a.id})
        self.post("debts", {"person_name": "Y", "debt_type": "take", "summa": 8000, "wallet": self.b.id})

        self.assertEqual(self.ids(f"incomes/?wallet={self.a.id}"), [inc_a["id"]])
        self.assertEqual(self.ids(f"incomes/?wallet={self.b.id}"), [inc_b["id"]])
        self.assertEqual(self.ids(f"expenses/?wallet={self.a.id}"), [exp_a["id"]])
        self.assertEqual(self.ids(f"expenses/?wallet={self.b.id}"), [exp_b["id"]])
        self.assertEqual(self.ids(f"transfers/?from_wallet={self.a.id}"), [out_a["id"]])
        self.assertEqual(self.ids(f"transfers/?to_wallet={self.a.id}"), [in_a["id"]])
        self.assertEqual(self.ids(f"debts/?wallet={self.a.id}"), [debt_a["id"]])

    def balances(self):
        res = self.api.get(f"{API}/wallets/summary/")
        self.assertEqual(res.status_code, 200)
        return res.json()["balances_by_currency"]

    def test_balance_is_summed_per_currency(self):
        make_wallet(self.user, 100000, name="UZS 3")
        Wallet.objects.create(user=self.user, name="Dollar", summa=1200, currency="USD")
        # eski yozuvlarda valyuta kichik harfda bo'lishi mumkin: bir guruhga tushadi
        Wallet.objects.create(user=self.user, name="Dollar 2", summa=300, currency="usd")
        self.assertEqual(self.balances(), [
            {"currency": "UZS", "total": 2_100_000},
            {"currency": "USD", "total": 1500},
        ])

    def test_uzs_goes_first_and_other_currencies_are_sorted(self):
        Wallet.objects.filter(user=self.user).delete()
        Wallet.objects.create(user=self.user, name="E", summa=5, currency="EUR")
        Wallet.objects.create(user=self.user, name="U", summa=7, currency="USD")
        Wallet.objects.create(user=self.user, name="S", summa=9, currency="UZS")
        self.assertEqual([b["currency"] for b in self.balances()], ["UZS", "EUR", "USD"])

    def test_balance_ignores_other_users_and_deleted_wallets(self):
        make_wallet(make_user("vali"), 999999)
        Wallet.objects.create(user=self.user, name="Eski", summa=777, currency="UZS", status=False)
        self.assertEqual(self.balances(), [{"currency": "UZS", "total": 2_000_000}])

    def test_no_wallets_gives_empty_balance_list(self):
        Wallet.objects.filter(user=self.user).delete()
        self.assertEqual(self.balances(), [])

    def test_large_limit_returns_every_record(self):
        for _ in range(12):
            self.post("incomes", {"wallet": self.a.id, "category": self.inc_cat.id, "summa": 100})
        self.assertEqual(len(self.ids(f"incomes/?wallet={self.a.id}&limit=200&offset=0")), 12)
        self.assertEqual(len(self.ids(f"incomes/?wallet={self.a.id}")), 10)  # standart sahifa hajmi


class DateRangeFilterTests(APITestCase):
    """?date_from=&date_to= (YYYY-MM-DD): ikkala kun ham kiradi, kun mahalliy (Toshkent) vaqt bo'yicha hisoblanadi"""

    PATHS = ("incomes", "expenses", "transfers")
    # Har bir turdan shu mahalliy vaqtlarning har biriga bittadan yozuv yaratiladi
    MOMENTS = [
        datetime(2026, 9, 30, 0, 30),    # UTC bo'yicha 29-sentyabr 19:30: kun UTC bo'yicha olinsa 29-ga tushib qolardi
        datetime(2026, 10, 1, 0, 0),     # kun boshi
        datetime(2026, 10, 10, 23, 59),  # kun oxiri
        datetime(2026, 10, 11, 0, 0),
        datetime(2026, 10, 20, 12, 0),
    ]
    ALL = ["2026-09-30", "2026-10-01", "2026-10-10", "2026-10-11", "2026-10-20"]

    def setUp(self):
        super().setUp()
        self.user = make_user("ali")
        a = make_wallet(self.user, 1_000_000, name="A")
        b = make_wallet(self.user, 0, name="B")
        inc_cat = Category.objects.create(name="Manba")
        exp_cat = ExpenseCategory.objects.create(name="Turkum")
        for moment in self.MOMENTS:
            when = timezone.make_aware(moment)
            Income.objects.create(user=self.user, wallet=a, category=inc_cat, summa=100, date=when)
            Expense.objects.create(user=self.user, wallet=a, category=exp_cat, summa=100, date=when)
            Transfer.objects.create(user=self.user, from_wallet=a, to_wallet=b, summa=10, date=when)
        self.login_as(self.user)

    def days(self, path, **params):
        res = self.api.get(f"{API}/{path}/", params)
        self.assertEqual(res.status_code, 200, res.content)
        return sorted(row["date"][:10] for row in rows(res))

    def check_all(self, expected, **params):
        for path in self.PATHS:
            with self.subTest(path=path, params=params):
                self.assertEqual(self.days(path, **params), expected)

    def test_without_params_everything_is_returned(self):
        self.check_all(self.ALL)

    def test_range_includes_both_boundary_days(self):
        # 1-oktyabr 00:00 va 10-oktyabr 23:59 kiradi; 30-sentyabr 00:30 va 11-oktyabr 00:00 kirmaydi
        self.check_all(["2026-10-01", "2026-10-10"], date_from="2026-10-01", date_to="2026-10-10")

    def test_range_uses_local_day_not_utc_day(self):
        # 30-sentyabr 00:30 (Toshkent) UTC bo'yicha 29-sentyabrga tushadi, lekin mahalliy kun 30-sentyabr
        self.check_all(["2026-09-30"], date_from="2026-09-30", date_to="2026-09-30")
        self.check_all([], date_from="2026-09-29", date_to="2026-09-29")

    def test_single_day_range(self):
        self.check_all(["2026-10-11"], date_from="2026-10-11", date_to="2026-10-11")

    def test_only_date_from_is_open_ended(self):
        self.check_all(["2026-10-10", "2026-10-11", "2026-10-20"], date_from="2026-10-10")

    def test_only_date_to_is_open_ended(self):
        self.check_all(["2026-09-30", "2026-10-01"], date_to="2026-10-01")

    def test_swapped_bounds_are_swapped_back(self):
        self.check_all(["2026-10-01", "2026-10-10"], date_from="2026-10-10", date_to="2026-10-01")

    def test_invalid_values_are_ignored(self):
        bad = ("abc", "2026-13-01", "2026-02-30", "20261005", "2026-1-5", "2026-10-05T12:00:00", "2026-W41-1",
               "0001-01-01", "1899-12-31", "2101-01-01", "9999-12-31", "-2026-10-01", "")
        for value in bad:
            # ikkala chegara ham yaroqsiz — filtr umuman qo'llanmaydi
            self.check_all(self.ALL, date_from=value, date_to=value)
        # bittasi yaroqsiz — ikkinchisi yolg'iz ishlaydi
        self.check_all(["2026-10-10", "2026-10-11", "2026-10-20"], date_from="2026-10-10", date_to="abc")
        self.check_all(["2026-09-30", "2026-10-01"], date_from="abc", date_to="2026-10-01")

    def test_invalid_range_falls_back_to_year_and_month(self):
        self.check_all(["2026-09-30"], date_from="abc", date_to="9999-12-31", year=2026, month=9)

    def test_range_takes_precedence_over_year_and_month(self):
        self.check_all(["2026-10-01", "2026-10-10"], date_from="2026-10-01", date_to="2026-10-10", year=2026, month=9)
        # bitta yaroqli chegara ham year/month ni o'chiradi
        self.check_all(["2026-10-10", "2026-10-11", "2026-10-20"], date_from="2026-10-10", year=2026, month=9)

    def test_year_and_month_still_work_without_range(self):
        self.check_all(["2026-09-30"], year=2026, month=9)
        self.check_all(["2026-10-01", "2026-10-10", "2026-10-11", "2026-10-20"], year=2026, month=10)

    def test_other_users_records_are_not_included(self):
        vali = make_user("vali")
        Expense.objects.create(user=vali, wallet=make_wallet(vali, 1000), category=ExpenseCategory.objects.create(name="X"),
                               summa=5, date=timezone.make_aware(datetime(2026, 10, 5, 12)))
        self.check_all(["2026-10-01", "2026-10-10"], date_from="2026-10-01", date_to="2026-10-10")


# ==========================================
# Valyuta kursi, hamyon PIN-kodi, login cheklovi
# ==========================================

FAKE_RATES = {"USD": (Decimal("12000"), "08.10.2026"), "EUR": (Decimal("13000"), "08.10.2026")}


@mock.patch("mainapp.currency._fetch_cbu", return_value=FAKE_RATES)
class CurrencyTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user("ali")
        self.uzs = make_wallet(self.user, 1_000_000, name="So'm")
        self.usd = Wallet.objects.create(user=self.user, name="Dollar", summa=500, currency="USD")
        self.login_as(self.user)

    def balance(self, wallet):
        wallet.refresh_from_db()
        return wallet.summa

    def transfer(self, **payload):
        return self.api.post(f"{API}/transfers/", payload, format="json")

    def test_cross_currency_transfer_uses_central_bank_rate(self, _fetch):
        res = self.transfer(from_wallet=self.usd.id, to_wallet=self.uzs.id, summa=100)
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()["to_summa"], 1_200_000)
        self.assertEqual(Decimal(res.json()["rate"]), Decimal("12000"))
        self.assertEqual((self.balance(self.usd), self.balance(self.uzs)), (400, 2_200_000))

    def test_reverse_direction_rounds_to_cents(self, _fetch):
        res = self.transfer(from_wallet=self.uzs.id, to_wallet=self.usd.id, summa=125_000)
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()["to_summa"], 10.42)  # 125 000 / 12 000 = 10.4166.. -> 10.42
        self.assertEqual(self.balance(self.usd), Decimal("510.42"))

    def test_manual_to_summa_overrides_rate(self, _fetch):
        res = self.transfer(from_wallet=self.usd.id, to_wallet=self.uzs.id, summa=100, to_summa=1_190_000)
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(self.balance(self.uzs), 2_190_000)
        self.assertEqual(Decimal(res.json()["rate"]), Decimal("11900"))

    def test_same_currency_ignores_to_summa(self, _fetch):
        other = make_wallet(self.user, 0, name="Karta")
        res = self.transfer(from_wallet=self.uzs.id, to_wallet=other.id, summa=1000, to_summa=999_999)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(self.balance(other), 1000)
        _fetch.assert_not_called()

    def test_deleting_cross_currency_transfer_restores_both_wallets(self, _fetch):
        res = self.transfer(from_wallet=self.usd.id, to_wallet=self.uzs.id, summa=100)
        self.assertEqual(self.api.delete(f"{API}/transfers/{res.json()['id']}/").status_code, 200)
        self.assertEqual((self.balance(self.usd), self.balance(self.uzs)), (500, 1_000_000))

    def test_rate_is_cached_in_database(self, _fetch):
        self.transfer(from_wallet=self.usd.id, to_wallet=self.uzs.id, summa=1)
        self.transfer(from_wallet=self.usd.id, to_wallet=self.uzs.id, summa=1)
        self.assertEqual(_fetch.call_count, 1)
        self.assertEqual(ExchangeRate.objects.get(currency="USD").rate, Decimal("12000"))

    def test_offline_uses_last_stored_rate(self, _fetch):
        ExchangeRate.objects.create(currency="USD", rate=Decimal("11000"))
        ExchangeRate.objects.filter(currency="USD").update(updated_at=timezone.now() - timedelta(days=2))
        _fetch.side_effect = OSError("internet yo'q")
        with self.assertLogs("mainapp.currency", "WARNING"):
            res = self.transfer(from_wallet=self.usd.id, to_wallet=self.uzs.id, summa=1)
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()["to_summa"], 11000)

    def test_no_rate_at_all_asks_for_manual_amount(self, _fetch):
        _fetch.side_effect = OSError("internet yo'q")
        with self.assertLogs("mainapp.currency", "WARNING"):
            res = self.transfer(from_wallet=self.usd.id, to_wallet=self.uzs.id, summa=1)
        self.assertEqual(res.status_code, 400)
        self.assertIn("qo'lda kiriting", res.json()["error"])
        self.assertEqual(self.balance(self.usd), 500)
        # Qo'lda kiritilsa ishlaydi
        res = self.transfer(from_wallet=self.usd.id, to_wallet=self.uzs.id, summa=1, to_summa=11_500)
        self.assertEqual(res.status_code, 201)

    def test_wallet_currency_is_normalized_and_validated(self, _fetch):
        res = self.api.post(f"{API}/wallets/", {"name": "Naqd", "currency": "so'm"}, format="json")
        self.assertEqual(res.json()["currency"], "UZS")
        res = self.api.post(f"{API}/wallets/", {"name": "Naqd", "currency": "dollar"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_debt_takes_wallet_currency(self, _fetch):
        res = self.api.post(f"{API}/debts/", {"person_name": "Rustam", "debt_type": "take", "summa": 50,
                                              "wallet": self.usd.id, "currency": "UZS"}, format="json")
        self.assertEqual(res.json()["currency"], "USD")

    def test_repay_into_other_currency_wallet_is_converted(self, _fetch):
        debt = self.api.post(f"{API}/debts/", {"person_name": "Rustam", "debt_type": "give", "summa": 100,
                                               "wallet": self.usd.id}, format="json").json()
        self.assertEqual(debt["currency"], "USD")
        res = self.api.post(f"{API}/debts/{debt['id']}/repay/", {"amount": 10, "wallet": self.uzs.id}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["wallet_amount"], 120_000)
        self.assertEqual(self.balance(self.uzs), 1_120_000)
        self.assertEqual(Debt.objects.get(pk=debt["id"]).paid_summa, 10)

    def test_convert_endpoint(self, _fetch):
        res = self.api.get(f"{API}/rates/convert/", {"from": "EUR", "to": "USD", "amount": 12})
        self.assertEqual(res.json()["result"], 13)  # 12 * 13000 / 12000 = 13


class BigAmountTests(APITestCase):
    def test_amounts_above_two_billion_work(self):
        user = make_user("boy")
        self.login_as(user)
        res = self.api.post(f"{API}/wallets/", {"name": "Katta", "summa": 5_000_000_000, "currency": "UZS"}, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        wallet_id = res.json()["id"]
        cat = ExpenseCategory.objects.create(name="Uy")
        res = self.api.post(f"{API}/expenses/", {"wallet": wallet_id, "category": cat.id, "summa": 3_000_000_000}, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(Wallet.objects.get(pk=wallet_id).summa, 2_000_000_000)


class LoginLockoutTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user("ali", email="ali@example.com")

    def login(self, password, username="ali"):
        return self.api.post(f"{API}/auth/login/", {"username": username, "password": password}, format="json")

    def test_five_failures_lock_the_login(self):
        for _ in range(4):
            self.assertEqual(self.login("xato").status_code, 401)
        self.assertEqual(self.login("xato").status_code, 429)
        self.assertEqual(self.login(PASSWORD).status_code, 429)

    def test_success_resets_counter(self):
        for _ in range(4):
            self.login("xato")
        self.assertEqual(self.login(PASSWORD).status_code, 200)
        self.api.post(f"{API}/auth/logout/")
        self.assertEqual(self.login("xato").status_code, 401)

    def test_remaining_attempts_are_shown_near_the_limit(self):
        for _ in range(3):
            res = self.login("xato")
        self.assertIn("2 ta urinish", res.json()["error"])

    def test_lock_is_per_login_and_case_insensitive(self):
        for _ in range(5):
            self.login("xato", username="ALI")
        self.assertEqual(self.login(PASSWORD, username="ali").status_code, 429)
        make_user("vali")
        self.assertEqual(self.login(PASSWORD, username="vali").status_code, 200)

    def test_lock_is_shared_between_username_and_email(self):
        for _ in range(3):
            self.login("xato", username="ali")
        for _ in range(2):
            self.login("xato", username="ALI@example.com")
        self.assertEqual(self.login(PASSWORD, username="ali").status_code, 429)
        self.assertEqual(self.login(PASSWORD, username="ali@example.com").status_code, 429)

    def test_unknown_login_is_still_locked(self):
        for _ in range(5):
            self.login("xato", username="yoq")
        self.assertEqual(self.login("xato", username="yoq").status_code, 429)


class SessionLifetimeTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.api.force_login(make_user("ali"))

    def later(self, seconds):
        return mock.patch("mainapp.middleware.time.time", return_value=time.time() + seconds)

    # Mutlaq muddat o'chirilgan (SESSION_MAX_AGE=None): sessiya faqat Chiqish/parol almashishda tugaydi.
    # Yoqilgan holatdagi xatti-harakat ham tekshiriladi — middleware kelajakda qayta yoqilishi mumkin
    @override_settings(SESSION_MAX_AGE=24 * 60 * 60)
    def test_session_ends_after_max_age_even_if_active_when_enabled(self):
        with self.later(settings.SESSION_MAX_AGE - 60):
            self.assertTrue(self.api.get(f"{API}/auth/me/").json()["authenticated"])
        with self.later(settings.SESSION_MAX_AGE + 1):
            self.assertFalse(self.api.get(f"{API}/auth/me/").json()["authenticated"])
        self.assertFalse(self.api.get(f"{API}/auth/me/").json()["authenticated"])

    @override_settings(SESSION_MAX_AGE=24 * 60 * 60)
    def test_expired_session_gets_401_so_page_shows_login(self):
        with self.later(settings.SESSION_MAX_AGE + 1):
            self.assertEqual(self.api.get(f"{API}/wallets/").status_code, 401)

    def test_no_absolute_limit_by_default(self):
        self.assertIsNone(settings.SESSION_MAX_AGE)
        with self.later(400 * 24 * 60 * 60):
            self.assertEqual(self.api.get(f"{API}/wallets/").status_code, 200)

    def test_session_survives_browser_close(self):
        self.assertFalse(settings.SESSION_EXPIRE_AT_BROWSER_CLOSE)
        self.assertGreaterEqual(settings.SESSION_COOKIE_AGE, 365 * 24 * 60 * 60)
        self.assertGreaterEqual(self.api.session.get_expiry_age(), 364 * 24 * 60 * 60)


class MonthlyTrendTests(APITestCase):
    def test_daily_trend_puts_amounts_on_the_right_day(self):
        user = make_user("ali")
        wallet = make_wallet(user, 100_000)
        cat = ExpenseCategory.objects.create(name="Ovqat")
        # Toshkentda 5-mart 02:30 = UTC bo'yicha 4-mart 21:30: kun UTC bo'yicha hisoblansa 4-kunga tushib qolardi
        Expense.objects.create(user=user, wallet=wallet, category=cat, summa=700,
                               date=timezone.make_aware(datetime(2026, 3, 5, 2, 30)))
        self.login_as(user)
        trend = self.api.get(f"{API}/stats/monthly/", {"year": 2026, "month": 3}).json()["daily_trend"]
        self.assertEqual(len(trend), 31)
        self.assertEqual(trend[4], {"date": "2026-03-05", "day": 5, "income": 0, "expense": 700})
        self.assertEqual(sum(d["expense"] for d in trend), 700)


class DateRangeStatsTests(APITestCase):
    """/stats/monthly/?date_from=&date_to= — oraliq rejimi; faqat ikkala sana ham to'g'ri bo'lsa yoqiladi"""

    def setUp(self):
        super().setUp()
        self.user = make_user("ali")
        self.wallet = make_wallet(self.user, 100_000_000)
        self.inc_cat = Category.objects.create(name="Oylik")
        self.exp_cat = ExpenseCategory.objects.create(name="Ovqat")
        self.login_as(self.user)
        # Oraliq 30-sentyabr..2-oktyabr (oy chegarasidan o'tadi); oldingi davr (3 kun) — 27..29-sentyabr
        self.expense(datetime(2026, 9, 26, 12), 7_000)   # oldingi davrdan ham oldin
        self.expense(datetime(2026, 9, 29, 12), 100)     # oldingi davr
        self.expense(datetime(2026, 9, 30, 0, 30), 200)  # UTC bo'yicha 29-sentyabr 19:30, mahalliy kun — 30-sentyabr
        self.expense(datetime(2026, 10, 1, 12), 300)
        self.expense(datetime(2026, 10, 2, 23, 30), 400)
        self.expense(datetime(2026, 10, 3, 0, 0), 5_000)  # oraliqdan keyin
        self.income(datetime(2026, 9, 28, 10), 500)       # oldingi davr
        self.income(datetime(2026, 10, 1, 9), 1_000)

    def income(self, moment, summa):
        return Income.objects.create(user=self.user, wallet=self.wallet, category=self.inc_cat, summa=summa,
                                     date=timezone.make_aware(moment))

    def expense(self, moment, summa):
        return Expense.objects.create(user=self.user, wallet=self.wallet, category=self.exp_cat, summa=summa,
                                      date=timezone.make_aware(moment))

    def stats(self, **params):
        res = self.api.get(f"{API}/stats/monthly/", params)
        self.assertEqual(res.status_code, 200, res.content)
        return res.json()

    def test_range_totals_and_categories(self):
        data = self.stats(date_from="2026-09-30", date_to="2026-10-02")
        self.assertEqual(data["total_expense"], 900)
        self.assertEqual(data["total_income"], 1_000)
        self.assertEqual(data["net_savings"], 100)
        self.assertEqual([c["total"] for c in data["category_expenses"]], [900])
        self.assertEqual([c["total"] for c in data["category_incomes"]], [1_000])
        self.assertEqual((data["date_from"], data["date_to"]), ("2026-09-30", "2026-10-02"))
        # year/month — oraliq oxiridagi oy (javob shakli oy rejimi bilan mos)
        self.assertEqual((data["year"], data["month"]), (2026, 10))
        self.assertEqual(data["stats_currency"], "UZS")
        self.assertEqual(data["missing_rates"], [])

    def test_daily_trend_crosses_month_boundary(self):
        trend = self.stats(date_from="2026-09-30", date_to="2026-10-02")["daily_trend"]
        self.assertEqual(len(trend), 3)
        self.assertEqual([d["date"] for d in trend], ["2026-09-30", "2026-10-01", "2026-10-02"])
        self.assertEqual([d["day"] for d in trend], [30, 1, 2])
        self.assertEqual([d["expense"] for d in trend], [200, 300, 400])
        self.assertEqual([d["income"] for d in trend], [0, 1_000, 0])
        # kalitlar tartibi shartnomadagidek
        self.assertEqual(list(trend[0]), ["date", "day", "income", "expense"])

    def test_previous_period_is_equal_length_range_right_before(self):
        data = self.stats(date_from="2026-09-30", date_to="2026-10-02")  # 3 kun -> oldingi davr 27..29-sentyabr
        self.assertEqual(data["prev_expense"], 100)
        self.assertEqual(data["prev_income"], 500)
        self.assertEqual(data["expense_change"], 800.0)
        self.assertEqual(data["income_change"], 100.0)

    def test_percent_change_is_none_when_previous_period_is_empty(self):
        data = self.stats(date_from="2026-10-01", date_to="2026-10-02")  # oldingi davr 29..30-sentyabr: 100 + 200
        self.assertEqual(data["prev_expense"], 300)
        self.assertEqual(data["prev_income"], 0)
        self.assertIsNone(data["income_change"])

    def test_single_day_range_uses_local_day(self):
        data = self.stats(date_from="2026-09-29", date_to="2026-09-29")
        self.assertEqual(data["total_expense"], 100)  # 30-sentyabr 00:30 dagi 200 so'm kirmaydi
        self.assertEqual([d["date"] for d in data["daily_trend"]], ["2026-09-29"])

    def test_swapped_bounds_are_swapped_back(self):
        straight = self.stats(date_from="2026-09-30", date_to="2026-10-02")
        swapped = self.stats(date_from="2026-10-02", date_to="2026-09-30")
        self.assertEqual(swapped, straight)

    def test_range_takes_precedence_over_year_and_month(self):
        data = self.stats(date_from="2026-09-30", date_to="2026-10-02", year=2020, month=1)
        self.assertEqual(data["total_expense"], 900)
        self.assertEqual((data["year"], data["month"]), (2026, 10))

    def test_one_valid_bound_keeps_month_mode(self):
        # Oraliq faqat ikkala sana to'g'ri bo'lsa ishlaydi, aks holda year/month
        for params in ({"date_from": "2026-10-02"}, {"date_to": "2026-10-02"},
                       {"date_from": "abc", "date_to": "2026-10-02"}, {"date_from": "2026-10-02", "date_to": "2026-99-99"}):
            with self.subTest(params=params):
                data = self.stats(year=2026, month=9, **params)
                self.assertEqual((data["year"], data["month"]), (2026, 9))
                self.assertEqual((data["date_from"], data["date_to"]), ("2026-09-01", "2026-09-30"))
                self.assertEqual(len(data["daily_trend"]), 30)
                self.assertEqual(data["total_expense"], 7_000 + 100 + 200)

    def test_range_longer_than_366_days_is_rejected(self):
        for params in ({"date_from": "2028-01-01", "date_to": "2029-01-01"},  # 367 kun
                       {"date_from": "2029-01-01", "date_to": "2028-01-01"},  # teskari berilgan ham rad etiladi
                       {"date_from": "1900-01-01", "date_to": "2100-12-31"}):
            with self.subTest(params=params):
                res = self.api.get(f"{API}/stats/monthly/", params)
                self.assertEqual(res.status_code, 400)
                self.assertEqual(res.json(), {"error": "Oraliq 1 yildan oshmasligi kerak"})

    def test_range_of_exactly_366_days_is_allowed(self):
        data = self.stats(date_from="2028-01-01", date_to="2028-12-31")  # kabisa yili: 366 kun
        self.assertEqual(len(data["daily_trend"]), 366)
        self.assertEqual(data["daily_trend"][59]["date"], "2028-02-29")
        self.assertEqual(data["daily_trend"][-1]["date"], "2028-12-31")

    def test_extreme_bounds_never_crash(self):
        for params in ({"date_from": "1900-01-01", "date_to": "1900-01-31"},  # oldingi davr 1899 yilga tushadi
                       {"date_from": "2100-12-01", "date_to": "2100-12-31"},
                       {"date_from": "0001-01-01", "date_to": "9999-12-31"},  # yaroqsiz — oy rejimi
                       {"date_from": "abc", "date_to": "xyz"}):
            with self.subTest(params=params):
                data = self.stats(**params)
                span = datetime.fromisoformat(data["date_to"]) - datetime.fromisoformat(data["date_from"])
                self.assertEqual(len(data["daily_trend"]), span.days + 1)

    def test_month_mode_adds_date_and_month_bounds(self):
        data = self.stats(year=2028, month=2)  # kabisa yili
        self.assertEqual((data["date_from"], data["date_to"]), ("2028-02-01", "2028-02-29"))
        trend = data["daily_trend"]
        self.assertEqual(len(trend), 29)
        self.assertEqual(trend[0], {"date": "2028-02-01", "day": 1, "income": 0, "expense": 0})
        self.assertEqual(trend[-1]["date"], "2028-02-29")
        self.assertEqual([d["day"] for d in trend], list(range(1, 30)))

    def test_month_mode_counts_local_calendar_days_and_previous_month(self):
        self.expense(datetime(2025, 12, 31, 23, 0), 50)      # yanvarning oldingi davri (yil almashadi)
        self.expense(datetime(2026, 1, 1, 0, 30), 10)        # UTC bo'yicha 31-dekabr, mahalliy kun — 1-yanvar
        self.expense(datetime(2026, 1, 31, 23, 30), 20)
        self.expense(datetime(2026, 2, 1, 0, 10), 400)       # fevralga tegishli
        data = self.stats(year=2026, month=1)
        self.assertEqual(data["total_expense"], 30)
        self.assertEqual(data["prev_expense"], 50)
        self.assertEqual(data["expense_change"], -40.0)
        feb = self.stats(year=2026, month=2)
        self.assertEqual(feb["total_expense"], 400)
        self.assertEqual(feb["prev_expense"], 30)


@mock.patch("mainapp.currency._fetch_cbu", return_value=FAKE_RATES)
class StatsCurrencyTests(APITestCase):
    """Hisobotda dollar va so'm kurs bo'yicha so'mga o'girilib jamlanadi va saralanadi (1 USD = 12 000 UZS)"""

    def setUp(self):
        super().setUp()
        self.user = make_user("ali")
        self.uzs = make_wallet(self.user, 0, name="So'm")
        self.usd = Wallet.objects.create(user=self.user, name="Dollar", summa=0, currency="USD")
        self.salary = Category.objects.create(name="Oylik maosh")
        self.other = Category.objects.create(name="Boshqa daromad")
        self.food = ExpenseCategory.objects.create(name="Ovqat")
        self.taxi = ExpenseCategory.objects.create(name="Taksi")
        self.login_as(self.user)

    def income(self, wallet, category, summa):
        return Income.objects.create(user=self.user, wallet=wallet, category=category, summa=summa)

    def expense(self, wallet, category, summa):
        return Expense.objects.create(user=self.user, wallet=wallet, category=category, summa=summa)

    def monthly(self):
        res = self.api.get(f"{API}/stats/monthly/")
        self.assertEqual(res.status_code, 200)
        return res.json()

    def test_dollar_income_is_converted_and_ranked_first(self, _fetch):
        self.income(self.uzs, self.salary, 1_000_000)
        self.income(self.usd, self.other, 100)  # 100 USD = 1 200 000 UZS > 1 000 000 UZS
        data = self.monthly()
        self.assertEqual(data["total_income"], 2_200_000)
        self.assertEqual([c["name"] for c in data["category_incomes"]], ["Boshqa daromad", "Oylik maosh"])
        first = data["category_incomes"][0]
        self.assertEqual(first["total"], 1_200_000)
        self.assertEqual(first["parts"], [{"currency": "USD", "total": 100}])
        self.assertEqual(first["percent"], 54.5)
        self.assertEqual(data["stats_currency"], "UZS")
        self.assertEqual(data["missing_rates"], [])

    def test_same_category_in_two_currencies_is_summed(self, _fetch):
        self.income(self.uzs, self.salary, 500_000)
        self.income(self.usd, self.salary, 50)
        cat = self.monthly()["category_incomes"][0]
        self.assertEqual(cat["total"], 1_100_000)
        self.assertEqual(cat["parts"], [{"currency": "UZS", "total": 500_000}, {"currency": "USD", "total": 50}])

    def test_expenses_trend_and_previous_month_are_converted(self, _fetch):
        self.income(self.uzs, self.salary, 1_000_000)
        self.income(self.usd, self.other, 100)
        self.expense(self.uzs, self.food, 300_000)
        self.expense(self.usd, self.taxi, 30)  # 360 000 UZS
        data = self.monthly()
        self.assertEqual(data["total_expense"], 660_000)
        self.assertEqual(data["net_savings"], 1_540_000)
        self.assertEqual([c["name"] for c in data["category_expenses"]], ["Taksi", "Ovqat"])
        self.assertEqual(sum(d["expense"] for d in data["daily_trend"]), 660_000)
        self.assertEqual(sum(d["income"] for d in data["daily_trend"]), 2_200_000)

    def test_dashboard_summary_is_converted(self, _fetch):
        self.income(self.uzs, self.salary, 1_000_000)
        self.income(self.usd, self.other, 100)
        self.expense(self.usd, self.taxi, 30)
        Debt.objects.create(user=self.user, person_name="Rustam", debt_type="give", summa=10, currency="USD")
        data = self.api.get(f"{API}/wallets/summary/").json()
        self.assertEqual(data["monthly_income"], 2_200_000)
        self.assertEqual(data["monthly_expense"], 360_000)
        self.assertEqual(data["total_income"], 2_200_000)
        self.assertEqual(data["category_expenses"][0]["total"], 360_000)
        self.assertEqual(sum(d["expense"] for d in data["weekly_expenses"]), 360_000)
        self.assertEqual(data["debts_to_receive"], 120_000)

    def test_weekly_chart_keeps_original_currency_amounts(self, _fetch):
        self.income(self.uzs, self.salary, 1_000_000)
        self.income(self.usd, self.other, 100)
        self.expense(self.uzs, self.food, 50_000)
        self.expense(self.usd, self.taxi, 30)
        week = self.api.get(f"{API}/wallets/summary/").json()["weekly_expenses"]
        today = next(d for d in week if d["expense"])
        # Ustun uzunligi so'mda (50 000 + 30 * 12 000), yozuv uchun asl summalar
        self.assertEqual(today["expense"], 410_000)
        self.assertEqual(today["parts"], [{"currency": "UZS", "total": 50_000}, {"currency": "USD", "total": 30}])
        self.assertTrue(all(d["parts"] == [] for d in week if not d["expense"]))

    def test_currency_without_rate_is_reported_not_added_as_som(self, _fetch):
        xyz = Wallet.objects.create(user=self.user, name="Noma'lum", summa=0, currency="XYZ")
        self.income(self.uzs, self.salary, 1_000)
        self.income(xyz, self.other, 5)
        data = self.monthly()
        self.assertEqual(data["total_income"], 1_000)
        self.assertEqual(data["missing_rates"], ["XYZ"])
        other = next(c for c in data["category_incomes"] if c["name"] == "Boshqa daromad")
        self.assertEqual((other["total"], other["parts"]), (0, [{"currency": "XYZ", "total": 5}]))

    def test_rates_are_fetched_once_per_request(self, _fetch):
        self.income(self.usd, self.other, 1)
        self.expense(self.usd, self.taxi, 1)
        self.monthly()
        self.api.get(f"{API}/wallets/summary/")
        self.assertEqual(_fetch.call_count, 1)

    def test_only_som_data_never_touches_the_network(self, _fetch):
        self.income(self.uzs, self.salary, 1_000)
        self.monthly()
        self.api.get(f"{API}/wallets/summary/")
        _fetch.assert_not_called()


class PasswordResetTests(APITestCase):
    """Parolni tiklash: kod so'rash -> kodni tekshirish -> yangi parol"""

    NEW_PASSWORD = "Yangi-parol-777"

    def setUp(self):
        super().setUp()
        self.user = make_user("ali", email="ali@example.com")

    def request_code(self):
        res = self.api.post(f"{API}/auth/password-reset/", {"username": "ali"}, format="json")
        self.assertEqual(res.status_code, 200)
        return re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)

    def verify(self, code):
        return self.api.post(f"{API}/auth/password-reset/verify/", {"username": "ali", "code": code}, format="json")

    def confirm(self, code, password=None):
        return self.api.post(
            f"{API}/auth/password-reset/confirm/",
            {"username": "ali", "code": code, "new_password": password or self.NEW_PASSWORD},
            format="json",
        )

    def wrong(self, code):
        return "000000" if code != "000000" else "111111"

    def test_correct_code_is_verified_without_using_it(self):
        code = self.request_code()
        self.assertEqual(self.verify(code).status_code, 200)
        # Tekshiruvdan keyin ham kod amal qiladi — yangi parol shu kod bilan o'rnatiladi
        self.assertEqual(self.confirm(code).status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.NEW_PASSWORD))
        self.assertEqual(self.confirm(code).status_code, 400)

    def test_wrong_code_is_rejected_and_counts_attempts(self):
        code = self.request_code()
        res = self.verify(self.wrong(code))
        self.assertEqual(res.status_code, 400)
        # "Yana N ta urinish qoldi" endi aytilmaydi: u faqat mavjud akkauntda chiqib, uning borligini oshkor qilardi
        self.assertNotIn("urinish qoldi", res.json()["code"])
        for _ in range(4):
            self.verify(self.wrong(code))
        # Urinishlar tugagach to'g'ri kod ham qabul qilinmaydi
        self.assertEqual(self.verify(code).status_code, 400)
        self.assertEqual(self.confirm(code).status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_verify_requires_code(self):
        self.request_code()
        self.assertEqual(self.verify("").status_code, 400)


# ==========================================
# Xavfsizlik auditi tuzatishlari (2026-10-12)
# ==========================================

class ForeignWalletLeakTests(APITestCase):
    """Begona hamyon ID'si bilan so'rov yuborilganda uning qoldig'i yoki valyutasi xato xabarida ko'rinmasligi kerak"""

    def setUp(self):
        super().setUp()
        self.victim = make_user("qurbon")
        self.thief = make_user("ogri")
        self.victim_wallet = Wallet.objects.create(user=self.victim, name="Karta", summa=7_654_321, currency="UZS")
        self.thief_wallet = make_wallet(self.thief, 10)
        self.login_as(self.thief)

    def assert_no_leak(self, res):
        self.assertEqual(res.status_code, 400)
        body = res.content.decode()
        self.assertNotIn("7,654,321", body)
        self.assertNotIn("7654321", body)

    def test_debt_with_foreign_wallet_does_not_reveal_balance(self):
        res = self.api.post(f"{API}/debts/", {"person_name": "X", "debt_type": "give", "summa": 10 ** 12,
                                              "wallet": self.victim_wallet.id}, format="json")
        self.assert_no_leak(res)

    def test_transfer_from_foreign_wallet_does_not_reveal_balance(self):
        res = self.api.post(f"{API}/transfers/", {"from_wallet": self.victim_wallet.id, "to_wallet": self.thief_wallet.id,
                                                  "summa": 10 ** 12}, format="json")
        self.assert_no_leak(res)

    def test_foreign_and_missing_wallet_give_same_answer(self):
        payload = {"person_name": "X", "debt_type": "take", "summa": 100}
        foreign = self.api.post(f"{API}/debts/", {**payload, "wallet": self.victim_wallet.id}, format="json")
        missing = self.api.post(f"{API}/debts/", {**payload, "wallet": 999_999}, format="json")
        self.assertEqual(foreign.json(), missing.json())

    def test_deleted_wallet_cannot_receive_operations(self):
        wallet = make_wallet(self.thief, 0, name="Eski")
        wallet.delete()
        res = self.api.post(f"{API}/incomes/", {"wallet": wallet.id, "summa": 500}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertFalse(Income.objects.filter(wallet=wallet).exists())


class WalletCurrencyChangeTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user("ali")
        self.wallet = make_wallet(self.user, 1_000_000)
        self.login_as(self.user)

    def test_currency_cannot_change_once_wallet_has_operations(self):
        self.api.post(f"{API}/incomes/", {"wallet": self.wallet.id, "summa": 5000}, format="json")
        res = self.api.patch(f"{API}/wallets/{self.wallet.id}/", {"currency": "USD"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.currency, "UZS")

    def test_renaming_with_same_currency_still_works(self):
        self.api.post(f"{API}/incomes/", {"wallet": self.wallet.id, "summa": 5000}, format="json")
        res = self.api.patch(f"{API}/wallets/{self.wallet.id}/", {"name": "Yangi", "currency": "uzs"}, format="json")
        self.assertEqual(res.status_code, 200, res.content)


class AmountLimitTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user("ali")
        self.wallet = make_wallet(self.user, 10)
        self.login_as(self.user)

    def test_too_large_amount_is_rejected_and_balance_stays_integer(self):
        res = self.api.post(f"{API}/incomes/", {"wallet": self.wallet.id, "summa": 2 ** 63 - 1}, format="json")
        self.assertEqual(res.status_code, 400)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.summa, 10)

    def test_balance_cannot_grow_past_limit(self):
        Wallet.objects.filter(pk=self.wallet.pk).update(summa=MAX_AMOUNT)
        res = self.api.post(f"{API}/incomes/", {"wallet": self.wallet.id, "summa": 1}, format="json")
        self.assertEqual(res.status_code, 400)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.summa, MAX_AMOUNT)

    def test_new_wallet_and_debt_respect_limit(self):
        res = self.api.post(f"{API}/wallets/", {"name": "Katta", "summa": MAX_AMOUNT + 1}, format="json")
        self.assertEqual(res.status_code, 400)
        res = self.api.post(f"{API}/debts/", {"person_name": "X", "debt_type": "take", "summa": MAX_AMOUNT + 1,
                                              "wallet": self.wallet.id}, format="json")
        self.assertEqual(res.status_code, 400)


class PasswordWhitespaceTests(APITestCase):
    def test_password_with_surrounding_spaces_still_logs_in(self):
        user = make_user("ali")
        self.login_as(user)
        res = self.api.post(f"{API}/auth/change-password/",
                            {"old_password": PASSWORD, "new_password": "  Yangi-Parol-9  "}, format="json")
        self.assertEqual(res.status_code, 200)
        for typed in ("  Yangi-Parol-9  ", "Yangi-Parol-9"):
            with self.subTest(typed=typed):
                res = APIClient().post(f"{API}/auth/login/", {"username": "ali", "password": typed}, format="json")
                self.assertEqual(res.status_code, 200)


class UsernameRulesTests(APITestCase):
    def test_deleted_prefix_is_reserved(self):
        res = self.api.post(f"{API}/auth/register/", {"username": "Deleted_5", "password": PASSWORD}, format="json")
        self.assertEqual(res.status_code, 400)
        user = make_user("ali")
        self.login_as(user)
        res = self.api.patch(f"{API}/auth/profile/", {"username": "deleted_9"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_users_endpoint_keeps_case_insensitive_uniqueness(self):
        make_user("ali")
        vali = make_user("vali")
        boss = make_user("boss", is_staff=True)
        boss.user_permissions.add(*Permission.objects.filter(codename__in=["view_user", "change_user"]))
        self.login_as(boss)
        res = self.api.patch(f"{API}/users/{vali.id}/", {"username": "ALI"}, format="json")
        self.assertEqual(res.status_code, 400)
        vali.refresh_from_db()
        self.assertEqual(vali.username, "vali")


class ThrottleAndLockTests(APITestCase):
    def test_spoofed_forwarded_for_does_not_bypass_throttle(self):
        codes = [
            self.api.post(f"{API}/auth/password-reset/", {"username": "yoq"}, format="json",
                          HTTP_X_FORWARDED_FOR=f"10.0.0.{i}").status_code
            for i in range(25)
        ]
        self.assertIn(429, codes)

    def test_lock_also_protects_admin_login(self):
        make_user("ali")
        for _ in range(5):
            self.api.post(f"{API}/auth/login/", {"username": "ali", "password": "xato"}, format="json")
        # Admin panel ham shu backend orqali kiradi (so'rov bilan) — to'g'ri parol bilan ham bloklangan
        admin_request = RequestFactory().post("/admin/login/")
        self.assertIsNone(authenticate(admin_request, username="ali", password=PASSWORD))

    def test_login_requires_csrf_token(self):
        make_user("ali")
        client = APIClient(enforce_csrf_checks=True)
        res = client.post(f"{API}/auth/login/", {"username": "ali", "password": PASSWORD}, format="json")
        self.assertEqual(res.status_code, 403)
        client.get("/")  # sahifa csrftoken cookie'sini beradi
        token = client.cookies["csrftoken"].value
        res = client.post(f"{API}/auth/login/", {"username": "ali", "password": PASSWORD}, format="json",
                          HTTP_X_CSRFTOKEN=token)
        self.assertEqual(res.status_code, 200)


class PasswordResetLimitTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user("ali", email="ali@example.com")

    def request_code(self):
        return self.api.post(f"{API}/auth/password-reset/", {"username": "ali"}, format="json")

    def test_hourly_email_limit(self):
        for _ in range(7):
            cache.clear()  # IP bo'yicha cheklov emas, akkaunt bo'yicha soatlik chegara tekshiriladi
            self.request_code()
            # 60 soniyalik kutishni chetlab o'tamiz: oldingi kodlarni biroz "eskiroq" qilamiz
            PasswordResetCode.objects.update(created_at=timezone.now() - timedelta(minutes=2))
        self.assertEqual(len(mail.outbox), 5)

    def test_correct_code_does_not_use_up_attempts(self):
        self.request_code()
        code = re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(4):
            self.api.post(f"{API}/auth/password-reset/verify/", {"username": "ali", "code": wrong}, format="json")
        res = self.api.post(f"{API}/auth/password-reset/verify/", {"username": "ali", "code": code}, format="json")
        self.assertEqual(res.status_code, 200)
        res = self.api.post(f"{API}/auth/password-reset/confirm/",
                            {"username": "ali", "code": code, "new_password": "Yangi-parol-777"}, format="json")
        self.assertEqual(res.status_code, 200)


class DeploymentSafetyTests(APITestCase):
    def test_seed_data_does_not_create_admin_with_known_password(self):
        call_command("seed_data", stdout=io.StringIO())
        self.assertFalse(User.objects.filter(is_superuser=True).exists())
        self.assertTrue(ExpenseCategory.objects.filter(user__isnull=True).exists())

    def test_page_has_csp_and_no_inline_scripts(self):
        res = self.client.get("/")
        self.assertIn("script-src 'self'", res.headers["Content-Security-Policy"])
        html = res.content.decode()
        self.assertNotRegex(html, r"\son[a-z]+=\"")
        self.assertNotIn("<script>", html)


class ExtremeInputTests(APITestCase):
    """G'ayrioddiy qiymatlar 500 (server xatosi) emas, tushunarli 4xx javob olishi kerak"""

    def setUp(self):
        super().setUp()
        self.user = make_user("ali")
        self.wallet = make_wallet(self.user, 1_000_000)
        self.cat = ExpenseCategory.objects.create(name="Ovqat")
        self.login_as(self.user)

    def test_extreme_years_in_stats_and_filters(self):
        for query in ("year=1&month=1", "year=1&month=2", "year=0&month=0", "year=-5&month=-3", "year=99999&month=1"):
            with self.subTest(query=query):
                self.assertEqual(self.api.get(f"{API}/stats/monthly/?{query}").status_code, 200)
        for query in ("year=1", "year=1&month=1"):
            with self.subTest(query=query):
                self.assertEqual(self.api.get(f"{API}/expenses/?{query}").status_code, 200)

    def test_operation_date_out_of_range_is_rejected(self):
        for date in ("0001-01-01T00:00:00", "9999-12-31T23:59:59"):
            with self.subTest(date=date):
                res = self.api.post(f"{API}/expenses/", {"wallet": self.wallet.id, "category": self.cat.id,
                                                         "summa": 100, "date": date}, format="json")
                self.assertEqual(res.status_code, 400)
                self.assertIn("1900", res.json()["error"])
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.summa, 1_000_000)

    def test_repay_with_malformed_wallet_id(self):
        debt = self.api.post(f"{API}/debts/", {"person_name": "X", "debt_type": "take", "summa": 1000,
                                               "wallet": self.wallet.id}, format="json").json()
        for wallet in ("abc", [1], {"id": 1}):
            with self.subTest(wallet=wallet):
                res = self.api.post(f"{API}/debts/{debt['id']}/repay/", {"amount": 10, "wallet": wallet}, format="json")
                self.assertEqual(res.status_code, 404)
        self.assertEqual(Debt.objects.get(pk=debt["id"]).paid_summa, 0)


class AccountTakeoverTests(APITestCase):
    """Ochiq qolgan (o'g'irlangan) sessiya bilan hisobni butunlay egallab yoki o'chirib bo'lmasligi kerak"""

    def setUp(self):
        super().setUp()
        self.user = make_user("ali", email="ali@example.com")
        self.login_as(self.user)

    def patch_profile(self, **data):
        return self.api.patch(f"{API}/auth/profile/", data, format="json")

    def test_email_change_requires_current_password(self):
        self.assertEqual(self.patch_profile(email="hacker@example.com").status_code, 400)
        self.assertEqual(self.patch_profile(email="hacker@example.com", password="xato").status_code, 400)
        self.assertEqual(self.patch_profile(email="").status_code, 400)  # emailni o'chirish ham
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "ali@example.com")
        self.assertEqual(self.patch_profile(email="yangi@example.com", password=PASSWORD).status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "yangi@example.com")

    def test_other_profile_fields_do_not_need_password(self):
        res = self.patch_profile(first_name="Ali", email="ALI@example.com", phone="+998901112233")
        self.assertEqual(res.status_code, 200)

    def test_current_password_cannot_be_brute_forced(self):
        for _ in range(5):
            self.api.post(f"{API}/auth/change-password/", {"old_password": "xato", "new_password": "Yangi-Parol-9"},
                          format="json")
        res = self.api.post(f"{API}/auth/change-password/", {"old_password": PASSWORD, "new_password": "Yangi-Parol-9"},
                            format="json")
        self.assertEqual(res.status_code, 429)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_users_endpoint_cannot_edit_or_delete_without_password(self):
        self.assertEqual(self.api.patch(f"{API}/users/{self.user.id}/", {"email": "h@x.com"}, format="json").status_code, 403)
        self.assertEqual(self.api.delete(f"{API}/users/{self.user.id}/").status_code, 403)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertEqual(self.user.email, "ali@example.com")

    def test_password_reset_daily_limit(self):
        anon = APIClient()
        for _ in range(12):
            cache.clear()  # IP bo'yicha cheklov emas, akkaunt bo'yicha kunlik chegara tekshiriladi
            anon.post(f"{API}/auth/password-reset/", {"username": "ali"}, format="json")
            # 60 soniya va 1 soatlik chegaralarni chetlab o'tamiz: kodlarni 2 soat oldin yaratilgan deb belgilaymiz
            PasswordResetCode.objects.update(created_at=timezone.now() - timedelta(hours=2))
        self.assertEqual(len(mail.outbox), 10)


class AdminPanelTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.boss = make_user("boss", is_staff=True)
        # Panelga faqat is_staff yetmaydi — akkauntlarni ko'rish ruxsati ham kerak (tests_security.py ga qarang)
        self.boss.user_permissions.add(Permission.objects.get(codename="view_user"))
        self.ali = make_user("ali", first_name="Ali", email="ali@example.com", phone="+998901112233")
        self.vali = make_user("vali")
        wallet = make_wallet(self.ali, summa=1000)
        Income.objects.create(user=self.ali, wallet=wallet, summa=500)
        Expense.objects.create(user=self.ali, wallet=wallet, summa=200)
        # O'chirilgan operatsiya hisobga kirmaydi
        Expense.objects.create(user=self.ali, wallet=wallet, summa=100).delete()
        User.objects.filter(pk=self.vali.pk).update(is_active=False)  # bloklangan (nofaol) akkaunt
        # Manzil .env dagi PANEL_URL ga bog'liq — qattiq yozilmaydi
        self.panel_url = reverse("panel-accounts")
        self.ali_url = reverse("panel-account", args=[self.ali.pk])

    def test_anonymous_gets_404_like_unknown_url(self):
        # Kirmagan odamga ham 404 (yo'naltirish PANEL_URL borligini oshkor qilardi)
        self.assertEqual(self.client.get(self.panel_url).status_code, 404)

    def test_regular_user_does_not_see_panel(self):
        self.client.force_login(self.ali)
        self.assertEqual(self.client.get(self.panel_url).status_code, 404)
        self.assertEqual(self.client.get(self.ali_url).status_code, 404)

    def test_dashboard_has_no_panel_link(self):
        # Panelga faqat manzilni bilgan xodim kiradi — navbarda havola yo'q
        self.client.force_login(self.boss)
        self.assertNotContains(self.client.get("/"), self.panel_url)

    def test_staff_sees_accounts_with_counts(self):
        self.client.force_login(self.boss)
        res = self.client.get(self.panel_url)
        self.assertEqual(res.status_code, 200)
        self.assertIn("no-store", res.headers["Cache-Control"])
        summary = res.context["summary"]
        self.assertEqual((summary["total"], summary["active"], summary["closed"], summary["operations"]), (3, 2, 1, 2))
        ali = next(u for u in res.context["page"] if u.pk == self.ali.pk)
        self.assertEqual((ali.wallets_count, ali.ops_count), (1, 2))
        self.assertContains(res, "ali@example.com")
        self.assertNotIn("<script>", res.content.decode())

    def test_search_and_status_filter(self):
        self.client.force_login(self.boss)
        found = self.client.get(self.panel_url, {"q": "998901112233"}).context["page"]
        self.assertEqual([u.pk for u in found], [self.ali.pk])
        closed = self.client.get(self.panel_url, {"status": "closed"}).context["page"]
        self.assertEqual([u.pk for u in closed], [self.vali.pk])

    def test_bad_query_params_do_not_break_page(self):
        self.client.force_login(self.boss)
        res = self.client.get(self.panel_url, {"sort": "password", "status": "x", "page": "abc"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual((res.context["sort_key"], res.context["status_key"]), ("new", "all"))

    def test_account_detail(self):
        self.client.force_login(self.boss)
        res = self.client.get(self.ali_url)
        self.assertEqual(res.status_code, 200)
        account = res.context["account"]
        self.assertEqual((account.incomes_count, account.expenses_count, account.wallets_count), (1, 1, 1))
        self.assertEqual(res.context["ops_30d"], 2)
        self.assertEqual(res.context["currencies"], ["UZS"])
        self.assertContains(res, f"/mainapp/user/{self.ali.pk}/change/")
        self.assertEqual(self.client.get(reverse("panel-account", args=[999999])).status_code, 404)

    def test_me_tells_frontend_who_is_staff(self):
        self.login_as(self.boss)
        self.assertTrue(self.api.get(f"{API}/auth/me/").json()["user"]["is_staff"])
        self.login_as(self.ali)
        self.assertFalse(self.api.get(f"{API}/auth/me/").json()["user"]["is_staff"])

class PlansIssueFixTests(APITestCase):
    """plans.md dagi kamchiliklar ro'yxatidan tuzatilgan xatolar qaytib kelmasligi uchun"""

    def setUp(self):
        super().setUp()
        self.user = make_user("ali")
        self.a = make_wallet(self.user, 1_000_000, name="A")
        self.b = make_wallet(self.user, 0, name="B")
        self.exp_cat = ExpenseCategory.objects.create(name="Turkum")
        self.inc_cat = Category.objects.create(name="Manba")
        self.login_as(self.user)

    def post(self, path, payload):
        return self.api.post(f"{API}/{path}/", payload, format="json")

    def test_incomes_and_transfers_filter_by_month(self):
        for date in (datetime(2026, 9, 15, 12), datetime(2026, 10, 5, 12)):
            date = timezone.make_aware(date).isoformat()
            inc = self.post("incomes", {"wallet": self.a.id, "category": self.inc_cat.id, "summa": 100, "date": date})
            self.assertEqual(inc.status_code, 201, inc.content)
            tr = self.post("transfers", {"from_wallet": self.a.id, "to_wallet": self.b.id, "summa": 10, "date": date})
            self.assertEqual(tr.status_code, 201, tr.content)
        for path in ("incomes", "transfers", "expenses"):
            with self.subTest(path=path):
                res = self.api.get(f"{API}/{path}/", {"year": 2026, "month": 9})
                self.assertTrue(all(r["date"].startswith("2026-09") for r in rows(res)))
        self.assertEqual(len(rows(self.api.get(f"{API}/incomes/", {"year": 2026, "month": 9}))), 1)
        self.assertEqual(len(rows(self.api.get(f"{API}/transfers/", {"year": 2026, "month": 10}))), 1)

    def test_wallet_with_money_or_open_debt_cannot_be_deleted(self):
        res = self.api.delete(f"{API}/wallets/{self.a.id}/")
        self.assertEqual(res.status_code, 400)
        self.assertIn("O'tkazma", res.json()["error"])
        self.a.refresh_from_db()
        self.assertTrue(self.a.status)

        lent = make_wallet(self.user, 500, name="C")
        self.assertEqual(self.post("debts", {"person_name": "X", "debt_type": "give", "summa": 500,
                                             "wallet": lent.id}).status_code, 201)
        res = self.api.delete(f"{API}/wallets/{lent.id}/")
        self.assertEqual(res.status_code, 400)
        self.assertIn("qarz", res.json()["error"])

        self.assertEqual(self.api.delete(f"{API}/wallets/{self.b.id}/").status_code, 200)

    def test_status_cannot_be_changed_through_api(self):
        self.api.patch(f"{API}/wallets/{self.a.id}/", {"status": False}, format="json")
        self.a.refresh_from_db()
        self.assertTrue(self.a.status)
        res = self.post("incomes", {"wallet": self.a.id, "category": self.inc_cat.id, "summa": 100, "status": False})
        self.assertEqual(res.status_code, 201, res.content)
        self.assertTrue(Income.objects.get(pk=res.json()["id"]).status)
        self.a.refresh_from_db()
        self.assertEqual(self.a.summa, 1_000_100)

    def test_settled_debt_reopens_when_amount_grows(self):
        debt = self.post("debts", {"person_name": "X", "debt_type": "take", "summa": 1000, "wallet": self.a.id}).json()
        self.assertEqual(self.post(f"debts/{debt['id']}/repay", {"amount": 1000, "wallet": self.a.id}).status_code, 200)
        self.assertTrue(Debt.objects.get(pk=debt["id"]).is_settled)
        res = self.api.patch(f"{API}/debts/{debt['id']}/", {"summa": 1500}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        obj = Debt.objects.get(pk=debt["id"])
        self.assertFalse(obj.is_settled)
        self.assertEqual(obj.remaining_summa, 500)

    def test_deleted_member_and_category_cannot_be_used(self):
        member = Member.objects.create(user=self.user, name="Ukam")
        member.delete()
        res = self.post("expenses", {"wallet": self.a.id, "category": self.exp_cat.id, "summa": 100, "member": member.id})
        self.assertEqual(res.status_code, 400)
        old_cat = ExpenseCategory.objects.create(name="Eski", user=self.user, status=False)
        res = self.post("expenses", {"wallet": self.a.id, "category": old_cat.id, "summa": 100})
        self.assertEqual(res.status_code, 400)
        self.assertFalse(Expense.objects.exists())

    def test_login_ignores_username_case(self):
        res = APIClient().post(f"{API}/auth/login/", {"username": "ALI", "password": PASSWORD}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["user"]["username"], "ali")

    @override_settings(CURRENCY_BACKGROUND_REFRESH=True)
    @mock.patch("mainapp.currency._fetch_cbu", return_value=FAKE_RATES)
    def test_stale_rate_is_refreshed_in_background(self, _fetch):
        ExchangeRate.objects.create(currency="USD", rate=Decimal("11000"))
        ExchangeRate.objects.filter(currency="USD").update(updated_at=timezone.now() - timedelta(days=2))
        # Fon oqimi bu testda ishga tushmaydi — uning qulfi keyingi testlarga qolib ketmasin
        self.addCleanup(lambda: currency._refresh_lock.locked() and currency._refresh_lock.release())
        with mock.patch("mainapp.currency.threading.Thread") as thread:
            self.assertEqual(currency.get_rate_to_uzs("USD"), Decimal("11000"))
        thread.return_value.start.assert_called_once()
        _fetch.assert_not_called()  # so'rov Markaziy bank javobini kutmadi

    def test_records_of_deleted_wallet_cannot_be_undone(self):
        exp = self.post("expenses", {"wallet": self.a.id, "category": self.exp_cat.id, "summa": 100}).json()
        tr = self.post("transfers", {"from_wallet": self.a.id, "to_wallet": self.b.id, "summa": 50}).json()
        Wallet.objects.filter(pk=self.b.id).update(status=False)
        res = self.api.delete(f"{API}/transfers/{tr['id']}/")
        self.assertEqual(res.status_code, 400)
        self.assertIn("o'chirilgan hamyon", res.json()["error"])
        Wallet.objects.filter(pk=self.a.id).update(status=False)
        self.assertEqual(self.api.delete(f"{API}/expenses/{exp['id']}/").status_code, 400)
        self.assertTrue(Expense.objects.get(pk=exp["id"]).status)
        self.a.refresh_from_db()
        self.assertEqual(self.a.summa, 1_000_000 - 100 - 50)

    def test_register_accepts_optional_email(self):
        res = APIClient().post(f"{API}/auth/register/", {"username": "vali", "password": PASSWORD,
                                                          "email": "vali@example.com"}, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(User.objects.get(username="vali").email, "vali@example.com")
        bad = APIClient().post(f"{API}/auth/register/", {"username": "soli", "password": PASSWORD,
                                                          "email": "email-emas"}, format="json")
        self.assertEqual(bad.status_code, 400)
        taken = APIClient().post(f"{API}/auth/register/", {"username": "goli", "password": PASSWORD,
                                                            "email": "VALI@example.com"}, format="json")
        self.assertEqual(taken.status_code, 400)
        self.assertFalse(User.objects.filter(username__in=["soli", "goli"]).exists())


# ==========================================
# plans.md: kirish himoyasi va akkaunt egallash xatolari (№2, 3, 5, 6, 14, 19)
# ==========================================

def post_login(api, password, username="ali", ip="10.0.0.1"):
    return api.post(f"{API}/auth/login/", {"username": username, "password": password}, format="json",
                    REMOTE_ADDR=ip)


class StaffCannotTouchSuperuserTests(APITestCase):
    """№2: superuser bo'lmagan xodim /users/ orqali superuser hisobini o'zgartira/o'chira olmasligi kerak"""

    def setUp(self):
        super().setUp()
        self.root = make_user("root", is_staff=True, is_superuser=True, email="root@example.com")
        self.staff = make_user("boss", is_staff=True)
        # Panelga o'xshash huquqlar: ko'rish va o'zgartirish (o'chirish emas)
        self.staff.user_permissions.add(*Permission.objects.filter(codename__in=["view_user", "change_user"]))
        self.ali = make_user("ali")

    def test_staff_cannot_hijack_superuser_email(self):
        self.login_as(self.staff)
        res = self.api.patch(f"{API}/users/{self.root.id}/", {"email": "hacker@example.com"}, format="json")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(self.api.put(f"{API}/users/{self.root.id}/", {"username": "root", "email": "h@example.com"},
                                      format="json").status_code, 404)
        self.root.refresh_from_db()
        self.assertEqual(self.root.email, "root@example.com")

    def test_staff_cannot_delete_or_see_superuser(self):
        self.login_as(self.staff)
        self.assertEqual(self.api.delete(f"{API}/users/{self.root.id}/").status_code, 404)
        self.assertEqual(self.api.get(f"{API}/users/{self.root.id}/").status_code, 404)
        ids = [u["id"] for u in rows(self.api.get(f"{API}/users/"))]
        self.assertNotIn(self.root.id, ids)
        self.assertIn(self.ali.id, ids)
        self.root.refresh_from_db()
        self.assertTrue(self.root.is_active)

    def test_staff_still_manages_ordinary_users(self):
        self.login_as(self.staff)
        res = self.api.patch(f"{API}/users/{self.ali.id}/", {"first_name": "Ali"}, format="json")
        self.assertEqual(res.status_code, 200)

    def test_superuser_can_manage_everyone(self):
        self.login_as(self.root)
        ids = [u["id"] for u in rows(self.api.get(f"{API}/users/"))]
        self.assertEqual({self.root.id, self.staff.id, self.ali.id} <= set(ids), True)
        for user in (self.staff, self.ali, self.root):
            res = self.api.patch(f"{API}/users/{user.id}/", {"first_name": "Yangi"}, format="json")
            self.assertEqual(res.status_code, 200, user.username)
        self.assertEqual(self.api.delete(f"{API}/users/{self.staff.id}/").status_code, 200)


class UnicodeUsernameTests(APITestCase):
    """№3: "ＡＤＭＩＮ" kabi keng harfli nom "admin" bilan yonma-yon "ADMIN" bo'lib saqlanmasligi kerak"""

    FULLWIDTH_ADMIN = "ＡＤＭＩＮ"  # ＡＤＭＩＮ (NFKC -> "ADMIN")

    def register(self, username):
        return APIClient().post(f"{API}/auth/register/", {"username": username, "password": PASSWORD}, format="json")

    def test_register_rejects_fullwidth_copy_of_taken_name(self):
        make_user("admin")
        self.assertEqual(self.register(self.FULLWIDTH_ADMIN).status_code, 400)
        self.assertEqual(User.objects.filter(username__iexact="admin").count(), 1)

    def test_username_is_stored_normalized(self):
        res = self.register("ＢＯＢ")  # ＢＯＢ
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()["user"]["username"], "BOB")
        self.assertTrue(User.objects.filter(username="BOB").exists())

    def test_profile_rename_is_checked_after_normalization(self):
        make_user("admin")
        ali = make_user("ali")
        self.login_as(ali)
        res = self.api.patch(f"{API}/auth/profile/", {"username": self.FULLWIDTH_ADMIN}, format="json")
        self.assertEqual(res.status_code, 400)
        ali.refresh_from_db()
        self.assertEqual(ali.username, "ali")
        res = self.api.patch(f"{API}/auth/profile/", {"username": "ＶＡＬＩ"}, format="json")  # ＶＡＬＩ
        self.assertEqual(res.status_code, 200)
        ali.refresh_from_db()
        self.assertEqual(ali.username, "VALI")

    def test_users_endpoint_is_checked_after_normalization(self):
        make_user("admin")
        vali = make_user("vali")
        self.login_as(make_user("root", is_staff=True, is_superuser=True))
        res = self.api.patch(f"{API}/users/{vali.id}/", {"username": self.FULLWIDTH_ADMIN}, format="json")
        self.assertEqual(res.status_code, 400)
        res = self.api.patch(f"{API}/users/{vali.id}/", {"username": "ＫＡＬＩ"}, format="json")  # ＫＡＬＩ
        self.assertEqual(res.status_code, 200)
        vali.refresh_from_db()
        self.assertEqual(vali.username, "KALI")

    def test_model_save_normalizes_username(self):
        user = make_user("tmp")
        user.username = "ＴＭＰ２"  # ＴＭＰ２
        user.save()
        user.refresh_from_db()
        self.assertEqual(user.username, "TMP2")

    def test_database_rejects_case_variant_duplicate(self):
        make_user("ali")
        for name in ("ALI", "Ali"):
            with self.subTest(name=name), self.assertRaises(IntegrityError), transaction.atomic():
                User.objects.create_user(username=name, password=PASSWORD)

    def test_lock_counter_is_shared_with_fullwidth_spelling(self):
        make_user("admin")
        for _ in range(4):
            post_login(self.api, "xato", username="admin")
        self.assertEqual(post_login(self.api, "xato", username=self.FULLWIDTH_ADMIN).status_code, 429)
        self.assertEqual(post_login(self.api, PASSWORD, username="admin").status_code, 429)

    def test_fullwidth_spelling_logs_into_same_account(self):
        make_user("ali")
        self.assertEqual(post_login(self.api, PASSWORD, username="ＡＬＩ").status_code, 200)  # ＡＬＩ

    def test_legacy_unnormalized_name_can_still_log_in(self):
        user = make_user("legacy")
        # eski bazadagi normallashmagan nom (0018-migratsiya unga NFKC + casefold kalitini yozgan bo'lardi)
        User.objects.filter(pk=user.pk).update(username="ＬＥＧ", username_key="leg")
        self.assertEqual(post_login(self.api, PASSWORD, username="ＬＥＧ").status_code, 200)


class AtSignLoginTests(APITestCase):
    """№6: "@" bor identifikator elektron pochta deb qidiriladi — begona odam qurbonning login nomini o'z elektron pochtasi qila olmasligi kerak"""

    def setUp(self):
        super().setUp()
        # "@" li nom eski bazada bo'lishi mumkin (hozir yangi nomda taqiqlangan)
        self.victim = User.objects.create_user(username="vera@gmail.com", password=PASSWORD)
        self.attacker = make_user("hacker", email="h@example.com")

    def test_new_username_cannot_contain_at_sign(self):
        res = APIClient().post(f"{API}/auth/register/", {"username": "yangi@nom", "password": PASSWORD}, format="json")
        self.assertEqual(res.status_code, 400)
        self.login_as(self.attacker)
        res = self.api.patch(f"{API}/auth/profile/", {"username": "boshqa@nom"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.attacker.refresh_from_db()
        self.assertEqual(self.attacker.username, "hacker")

    def test_email_cannot_equal_someone_elses_login(self):
        self.login_as(self.attacker)
        res = self.api.patch(f"{API}/auth/profile/", {"email": "Vera@Gmail.com", "password": PASSWORD}, format="json")
        self.assertEqual(res.status_code, 400)
        self.attacker.refresh_from_db()
        self.assertEqual(self.attacker.email, "h@example.com")
        res = APIClient().post(f"{API}/auth/register/", {"username": "soli", "password": PASSWORD,
                                                          "email": "vera@gmail.com"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.login_as(make_user("root", is_staff=True, is_superuser=True))
        res = self.api.patch(f"{API}/users/{self.attacker.id}/", {"email": "vera@gmail.com"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_victim_with_legacy_at_login_still_logs_in(self):
        self.assertEqual(post_login(self.api, PASSWORD, username="vera@gmail.com").status_code, 200)

    def test_legacy_at_login_keeps_working_when_profile_is_saved(self):
        self.login_as(self.victim)
        res = self.api.patch(f"{API}/auth/profile/", {"username": "vera@gmail.com", "first_name": "Vera"},
                             format="json")
        self.assertEqual(res.status_code, 200, res.content)


class LoginCacheEvictionTests(APITestCase):
    """№5: kesh to'lib ketganda login hisoblagichlari o'chib ketmasligi kerak"""

    def test_login_counter_survives_many_cache_entries(self):
        make_user("ali")
        for _ in range(3):
            post_login(self.api, "xato")
        # Eski MAX_ENTRIES=300 bilan shu yerda alifbo bo'yicha birinchi kalitlar ("login_fail:*") o'chib ketardi
        for i in range(400):
            cache.set(f"zz_fill_{i}", i, 600)
        res = post_login(self.api, "xato")
        self.assertEqual(res.status_code, 401)
        self.assertIn("1 ta urinish", res.json()["error"])
        self.assertEqual(post_login(self.api, "xato").status_code, 429)


class LoginLockPerIpTests(APITestCase):
    """№14: blok (hisob + IP) juftligi bo'yicha; taqsimlangan urinishlarga qarshi hisob bo'yicha umumiy chegara"""

    def setUp(self):
        super().setUp()
        self.user = make_user("ali", email="ali@example.com")

    def fail(self, ip, times):
        return [post_login(self.api, "xato", ip=ip).status_code for _ in range(times)]

    def test_stranger_cannot_lock_the_owner_out(self):
        self.assertEqual(self.fail("203.0.113.9", 5), [401, 401, 401, 401, 429])
        self.assertEqual(post_login(self.api, "xato", ip="203.0.113.9").status_code, 429)
        self.assertEqual(post_login(self.api, PASSWORD, ip="203.0.113.9").status_code, 429)
        # Egasi o'z IP'sidan odatdagidek kiradi
        self.assertEqual(post_login(self.api, PASSWORD, ip="198.51.100.7").status_code, 200)

    def test_distributed_guessing_below_account_limit_does_not_lock(self):
        for n in range(5):
            self.fail(f"10.1.0.{n}", 5)
        self.assertEqual(post_login(self.api, PASSWORD, ip="10.1.9.9").status_code, 200)

    def test_distributed_guessing_locks_the_account(self):
        for n in range(6):  # 6 IP x 5 urinish = 30 — umumiy chegara
            self.fail(f"10.1.0.{n}", 5)
        res = post_login(self.api, PASSWORD, ip="10.1.9.9")
        self.assertEqual(res.status_code, 429)

    def test_single_ip_cannot_push_account_counter_past_its_own_limit(self):
        self.fail("203.0.113.9", 40)
        account_key = _login_keys("ali", None)[1]
        self.assertEqual(cache.get(account_key), LOGIN_MAX_FAILS)
        self.assertEqual(post_login(self.api, PASSWORD, ip="198.51.100.7").status_code, 200)

    def test_success_clears_only_its_own_pair(self):
        self.fail("10.2.0.1", 4)
        self.fail("10.2.0.2", 3)
        self.assertEqual(post_login(self.api, PASSWORD, ip="10.2.0.1").status_code, 200)
        # 10.2.0.1 hisoblagichi nollandi: yana 4 ta xato mumkin, 5-sida bloklanadi
        self.assertEqual(self.fail("10.2.0.1", 5), [401, 401, 401, 401, 429])
        # 10.2.0.2 ga muvaffaqiyatli kirish ta'sir qilmadi: bor-yo'g'i 2 ta urinish qolgan edi
        self.assertEqual(self.fail("10.2.0.2", 2), [401, 429])
        # Umumiy hisoblagich ham nollanmagan (kirishning o'zi ham sanaladi)
        self.assertGreaterEqual(cache.get(_login_keys("ali", None)[1]), 4 + 3 + 1)

    def test_authenticate_without_request_is_safe(self):
        self.assertIsNone(authenticate(None, username="ali", password="xato"))
        self.assertEqual(authenticate(None, username="ali", password=PASSWORD), self.user)
        for _ in range(5):
            authenticate(None, username="ali", password="xato")
        self.assertIsNone(authenticate(None, username="ali", password=PASSWORD))
        self.assertTrue(is_login_locked("ali"))

    def test_client_ip_follows_num_proxies_setting(self):
        request = RequestFactory().post("/", REMOTE_ADDR="9.9.9.9", HTTP_X_FORWARDED_FOR="6.6.6.6, 7.7.7.7")
        for proxies, expected in ((0, "9.9.9.9"), (1, "7.7.7.7")):
            with self.subTest(proxies=proxies), override_settings(
                    REST_FRAMEWORK={**settings.REST_FRAMEWORK, "NUM_PROXIES": proxies}):
                self.assertEqual(client_ip(request), expected)
        self.assertEqual(client_ip(None), "")

    def test_password_reset_clears_the_lock(self):
        self.fail("203.0.113.9", 5)
        anon = APIClient()
        post = lambda path, data: anon.post(f"{API}/auth/{path}", data, format="json", REMOTE_ADDR="203.0.113.9")
        post("password-reset/", {"username": "ali"})
        code = re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)
        res = post("password-reset/confirm/", {"username": "ali", "code": code, "new_password": "Yangi-parol-777"})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(post_login(self.api, "Yangi-parol-777", ip="203.0.113.9").status_code, 200)


class PasswordResetIpLimitTests(APITestCase):
    """№14: bitta IP birovning kunlik tiklash kodi limitini tugata olmasligi kerak"""

    def request_code(self, username="ali", ip="203.0.113.9"):
        return APIClient().post(f"{API}/auth/password-reset/", {"username": username}, format="json", REMOTE_ADDR=ip)

    def age_codes(self):
        # 60 soniyalik kutishni chetlab o'tamiz: oldingi kodlarni biroz "eskiroq" qilamiz
        PasswordResetCode.objects.update(created_at=timezone.now() - timedelta(minutes=2))

    def test_one_ip_cannot_use_up_the_accounts_daily_budget(self):
        make_user("ali", email="ali@example.com")
        responses = []
        for _ in range(6):
            responses.append(self.request_code().json())
            self.age_codes()
        self.assertEqual(len(mail.outbox), 3)  # bitta IP dan sutkada 3 tadan ko'p kod yuborilmaydi
        self.assertEqual(len({r["message"] for r in responses}), 1)  # javob doim bir xil — akkaunt borligi bilinmaydi
        # Egasi boshqa IP'dan hali kod ola oladi
        self.assertEqual(self.request_code(ip="198.51.100.7").status_code, 200)
        self.assertEqual(len(mail.outbox), 4)

    def test_one_ip_cannot_bury_many_accounts_in_mail(self):
        for n in range(12):
            make_user(f"user{n}", email=f"user{n}@example.com")
        for n in range(12):
            self.request_code(username=f"user{n}")
        self.assertEqual(len(mail.outbox), 10)

    def test_failed_mail_does_not_use_up_the_ip_limit(self):
        make_user("ali", email="ali@example.com")
        # Xat fonda yuboriladi: pochta xatosi javobga ta'sir qilmaydi (akkaunt borligi bilinmasligi uchun), faqat logga yoziladi
        with mock.patch("mainapp.views.send_mail", side_effect=OSError("smtp")), \
                self.assertLogs("mainapp.views", level="ERROR"):
            self.assertEqual([self.request_code().status_code for _ in range(4)], [200, 200, 200, 200])
        self.assertEqual(self.request_code().status_code, 200)
        self.assertEqual(len(mail.outbox), 1)


@unittest.skipUnless(isinstance(caches["default"], BaseDatabaseCache), "faqat baza keshi uchun")
class CounterAtomicityTests(APITestCase):
    """№19: baza keshida incr() o'qi-yoz ketma-ketligi — hisoblagich tranzaksiya ichida yangilanishi kerak"""

    def test_incr_runs_inside_its_own_transaction(self):
        backend = caches["default"]
        real_incr = backend.incr
        depth = {}

        def spy(*args, **kwargs):
            depth["inside"] = len(connection.savepoint_ids)
            return real_incr(*args, **kwargs)

        _bump_counter("counter:test")
        before = len(connection.savepoint_ids)
        with mock.patch.object(backend, "incr", side_effect=spy):
            _bump_counter("counter:test")
        self.assertGreater(depth["inside"], before)  # atomic() blok (yozish qulfi) incr() dan oldin ochilgan

    def test_counter_counts_and_keeps_its_window(self):
        self.assertEqual([_bump_counter("counter:test", 900) for _ in range(5)], [1, 2, 3, 4, 5])
        self.assertEqual(cache.get("counter:test"), 5)
        refund_limit("counter:test", 900)
        self.assertEqual(cache.get("counter:test"), 4)
        refund_limit("counter:yoq", 900)  # mavjud bo'lmagan kalit xato bermaydi
        self.assertIsNone(cache.get("counter:yoq"))
