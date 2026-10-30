"""plans.md №8, 9, 10, 15, 16, 17 testlari: yozuvni tahrirlash hamyon qoldig'ini buzmasligi kerak.
Tarmoq har doim mock: haqiqiy cbu.uz ga murojaat qilinmaydi."""
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from .models import (
    MAX_AMOUNT, Category, Debt, Expense, ExpenseCategory, Income, Member, Transfer, User, Wallet, apply_wallet_changes,
)
from .serializers import MIN_RATE, MIN_RATE_MESSAGE, ExpenseSerializer, IncomeSerializer, TransferSerializer
from .views import strict_int

API = "/api/v1"


class BalanceTestCase(TestCase):
    def setUp(self):
        cache.clear()
        offline = mock.patch("mainapp.currency._fetch_cbu", side_effect=OSError("testlarda internet ishlatilmaydi"))
        offline.start()
        self.addCleanup(offline.stop)
        self.user = User.objects.create_user(username="ali", password="Parol-12345")
        self.api = APIClient()
        self.api.force_authenticate(self.user)
        self.a = self.wallet("A", 0)
        self.b = self.wallet("B", 0)

    def wallet(self, name, summa, currency="UZS", user=None):
        return Wallet.objects.create(user=user or self.user, name=name, summa=summa, currency=currency)

    def balance(self, wallet):
        wallet.refresh_from_db()
        return wallet.summa

    def post(self, path, payload):
        return self.api.post(f"{API}/{path}/", payload, format="json")

    def put(self, path, pk, payload):
        return self.api.put(f"{API}/{path}/{pk}/", payload, format="json")

    def patch(self, path, pk, payload):
        return self.api.patch(f"{API}/{path}/{pk}/", payload, format="json")

    def income(self, wallet, summa, **extra):
        res = self.post("incomes", {"wallet": wallet.id, "summa": summa, **extra})
        self.assertEqual(res.status_code, 201, res.content)
        return res.json()

    def expense(self, wallet, summa, **extra):
        category = extra.pop("category", None) or ExpenseCategory.objects.create(name="Turkum").id
        res = self.post("expenses", {"wallet": wallet.id, "summa": summa, "category": category, **extra})
        self.assertEqual(res.status_code, 201, res.content)
        return res.json()

    def transfer(self, source, target, summa, **extra):
        res = self.post("transfers", {"from_wallet": source.id, "to_wallet": target.id, "summa": summa, **extra})
        self.assertEqual(res.status_code, 201, res.content)
        return res.json()

    def debt(self, wallet, summa, debt_type="give", **extra):
        res = self.post("debts", {"person_name": "Rustam", "debt_type": debt_type, "summa": summa,
                                  "wallet": wallet.id, **extra})
        self.assertEqual(res.status_code, 201, res.content)
        return res.json()

    def delete_wallet_quietly(self, wallet):
        """Hamyon o'chirilgan, lekin yozuvlari qolgan holat (API buni qoldiq 0 bo'lganda ruxsat etadi)"""
        Wallet.objects.filter(pk=wallet.pk).update(status=False)


class ApplyWalletChangesTests(BalanceTestCase):
    def test_same_row_through_different_instances_is_netted(self):
        """Eski va yangi effektdagi hamyon boshqa-boshqa Python obyekti, lekin bitta qator: sof farq 0 — hamyonga tegilmaydi"""
        first, second = Wallet.objects.get(pk=self.a.pk), Wallet.objects.get(pk=self.a.pk)
        self.assertIsNot(first, second)
        apply_wallet_changes([(first, 5000)], [(second, 5000)])  # balans 0: farq yo'q — xatosiz
        self.assertEqual(self.balance(self.a), 0)

    def test_only_difference_is_applied(self):
        self.a.summa = 500
        self.a.save()
        apply_wallet_changes([(Wallet.objects.get(pk=self.a.pk), 5200)], [(Wallet.objects.get(pk=self.a.pk), 5000)])
        self.assertEqual(self.balance(self.a), 700)

    def test_moving_between_wallets(self):
        self.a.summa = 1000
        self.a.save()
        apply_wallet_changes([(self.b, 1000)], [(self.a, 1000)])
        self.assertEqual((self.balance(self.a), self.balance(self.b)), (0, 1000))

    def test_failure_rolls_back_the_whole_change(self):
        self.b.summa = 10
        self.b.save()
        with self.assertRaises(ValueError):
            apply_wallet_changes([(self.a, 300), (self.b, -999)])
        self.assertEqual((self.balance(self.a), self.balance(self.b)), (0, 10))


