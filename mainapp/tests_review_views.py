"""Views / parser / settings bo'yicha chuqur tekshiruvda topilgan 500 xatolar va poyga (race) uchun regressiya testlari."""
import json
from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Category, Debt, Income, Wallet
from .tests import API, PASSWORD, make_user, make_wallet
from .views import WalletViewSet

# JSON'dagi yolg'iz surrogat escape'i: chr(92) + "ud800" (faylga to'g'ridan-to'g'ri yozilmaydi — tahrirlovchilar buzadi)
LONE_SURROGATE = chr(92) + "ud800"
JSON = "application/json"


class ParserRobustnessTests(TestCase):
    """JSON tanasi qanday bo'lmasin 500 emas, 400 qaytishi kerak"""

    def setUp(self):
        cache.clear()
        self.api = APIClient()
        self.user = make_user("ali", email="ali@example.com")

    def post_raw(self, path, raw):
        return self.api.post(f"{API}{path}", raw, content_type=JSON)

    def test_lone_surrogate_in_anonymous_auth_endpoints_is_400(self):
        # UTF-8 ga o'girilmaydigan belgi bazaga tushganda UnicodeEncodeError berardi (login, tiklash, ro'yxatdan o'tish)
        cases = {
            "/auth/login/": '{"username": "%s", "password": "x"}' % LONE_SURROGATE,
            "/auth/login/verify/": '{"token": "%s", "code": "123456"}' % LONE_SURROGATE,
            "/auth/register/": '{"username": "yangi", "password": "Parol-12345", "first_name": "%s"}' % LONE_SURROGATE,
            "/auth/password-reset/": '{"username": "%s"}' % LONE_SURROGATE,
            "/auth/password-reset/verify/": '{"username": "ali", "code": "%s"}' % LONE_SURROGATE,
        }
        for path, raw in cases.items():
            with self.subTest(path=path):
                self.assertEqual(self.post_raw(path, raw).status_code, 400)

    def test_lone_surrogate_in_authenticated_endpoints_is_400(self):
        self.api.force_login(self.user)
        res = self.api.patch(f"{API}/auth/profile/", '{"first_name": "%s"}' % LONE_SURROGATE, content_type=JSON)
        self.assertEqual(res.status_code, 400)
        res = self.post_raw("/wallets/", '{"name": "%s", "currency": "UZS"}' % LONE_SURROGATE)
        self.assertEqual(res.status_code, 400)

    def test_lone_surrogate_in_key_is_400(self):
        self.assertEqual(self.post_raw("/auth/login/", '{"%s": 1}' % LONE_SURROGATE).status_code, 400)

    def test_normal_unicode_still_accepted(self):
        res = self.post_raw("/auth/register/", json.dumps(
            {"username": "yangi", "password": PASSWORD, "first_name": "Ўктам 😀"}))
        self.assertEqual(res.status_code, 201)

    def test_deeply_nested_json_is_400(self):
        # json.loads RecursionError beradi — DRF uni ushlamasdi (500)
        for raw in ('{"a":' * 50000 + "1" + "}" * 50000, "[" * 50000 + "]" * 50000):
            with self.subTest(start=raw[:6]):
                self.assertEqual(self.post_raw("/auth/login/", raw).status_code, 400)


