from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Category, Debt, Expense, ExpenseCategory, User, Wallet

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

    def test_allows_common_but_varied_passwords(self):
        self.check("password")

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
        self.assertEqual(res.status_code, 403)

    def test_user_creates_private_category(self):
        self.login_as(self.ali)
        res = self.api.post(f"{API}/expense-categories/", {"name": "Mening toifam"}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(ExpenseCategory.objects.get(name="Mening toifam").user, self.ali)
        self.login_as(self.vali)
        names = [c["name"] for c in rows(self.api.get(f"{API}/expense-categories/"))]
        self.assertNotIn("Mening toifam", names)
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
        self.assertEqual(self.api.delete(f"{API}/expense-categories/{cat.id}/").status_code, 204)

    def test_regular_user_cannot_modify_global_category(self):
        self.login_as(self.ali)
        res = self.api.patch(f"{API}/expense-categories/{self.global_cat.id}/", {"name": "Buzildi"}, format="json")
        self.assertEqual(res.status_code, 403)
        self.assertEqual(self.api.delete(f"{API}/expense-categories/{self.global_cat.id}/").status_code, 403)
        self.assertTrue(ExpenseCategory.objects.filter(pk=self.global_cat.pk, name="Oziq-ovqat").exists())

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
        self.exp_cat = ExpenseCategory.objects.create(name="Toifa")
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
        self.exp_cat = ExpenseCategory.objects.create(name="Toifa")
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
        self.login_as(self.user)

    def create_debt(self, summa):
        res = self.api.post(f"{API}/debts/", {"person_name": "Rustam", "debt_type": "take", "summa": summa}, format="json")
        return res.json()

    def test_partial_then_full_repayment_settles_debt(self):
        debt = self.create_debt(500000)
        self.assertEqual(self.api.post(f"{API}/debts/{debt['id']}/repay/", {"amount": 200000}, format="json").status_code, 200)
        self.assertFalse(Debt.objects.get(pk=debt["id"]).is_settled)
        self.assertEqual(self.api.post(f"{API}/debts/{debt['id']}/repay/", {"amount": 300000}, format="json").status_code, 200)
        self.assertTrue(Debt.objects.get(pk=debt["id"]).is_settled)

    def test_overpayment_is_rejected(self):
        debt = self.create_debt(1000)
        res = self.api.post(f"{API}/debts/{debt['id']}/repay/", {"amount": 1001}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Debt.objects.get(pk=debt["id"]).paid_summa, 0)

    def test_debt_requires_positive_amount(self):
        res = self.api.post(f"{API}/debts/", {"person_name": "X", "debt_type": "take", "summa": 0}, format="json")
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

    def test_deleted_account_cannot_log_in_and_personal_data_is_wiped(self):
        self.assertEqual(self.delete_account(PASSWORD).status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertFalse(self.user.status)
        self.assertEqual((self.user.first_name, self.user.last_name, self.user.email), ("", "", ""))
        self.assertIsNone(self.user.phone)
        self.assertNotEqual(self.user.username, "ali")
        self.assertFalse(self.user.has_usable_password())

        res = APIClient().post(f"{API}/auth/login/", {"username": "ali", "password": PASSWORD}, format="json")
        self.assertEqual(res.status_code, 401)

    def test_username_is_freed_for_reuse(self):
        self.delete_account(PASSWORD)
        res = APIClient().post(f"{API}/auth/register/", {"username": "ali", "password": PASSWORD}, format="json")
        self.assertEqual(res.status_code, 201)

    def test_financial_history_is_kept(self):
        self.delete_account(PASSWORD)
        self.assertTrue(Expense.objects.filter(pk=self.expense.pk).exists())
        self.assertTrue(Wallet.objects.filter(pk=self.wallet.pk).exists())


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

    def test_balance_cannot_be_edited_directly(self):
        self.assertEqual(self.patch({"summa": 1}).status_code, 400)
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
        self.exp_cat = ExpenseCategory.objects.create(name="Toifa")
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
        self.post("debts", {"person_name": "Y", "debt_type": "take", "summa": 8000})

        self.assertEqual(self.ids(f"incomes/?wallet={self.a.id}"), [inc_a["id"]])
        self.assertEqual(self.ids(f"incomes/?wallet={self.b.id}"), [inc_b["id"]])
        self.assertEqual(self.ids(f"expenses/?wallet={self.a.id}"), [exp_a["id"]])
        self.assertEqual(self.ids(f"expenses/?wallet={self.b.id}"), [exp_b["id"]])
        self.assertEqual(self.ids(f"transfers/?from_wallet={self.a.id}"), [out_a["id"]])
        self.assertEqual(self.ids(f"transfers/?to_wallet={self.a.id}"), [in_a["id"]])
        self.assertEqual(self.ids(f"debts/?wallet={self.a.id}"), [debt_a["id"]])

    def test_large_limit_returns_every_record(self):
        for _ in range(12):
            self.post("incomes", {"wallet": self.a.id, "category": self.inc_cat.id, "summa": 100})
        self.assertEqual(len(self.ids(f"incomes/?wallet={self.a.id}&limit=200&offset=0")), 12)
        self.assertEqual(len(self.ids(f"incomes/?wallet={self.a.id}")), 10)  # standart sahifa hajmi