class IncomeEditTests(BalanceTestCase):
    """№8: daromad tahriri pul sarflangandan keyin"""

    def setUp(self):
        super().setUp()
        self.inc = self.income(self.a, 5000, description="Oylik")
        self.expense(self.a, 4500)  # balans: 5000 - 4500 = 500
        self.url = ("incomes", self.inc["id"])

    def test_note_only_edit_is_allowed_when_balance_is_below_income(self):
        """Asl xato: qoldiq 500 < 5000 — izohni o'zgartirish ham "mablag' yetarli emas" berardi"""
        for method in (self.put, self.patch):
            with self.subTest(method=method.__name__):
                payload = {"wallet": self.a.id, "summa": 5000, "description": f"Yangi izoh {method.__name__}"}
                res = method(*self.url, payload)
                self.assertEqual(res.status_code, 200, res.content)
                self.assertEqual(self.balance(self.a), 500)
        self.assertTrue(Income.objects.get(pk=self.inc["id"]).description.startswith("Yangi izoh"))

    def test_increase_adds_only_the_difference(self):
        self.assertEqual(self.patch(*self.url, {"summa": 6000}).status_code, 200)
        self.assertEqual(self.balance(self.a), 1500)

    def test_decrease_within_balance(self):
        self.assertEqual(self.patch(*self.url, {"summa": 4600}).status_code, 200)
        self.assertEqual(self.balance(self.a), 100)

    def test_decrease_beyond_balance_is_rejected_and_nothing_changes(self):
        res = self.patch(*self.url, {"summa": 4000})  # 1000 ni qaytarish kerak, hamyonda 500
        self.assertEqual(res.status_code, 400)
        self.assertEqual(self.balance(self.a), 500)
        self.assertEqual(Income.objects.get(pk=self.inc["id"]).summa, 5000)

    def test_moving_to_other_wallet_needs_the_money_in_the_old_one(self):
        res = self.patch(*self.url, {"wallet": self.b.id})
        self.assertEqual(res.status_code, 400)
        self.assertEqual((self.balance(self.a), self.balance(self.b)), (500, 0))
        self.assertEqual(Income.objects.get(pk=self.inc["id"]).wallet_id, self.a.id)

    def test_moving_to_other_wallet_when_money_is_there(self):
        inc = self.income(self.b, 300)
        res = self.patch("incomes", inc["id"], {"wallet": self.a.id})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual((self.balance(self.a), self.balance(self.b)), (800, 0))


class ExpenseEditTests(BalanceTestCase):
    def setUp(self):
        super().setUp()
        self.a.summa = 1000
        self.a.save()
        self.exp = self.expense(self.a, 1000, description="Non")  # balans 0
        self.url = ("expenses", self.exp["id"])

    def test_note_only_edit_with_empty_wallet(self):
        res = self.patch(*self.url, {"description": "Somsa"})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(self.balance(self.a), 0)

    def test_full_put_with_same_values(self):
        payload = {"wallet": self.a.id, "summa": 1000, "category": self.exp["category"], "description": "Boshqa"}
        res = self.put(*self.url, payload)
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(self.balance(self.a), 0)

    def test_decrease_refunds_only_the_difference(self):
        self.assertEqual(self.patch(*self.url, {"summa": 400}).status_code, 200)
        self.assertEqual(self.balance(self.a), 600)

    def test_increase_beyond_balance_is_rejected(self):
        res = self.patch(*self.url, {"summa": 1001})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(self.balance(self.a), 0)
        self.assertEqual(Expense.objects.get(pk=self.exp["id"]).summa, 1000)

    def test_moving_to_poorer_wallet_fails_without_refunding_the_old_one(self):
        res = self.patch(*self.url, {"wallet": self.b.id})  # B da pul yo'q
        self.assertEqual(res.status_code, 400)
        self.assertEqual((self.balance(self.a), self.balance(self.b)), (0, 0))

    def test_moving_to_other_wallet(self):
        self.b.summa = 1500
        self.b.save()
        self.assertEqual(self.patch(*self.url, {"wallet": self.b.id}).status_code, 200)
        self.assertEqual((self.balance(self.a), self.balance(self.b)), (1000, 500))


class TransferEditTests(BalanceTestCase):
    def setUp(self):
        super().setUp()
        self.a.summa = 2000
        self.a.save()
        self.tr = self.transfer(self.a, self.b, 1000, description="Karta")
        self.expense(self.b, 1000)  # B ga tushgan pul sarflandi: A=1000, B=0
        self.url = ("transfers", self.tr["id"])

    def test_note_only_edit_after_receiver_spent_the_money(self):
        """Asl xato: tahrirda eski o'tkazma to'liq qaytarilardi — B da 1000 yo'q, shuning uchun rad etilardi"""
        for method in (self.put, self.patch):
            with self.subTest(method=method.__name__):
                payload = {"from_wallet": self.a.id, "to_wallet": self.b.id, "summa": 1000,
                           "description": f"Izoh {method.__name__}"}
                res = method(*self.url, payload)
                self.assertEqual(res.status_code, 200, res.content)
                self.assertEqual((self.balance(self.a), self.balance(self.b)), (1000, 0))

    def test_increase_moves_only_the_difference(self):
        self.assertEqual(self.patch(*self.url, {"summa": 1500}).status_code, 200)
        self.assertEqual((self.balance(self.a), self.balance(self.b)), (500, 500))

    def test_decrease_needs_the_money_in_receiver_and_rolls_back(self):
        res = self.patch(*self.url, {"summa": 600})  # B dan 400 qaytarish kerak, B da 0
        self.assertEqual(res.status_code, 400)
        self.assertEqual((self.balance(self.a), self.balance(self.b)), (1000, 0))
        self.assertEqual(Transfer.objects.get(pk=self.tr["id"]).summa, 1000)

    def test_increase_beyond_sender_balance_is_rejected(self):
        res = self.patch(*self.url, {"summa": 2001})  # A da 1000 + eski 1000 = 2000 mavjud
        self.assertEqual(res.status_code, 400)
        self.assertEqual((self.balance(self.a), self.balance(self.b)), (1000, 0))

    def test_repointing_receiver_needs_the_money_in_old_receiver(self):
        c = self.wallet("C", 0)
        res = self.patch(*self.url, {"to_wallet": c.id})
        self.assertEqual(res.status_code, 400)
        self.assertEqual((self.balance(self.a), self.balance(self.b), self.balance(c)), (1000, 0, 0))

    def test_repointing_receiver_when_money_is_there(self):
        c = self.wallet("C", 0)
        self.b.summa = 1000
        self.b.save()
        self.assertEqual(self.patch(*self.url, {"to_wallet": c.id}).status_code, 200)
        self.assertEqual((self.balance(self.a), self.balance(self.b), self.balance(c)), (1000, 0, 1000))