class HugeAmountTests(TestCase):
    """28 xonadan uzun raqam Decimal.quantize() da InvalidOperation berardi (500)"""

    HUGE = ["1e999999", "1" * 40, 10 ** 30, 1e308]

    def setUp(self):
        cache.clear()
        self.api = APIClient()
        self.user = make_user("ali")
        self.wallet = make_wallet(self.user, 1000)
        self.wallet2 = make_wallet(self.user, 1000, name="Karta")
        self.category = Category.objects.create(name="Oylik")
        self.api.force_login(self.user)

    def test_create_with_huge_amount_is_400(self):
        for value in self.HUGE:
            bodies = {
                "/incomes/": {"wallet": self.wallet.pk, "category": self.category.pk, "summa": value},
                "/wallets/": {"name": "Yangi", "currency": "UZS", "summa": value},
                "/transfers/": {"from_wallet": self.wallet.pk, "to_wallet": self.wallet2.pk, "summa": value},
                "/debts/": {"person_name": "Vali", "debt_type": "give", "wallet": self.wallet.pk, "summa": value},
            }
            for path, body in bodies.items():
                with self.subTest(path=path, value=str(value)[:12]):
                    res = self.api.post(f"{API}{path}", json.dumps(body), content_type=JSON)
                    self.assertEqual(res.status_code, 400, res.content)

    def test_update_with_huge_amount_is_400_and_balance_untouched(self):
        income = Income.objects.create(user=self.user, wallet=self.wallet, category=self.category, summa=5)
        self.wallet.refresh_from_db()
        balance = self.wallet.summa
        for value in self.HUGE:
            with self.subTest(value=str(value)[:12]):
                res = self.api.patch(f"{API}/incomes/{income.pk}/", json.dumps({"summa": value}), content_type=JSON)
                self.assertEqual(res.status_code, 400, res.content)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.summa, balance)

    def test_normal_amount_still_works(self):
        res = self.api.post(f"{API}/incomes/", json.dumps(
            {"wallet": self.wallet.pk, "category": self.category.pk, "summa": "12.50"}), content_type=JSON)
        self.assertEqual(res.status_code, 201)

    def test_repay_with_huge_amount_is_400(self):
        debt = Debt.objects.create(user=self.user, wallet=self.wallet, person_name="Vali", debt_type="give", summa=100)
        for value in self.HUGE:
            res = self.api.post(f"{API}/debts/{debt.pk}/repay/",
                                json.dumps({"amount": value, "wallet": self.wallet.pk}), content_type=JSON)
            self.assertEqual(res.status_code, 400, res.content)


class WalletDestroyAtomicTests(TestCase):
    """Hamyonni o'chirish tekshiruvlari va o'chirishning o'zi bitta tranzaksiyada bo'lishi kerak: aks holda tekshiruvdan
    keyin tushgan kirim pulni o'chirilgan hamyonda qoldirardi, ikki parallel so'rov esa 'oxirgi hamyon' qoidasini aylanib o'tardi"""

    def setUp(self):
        cache.clear()
        self.api = APIClient()
        self.user = make_user("ali")
        self.first = make_wallet(self.user, 0, name="Birinchi")
        self.second = make_wallet(self.user, 0, name="Ikkinchi")
        self.api.force_login(self.user)

    def test_delete_runs_inside_a_transaction(self):
        from django.db import connection
        baseline = len(connection.savepoint_ids)
        seen = []
        original = WalletViewSet.perform_destroy

        def spy(view, instance):
            seen.append(len(connection.savepoint_ids))
            return original(view, instance)

        with mock.patch.object(WalletViewSet, "perform_destroy", spy):
            res = self.api.delete(f"{API}/wallets/{self.second.pk}/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(seen, [baseline + 1])
        self.second.refresh_from_db()
        self.assertFalse(self.second.status)

    def test_rules_still_enforced(self):
        # Puli bor hamyon o'chmaydi
        Wallet.objects.filter(pk=self.second.pk).update(summa=5)
        res = self.api.delete(f"{API}/wallets/{self.second.pk}/")
        self.assertEqual(res.status_code, 400)
        Wallet.objects.filter(pk=self.second.pk).update(summa=0)
        # Birinchisi o'chadi, oxirgisi o'chmaydi
        self.assertEqual(self.api.delete(f"{API}/wallets/{self.first.pk}/").status_code, 200)
        res = self.api.delete(f"{API}/wallets/{self.second.pk}/")
        self.assertEqual(res.status_code, 400)
        self.second.refresh_from_db()
        self.assertTrue(self.second.status)

    def test_foreign_or_missing_wallet_is_404(self):
        other = make_wallet(make_user("vali"), 0)
        self.assertEqual(self.api.delete(f"{API}/wallets/{other.pk}/").status_code, 404)
        self.assertEqual(self.api.delete(f"{API}/wallets/999999/").status_code, 404)
        self.assertEqual(self.api.delete(f"{API}/wallets/abc/").status_code, 404)