class DebtEditTests(BalanceTestCase):
    """№9: qarzni tahrirlash qoldiqni buzmasligi kerak"""

    def setUp(self):
        super().setUp()
        self.a.summa = 1000
        self.a.save()

    def test_type_change_of_partially_paid_debt_is_rejected(self):
        """Asl xato: give 500, 200 to'langan, take ga o'zgartirilsa qoldiq noto'g'ri (2 × to'langan) bo'lardi"""
        debt = self.debt(self.a, 500)  # 500
        self.assertEqual(self.post(f"debts/{debt['id']}/repay", {"amount": 200, "wallet": self.a.id}).status_code, 200)
        self.assertEqual(self.balance(self.a), 700)
        res = self.patch("debts", debt["id"], {"debt_type": "take"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("turini", res.json()["error"])
        self.assertEqual(self.balance(self.a), 700)
        self.assertEqual(Debt.objects.get(pk=debt["id"]).debt_type, "give")

    def test_type_change_of_unpaid_debt_flips_the_balance_once(self):
        debt = self.debt(self.a, 500)  # 500
        res = self.patch("debts", debt["id"], {"debt_type": "take"})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(self.balance(self.a), 1500)

    def test_model_level_guard_for_type_change(self):
        debt = self.debt(self.a, 500)
        self.post(f"debts/{debt['id']}/repay", {"amount": 100, "wallet": self.a.id})
        obj = Debt.objects.get(pk=debt["id"])
        obj.debt_type = "take"
        with self.assertRaises(ValidationError):
            obj.save()
        self.assertEqual(self.balance(self.a), 600)

    def test_moving_to_other_currency_wallet_is_rejected(self):
        usd = self.wallet("USD", 100, currency="USD")
        debt = self.debt(self.a, 500)
        res = self.patch("debts", debt["id"], {"wallet": usd.id})
        self.assertEqual(res.status_code, 400)
        self.assertIn("ko'chirib bo'lmaydi", res.json()["error"])
        self.assertEqual((self.balance(self.a), self.balance(usd)), (500, 100))
        self.assertEqual(Debt.objects.get(pk=debt["id"]).wallet_id, self.a.id)

    def test_model_level_guard_for_wallet_currency(self):
        usd = self.wallet("USD", 100, currency="USD")
        obj = Debt.objects.get(pk=self.debt(self.a, 500)["id"])
        obj.wallet = usd
        with self.assertRaises(ValidationError):
            obj.save()
        self.assertEqual((self.balance(self.a), self.balance(usd)), (500, 100))

    def test_moving_to_same_currency_wallet(self):
        debt = self.debt(self.a, 500)
        res = self.patch("debts", debt["id"], {"wallet": self.b.id})
        self.assertEqual(res.status_code, 400)  # B da 500 yo'q: "give" B dan yechadi
        self.assertEqual((self.balance(self.a), self.balance(self.b)), (500, 0))
        self.b.summa = 500
        self.b.save()
        res = self.patch("debts", debt["id"], {"wallet": self.b.id})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual((self.balance(self.a), self.balance(self.b)), (1000, 0))

    def test_note_and_repayment_do_not_touch_the_balance(self):
        debt = self.debt(self.a, 500, debt_type="take")  # 1500
        self.post(f"debts/{debt['id']}/repay", {"amount": 100, "wallet": self.a.id})  # 1400
        res = self.patch("debts", debt["id"], {"description": "Izoh"})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(self.balance(self.a), 1400)

    def test_amount_edit_applies_difference_with_payments_kept(self):
        debt = self.debt(self.a, 500)  # 500
        self.post(f"debts/{debt['id']}/repay", {"amount": 100, "wallet": self.a.id})  # 600
        self.assertEqual(self.patch("debts", debt["id"], {"summa": 700}).status_code, 200)
        self.assertEqual(self.balance(self.a), 400)  # 600 - 200
        # qarz o'chirilganda qoldig'i (700 - 100) qaytadi: boshlang'ich 1000 ga teng
        self.assertEqual(self.api.delete(f"{API}/debts/{debt['id']}/").status_code, 200)
        self.assertEqual(self.balance(self.a), 1000)

    def test_amount_cannot_drop_below_paid(self):
        debt = self.debt(self.a, 500)
        self.post(f"debts/{debt['id']}/repay", {"amount": 300, "wallet": self.a.id})
        self.assertEqual(self.patch("debts", debt["id"], {"summa": 200}).status_code, 400)

    def test_legacy_debt_without_wallet(self):
        legacy = Debt.objects.create(user=self.user, person_name="Eski", debt_type="give", summa=400, wallet=None)
        self.assertEqual(self.patch("debts", legacy.id, {"description": "Izoh"}).status_code, 200)
        self.assertEqual(self.patch("debts", legacy.id, {"summa": 450, "person_name": "Yangi"}).status_code, 200)
        self.assertEqual(self.balance(self.a), 1000)
        # PUT da hamyon majburiy
        res = self.put("debts", legacy.id, {"person_name": "Eski", "debt_type": "give", "summa": 450})
        self.assertEqual(res.status_code, 400)
        # hamyon biriktirilsa, "give" summasi hamyondan yechiladi
        res = self.patch("debts", legacy.id, {"wallet": self.a.id})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(self.balance(self.a), 550)

    def test_debt_on_deleted_wallet_cannot_be_edited(self):
        debt = self.debt(self.a, 500)
        self.delete_wallet_quietly(self.a)
        res = self.patch("debts", debt["id"], {"description": "Izoh"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("tahrirlab", res.json()["error"])


class DeletedWalletEditTests(BalanceTestCase):
    """№10: o'chirilgan hamyondagi yozuvni tahrirlash rad etiladi (pul ko'rinmas hamyonga o'tmasin)"""

    def setUp(self):
        super().setUp()
        self.a.summa = 10_000
        self.a.save()

    def assert_rejected(self, res):
        self.assertEqual(res.status_code, 400, res.content)
        self.assertIn("o'chirilgan hamyon", res.json()["error"])
        self.assertIn("tahrirlab", res.json()["error"])

    def test_income(self):
        inc = self.income(self.a, 1000)
        self.delete_wallet_quietly(self.a)
        self.assert_rejected(self.patch("incomes", inc["id"], {"description": "Izoh"}))
        self.assert_rejected(self.patch("incomes", inc["id"], {"wallet": self.b.id}))
        self.assertEqual((self.balance(self.a), self.balance(self.b)), (11_000, 0))
        self.assertEqual(Income.objects.get(pk=inc["id"]).wallet_id, self.a.id)

    def test_expense_cannot_be_moved_off_a_deleted_wallet(self):
        exp = self.expense(self.a, 1000)
        self.delete_wallet_quietly(self.a)
        self.b.summa = 5000
        self.b.save()
        self.assert_rejected(self.patch("expenses", exp["id"], {"wallet": self.b.id}))
        self.assert_rejected(self.put("expenses", exp["id"], {"wallet": self.b.id, "summa": 1000, "category": exp["category"]}))
        self.assertEqual((self.balance(self.a), self.balance(self.b)), (9000, 5000))

    def test_transfer_on_either_side(self):
        for deleted, other in (("a", "b"), ("b", "a")):
            with self.subTest(deleted=deleted):
                Wallet.objects.update(status=True)
                Wallet.objects.filter(pk=self.a.pk).update(summa=10_000)
                Wallet.objects.filter(pk=self.b.pk).update(summa=0)
                Transfer.objects.all().delete()
                tr = self.transfer(self.a, self.b, 1000)
                self.delete_wallet_quietly(getattr(self, deleted))
                self.assert_rejected(self.patch("transfers", tr["id"], {"description": "Izoh"}))
                self.assertEqual((self.balance(self.a), self.balance(self.b)), (9000, 1000))

    def test_live_wallet_records_still_editable_and_destroy_message_unchanged(self):
        inc = self.income(self.b, 1000)
        self.assertEqual(self.patch("incomes", inc["id"], {"description": "Izoh"}).status_code, 200)
        self.delete_wallet_quietly(self.b)
        res = self.api.delete(f"{API}/incomes/{inc['id']}/")
        self.assertEqual(res.status_code, 400)
        self.assertIn("bekor qilib", res.json()["error"])


class HiddenAndDeletedRelationsTests(BalanceTestCase):
    """№15: o'chirilgan/yashirilgan turkum va a'zo"""

    def setUp(self):
        super().setUp()
        self.a.summa = 100_000
        self.a.save()
        self.inc_cat = Category.objects.create(name="Manba")
        self.other_inc_cat = Category.objects.create(name="Boshqa manba")
        self.exp_cat = ExpenseCategory.objects.create(name="Ovqat")
        self.other_exp_cat = ExpenseCategory.objects.create(name="Transport")
        self.member = Member.objects.create(user=self.user, name="Ukam")

    def test_expense_with_since_deleted_category_and_member_can_be_put_back(self):
        exp = self.expense(self.a, 1000, category=self.exp_cat.id, member=self.member.id)
        ExpenseCategory.objects.filter(pk=self.exp_cat.pk).update(status=False)
        Member.objects.filter(pk=self.member.pk).update(status=False)
        payload = {"wallet": self.a.id, "summa": 1500, "category": self.exp_cat.id, "member": self.member.id,
                   "description": "Izoh"}
        res = self.put("expenses", exp["id"], payload)
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(self.balance(self.a), 100_000 - 1500)

    def test_deleted_category_or_member_cannot_be_chosen_for_other_records(self):
        exp = self.expense(self.a, 1000, category=self.exp_cat.id)
        ExpenseCategory.objects.filter(pk=self.other_exp_cat.pk).update(status=False)
        Member.objects.filter(pk=self.member.pk).update(status=False)
        self.assertEqual(self.patch("expenses", exp["id"], {"category": self.other_exp_cat.id}).status_code, 400)
        self.assertEqual(self.patch("expenses", exp["id"], {"member": self.member.id}).status_code, 400)
        new = self.post("expenses", {"wallet": self.a.id, "summa": 10, "category": self.other_exp_cat.id})
        self.assertEqual(new.status_code, 400)

    def test_income_with_since_deleted_category(self):
        inc = self.income(self.a, 1000, category=self.inc_cat.id)
        Category.objects.filter(pk=self.inc_cat.pk).update(status=False)
        payload = {"wallet": self.a.id, "summa": 1000, "category": self.inc_cat.id, "description": "Izoh"}
        self.assertEqual(self.put("incomes", inc["id"], payload).status_code, 200)
        self.assertEqual(self.patch("incomes", inc["id"], {"category": self.other_inc_cat.id}).status_code, 200)
        # endi eski toifaga qaytib bo'lmaydi: u joriy qiymat emas
        self.assertEqual(self.patch("incomes", inc["id"], {"category": self.inc_cat.id}).status_code, 400)

    def test_hidden_income_category_cannot_be_chosen_for_new_record(self):
        self.user.hidden_income_categories.add(self.inc_cat)
        res = self.post("incomes", {"wallet": self.a.id, "summa": 100, "category": self.inc_cat.id})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["error"], "Turkum topilmadi")
        self.assertEqual(self.post("incomes", {"wallet": self.a.id, "summa": 100,
                                               "category": self.other_inc_cat.id}).status_code, 201)

    def test_hidden_expense_category_cannot_be_chosen_for_new_record(self):
        self.user.hidden_expense_categories.add(self.exp_cat)
        res = self.post("expenses", {"wallet": self.a.id, "summa": 100, "category": self.exp_cat.id})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(self.balance(self.a), 100_000)

    def test_old_record_with_since_hidden_category_stays_editable_but_cannot_switch_to_another_hidden_one(self):
        exp = self.expense(self.a, 1000, category=self.exp_cat.id)
        self.user.hidden_expense_categories.add(self.exp_cat, self.other_exp_cat)
        payload = {"wallet": self.a.id, "summa": 1000, "category": self.exp_cat.id, "description": "Izoh"}
        self.assertEqual(self.put("expenses", exp["id"], payload).status_code, 200)
        self.assertEqual(self.patch("expenses", exp["id"], {"category": self.other_exp_cat.id}).status_code, 400)

    def test_hiding_is_per_user(self):
        other = User.objects.create_user(username="vali", password="Parol-12345")
        other.hidden_income_categories.add(self.inc_cat)
        res = self.post("incomes", {"wallet": self.a.id, "summa": 100, "category": self.inc_cat.id})
        self.assertEqual(res.status_code, 201, res.content)

    def test_foreign_private_category_is_still_rejected(self):
        other = User.objects.create_user(username="vali", password="Parol-12345")
        private = Category.objects.create(name="Vali", user=other)
        inc = self.income(self.a, 100)
        self.assertEqual(self.patch("incomes", inc["id"], {"category": private.id}).status_code, 400)

    def test_serializer_with_many_and_a_list_or_queryset_instance(self):
        """many=True da child.instance — ro'yxat/queryset: keep_current_relations xato bermasligi kerak"""
        self.expense(self.a, 100, category=self.exp_cat.id, member=self.member.id)
        self.income(self.a, 100, category=self.inc_cat.id)
        request = mock.Mock(user=self.user)
        for instance in (Expense.objects.all(), list(Expense.objects.all())):
            data = ExpenseSerializer(instance, many=True, context={"request": request}).data
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["category"], self.exp_cat.id)
        data = IncomeSerializer(Income.objects.all(), many=True, context={"request": request}).data
        self.assertEqual(data[0]["category"], self.inc_cat.id)

    def test_list_endpoints_still_work(self):
        self.expense(self.a, 100, category=self.exp_cat.id)
        self.income(self.a, 100, category=self.inc_cat.id)
        for path in ("expenses", "incomes"):
            self.assertEqual(self.api.get(f"{API}/{path}/").status_code, 200)


class TransferRateTests(BalanceTestCase):
    """№16: kurs chegarasi va miqdor o'zgarmagan tahrirda to_miqdor saqlanishi"""

    def setUp(self):
        super().setUp()
        self.uzs = self.wallet("UZS", 3_000_000_000)
        self.usd = self.wallet("USD", 0, currency="USD")

    def payload(self, summa, to_summa=None, **extra):
        data = {"from_wallet": self.uzs.id, "to_wallet": self.usd.id, "summa": summa, **extra}
        if to_summa is not None:
            data["to_summa"] = to_summa
        return data

    def test_absurd_rate_is_a_400_not_a_500(self):
        """Asl xato: miqdor=0.01, to_miqdor=10^12 -> decimal.InvalidOperation (500)"""
        res = self.post("transfers", self.payload(Decimal("0.01"), 10 ** 12))
        self.assertEqual(res.status_code, 400, res.content)
        self.assertIn("kurs", res.json()["error"])
        self.assertEqual(Transfer.objects.count(), 0)
        self.assertEqual((self.balance(self.uzs), self.balance(self.usd)), (3_000_000_000, 0))

    def test_rate_boundary(self):
        self.assertEqual(self.post("transfers", self.payload(1, 10 ** 12)).status_code, 400)
        res = self.post("transfers", self.payload(1, 10 ** 12 - 1))
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(Decimal(res.json()["rate"]), Decimal(10 ** 12 - 1))

    def test_absurd_rate_on_edit(self):
        tr = self.transfer(self.uzs, self.usd, 1000, to_summa=1)
        res = self.patch("transfers", tr["id"], {"to_summa": 10 ** 15})
        self.assertEqual(res.status_code, 400, res.content)
        self.assertEqual(Transfer.objects.get(pk=tr["id"]).to_summa, 1)
        self.assertEqual(self.balance(self.usd), 1)

    def test_absurd_automatic_rate(self):
        with mock.patch("mainapp.serializers.convert", return_value=(10 ** 12, Decimal(10 ** 14))):
            res = self.post("transfers", self.payload(1))
        self.assertEqual(res.status_code, 400, res.content)
        self.assertIn("kurs", res.json()["error"])

    def test_tiny_rate_is_a_400_not_a_zero_rate(self):
        """Asl xato: miqdor=10^12, to_miqdor=1 -> kurs 0 bo'lib saqlanardi, keyin miqdorni tahrirlash "Miqdor juda kichik" berardi"""
        res = self.post("transfers", self.payload(10 ** 12, 1))
        self.assertEqual(res.status_code, 400, res.content)
        self.assertIn(MIN_RATE_MESSAGE, res.json()["error"])
        self.assertEqual(Transfer.objects.count(), 0)
        self.assertEqual((self.balance(self.uzs), self.balance(self.usd)), (3_000_000_000, 0))

    def test_tiny_rate_error_is_on_to_summa_when_entered_by_user(self):
        context = {"request": mock.Mock(user=self.user)}
        ser = TransferSerializer(data=self.payload(10 ** 12, 1), context=context)
        self.assertFalse(ser.is_valid())
        self.assertEqual(list(ser.errors), ["to_summa"])

    def test_min_rate_boundary(self):
        # 1 / 10^8 = 0.00000001 — ustun saqlay oladigan eng kichik kurs
        res = self.post("transfers", self.payload(10 ** 8, 1))
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(Transfer.objects.get(pk=res.json()["id"]).rate, MIN_RATE)
        # 1 / (3 * 10^8) = 3.3e-9 -> 8 xonaga yaxlitlanganda 0 bo'lardi
        res = self.post("transfers", self.payload(3 * 10 ** 8, 1))
        self.assertEqual(res.status_code, 400, res.content)
        self.assertEqual(Transfer.objects.count(), 1)
        self.assertEqual(self.balance(self.usd), 1)

    def test_tiny_rate_on_edit(self):
        tr = self.transfer(self.uzs, self.usd, 1000, to_summa=1)
        res = self.patch("transfers", tr["id"], {"summa": 10 ** 12, "to_summa": 1})
        self.assertEqual(res.status_code, 400, res.content)
        self.assertIn(MIN_RATE_MESSAGE, res.json()["error"])
        obj = Transfer.objects.get(pk=tr["id"])
        self.assertEqual((obj.summa, obj.to_summa, obj.rate), (1000, 1, Decimal("0.001")))
        self.assertEqual(self.balance(self.usd), 1)

    def test_tiny_automatic_rate(self):
        """convert() orqali hisoblangan kurs 0 bo'lib qolsa ham 400 (xato "summa" maydoniga yoziladi)"""
        context = {"request": mock.Mock(user=self.user)}
        with mock.patch("mainapp.serializers.convert", return_value=(5, Decimal("0"))):
            res = self.post("transfers", self.payload(10 ** 12))
            ser = TransferSerializer(data=self.payload(10 ** 15), context=context)
            self.assertFalse(ser.is_valid())
        self.assertEqual(res.status_code, 400, res.content)
        self.assertIn(MIN_RATE_MESSAGE, res.json()["error"])
        self.assertEqual(list(ser.errors), ["summa"])
        self.assertEqual(Transfer.objects.count(), 0)

    def test_min_automatic_rate_is_accepted(self):
        with mock.patch("mainapp.serializers.convert", return_value=(5, MIN_RATE)):
            res = self.post("transfers", self.payload(5 * 10 ** 8))
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(Transfer.objects.get(pk=res.json()["id"]).rate, MIN_RATE)

    def test_normal_automatic_transfer_still_works(self):
        with mock.patch("mainapp.serializers.convert", return_value=(80, Decimal("0.0000800"))):
            res = self.post("transfers", self.payload(1_000_000))
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(Transfer.objects.get(pk=res.json()["id"]).rate, Decimal("0.00008"))
        self.assertEqual((self.balance(self.uzs), self.balance(self.usd)), (3_000_000_000 - 1_000_000, 80))

    def test_summa_only_edit_with_minimum_rate(self):
        tr = self.transfer(self.uzs, self.usd, 10 ** 8, to_summa=1)  # kurs 0.00000001
        self.assertEqual(self.patch("transfers", tr["id"], {"summa": 5 * 10 ** 8}).status_code, 200)
        self.assertEqual(Transfer.objects.get(pk=tr["id"]).to_summa, 5)
        self.assertEqual(self.balance(self.usd), 5)
        # kurs bo'yicha 0 bo'ladigan summa: "Summa juda kichik", hech narsa o'zgarmaydi
        res = self.patch("transfers", tr["id"], {"summa": 10})
        self.assertEqual(res.status_code, 400, res.content)
        self.assertIn("Miqdor juda kichik", res.json()["error"])
        self.assertEqual(Transfer.objects.get(pk=tr["id"]).summa, 5 * 10 ** 8)
        self.assertEqual(self.balance(self.usd), 5)

    def test_unchanged_put_keeps_to_summa_and_rate(self):
        """Asl xato: kurs 8 xonaga yaxlitlanadi (7 / 10^9 -> 1e-8), PUT da to_miqdor jimgina 7 dan 10 ga o'zgarardi"""
        tr = self.transfer(self.uzs, self.usd, 10 ** 9, to_summa=7)
        rate = Transfer.objects.get(pk=tr["id"]).rate
        self.assertEqual(self.balance(self.usd), 7)
        res = self.put("transfers", tr["id"], self.payload(10 ** 9, description="Izoh"))
        self.assertEqual(res.status_code, 200, res.content)
        obj = Transfer.objects.get(pk=tr["id"])
        self.assertEqual((obj.to_summa, obj.rate, obj.description), (7, rate, "Izoh"))
        self.assertEqual(self.balance(self.usd), 7)
        # to_summa o'zgarmagan qiymat bilan yuborilsa ham xuddi shunday
        res = self.put("transfers", tr["id"], self.payload(10 ** 9, 7, description="Yana"))
        self.assertEqual(res.status_code, 200, res.content)
        obj.refresh_from_db()
        self.assertEqual((obj.to_summa, obj.rate), (7, rate))

    def test_changed_to_summa_recomputes_rate(self):
        tr = self.transfer(self.uzs, self.usd, 1000, to_summa=1)
        res = self.patch("transfers", tr["id"], {"to_summa": 4})
        self.assertEqual(res.status_code, 200, res.content)
        obj = Transfer.objects.get(pk=tr["id"])
        self.assertEqual((obj.to_summa, obj.rate), (4, Decimal("0.004")))
        self.assertEqual(self.balance(self.usd), 4)

    def test_changed_summa_uses_stored_rate(self):
        tr = self.transfer(self.uzs, self.usd, 1000, to_summa=10)  # kurs 0.01
        self.assertEqual(self.patch("transfers", tr["id"], {"summa": 5000}).status_code, 200)
        self.assertEqual(Transfer.objects.get(pk=tr["id"]).to_summa, 50)
        self.assertEqual(self.balance(self.usd), 50)

    def test_same_currency_unchanged_put(self):
        self.a.summa = 500
        self.a.save()
        tr = self.transfer(self.a, self.b, 300)
        res = self.put("transfers", tr["id"], {"from_wallet": self.a.id, "to_wallet": self.b.id, "summa": 300,
                                               "description": "Izoh"})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual((self.balance(self.a), self.balance(self.b)), (200, 300))


class RepayInputTests(BalanceTestCase):
    """№17: /repay/ — miqdor haqiqiy butun son, hamyon majburiy"""

    def setUp(self):
        super().setUp()
        self.a.summa = 1000
        self.a.save()
        self.debt_data = self.debt(self.a, 500)  # give: hamyon 500
        self.url = f"debts/{self.debt_data['id']}/repay"

    def paid(self):
        return Debt.objects.get(pk=self.debt_data["id"]).paid_summa

    def assert_untouched(self):
        self.assertEqual(self.paid(), 0)
        self.assertEqual(self.balance(self.a), 500)

    def test_fractional_amount_is_rejected(self):
        """Asl xato: int(99.9) jimgina 99 bo'lardi"""
        for amount in (99.999, "99.001", 0.001, 100.0000001):
            with self.subTest(amount=amount):
                res = self.post(self.url, {"amount": amount, "wallet": self.a.id})
                self.assertEqual(res.status_code, 400, res.content)
                self.assertIn("kasr xonasi", res.json()["error"])
        self.assert_untouched()

    def test_boolean_amount_is_rejected(self):
        """Asl xato: JSON true int() da 1 bo'lardi"""
        for amount in (True, False):
            with self.subTest(amount=amount):
                self.assertEqual(self.post(self.url, {"amount": amount, "wallet": self.a.id}).status_code, 400)
        self.assert_untouched()

    def test_garbage_amount_is_rejected(self):
        for amount in ("abc", "", "1e2", "1_0", "+5", "١٢٣", "５０", None, [5], {"a": 1}):
            with self.subTest(amount=amount):
                res = self.post(self.url, {"amount": amount, "wallet": self.a.id})
                self.assertEqual(res.status_code, 400, res.content)
        self.assert_untouched()

    def test_missing_amount_and_non_positive_amount(self):
        self.assertEqual(self.post(self.url, {"wallet": self.a.id}).status_code, 400)
        for amount in (0, -5, "0", -5.0):
            with self.subTest(amount=amount):
                self.assertEqual(self.post(self.url, {"amount": amount, "wallet": self.a.id}).status_code, 400)
        self.assert_untouched()

    def test_huge_amounts_are_400_not_500(self):
        for amount in (MAX_AMOUNT + 1, 1e30, "9" * 30, "9" * 5000):
            with self.subTest(amount=str(amount)[:20]):
                self.assertEqual(self.post(self.url, {"amount": amount, "wallet": self.a.id}).status_code, 400)
        self.assert_untouched()

    def test_integer_forms_are_accepted(self):
        for amount, expected in ((100, 100), (50.0, 50), ("25", 25), (" 5 ", 5)):
            with self.subTest(amount=amount):
                before = self.paid()
                res = self.post(self.url, {"amount": amount, "wallet": self.a.id})
                self.assertEqual(res.status_code, 200, res.content)
                self.assertEqual(self.paid() - before, expected)
        self.assertEqual(self.balance(self.a), 500 + 180)

    def test_form_encoded_request(self):
        res = self.api.post(f"{API}/{self.url}/", {"amount": "40", "wallet": str(self.a.id)})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual((self.paid(), self.balance(self.a)), (40, 540))

    def test_wallet_is_required(self):
        """Asl xato: hamyonsiz to'lov qarzni kamaytirardi, lekin hech qaysi qoldiqqa tushmasdi"""
        for payload in ({"amount": 100}, {"amount": 100, "wallet": None}, {"amount": 100, "wallet": ""}):
            with self.subTest(payload=payload):
                res = self.post(self.url, payload)
                self.assertEqual(res.status_code, 400, res.content)
                self.assertEqual(res.json()["error"], "Hamyonni tanlang")
        self.assert_untouched()

    def test_malformed_or_foreign_wallet_is_not_found(self):
        stranger = User.objects.create_user(username="vali", password="Parol-12345")
        foreign = self.wallet("Begona", 0, user=stranger)
        for wallet in (True, 1.5, "abc", [1], {"id": 1}, 0, foreign.id):
            with self.subTest(wallet=wallet):
                self.assertEqual(self.post(self.url, {"amount": 100, "wallet": wallet}).status_code, 404)
        self.assert_untouched()
        self.assertEqual(self.balance(foreign), 0)

    def test_wallet_balance_follows_the_debt_type(self):
        take = self.debt(self.a, 300, debt_type="take")  # hamyon 800
        self.assertEqual(self.balance(self.a), 800)
        res = self.post(f"debts/{take['id']}/repay", {"amount": 100, "wallet": self.a.id})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["wallet_amount"], 100)
        self.assertEqual(self.balance(self.a), 700)

    def test_repaying_a_legacy_debt_without_wallet_needs_a_wallet(self):
        legacy = Debt.objects.create(user=self.user, person_name="Eski", debt_type="give", summa=400, wallet=None)
        self.assertEqual(self.post(f"debts/{legacy.id}/repay", {"amount": 100}).status_code, 400)
        self.assertEqual(Debt.objects.get(pk=legacy.id).paid_summa, 0)
        self.assertEqual(self.post(f"debts/{legacy.id}/repay", {"amount": 100, "wallet": self.a.id}).status_code, 200)
        self.assertEqual((Debt.objects.get(pk=legacy.id).paid_summa, self.balance(self.a)), (100, 600))


class StrictIntTests(TestCase):
    def test_accepted(self):
        for value, expected in ((5, 5), (0, 0), (-3, -3), (99.0, 99), ("42", 42), (" 7 ", 7), ("007", 7), ("-1", -1)):
            with self.subTest(value=value):
                self.assertEqual(strict_int(value), expected)

    def test_rejected(self):
        for value in (True, False, 99.9, float("nan"), float("inf"), "99.9", "", " ", "abc", "-", "+1", "1_0", "1e3",
                      "٣", None, [1], (1,), {"a": 1}, b"5", Decimal("5"), "1" * 5000):
            with self.subTest(value=repr(value)[:30]):
                self.assertIsNone(strict_int(value))
