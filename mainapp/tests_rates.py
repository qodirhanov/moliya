"""plans.md №26: daromad/harajat yozilgan paytdagi kurs (uzs_rate) qatorning o'zida saqlanadi va statistika shundan foydalanadi."""
import importlib
from decimal import Decimal
from unittest import mock

from django.apps import apps
from django.db import connection
from django.test import TestCase

from .currency import CurrencyRateError
from .models import MAX_AMOUNT, Category, ExchangeRate, Expense, ExpenseCategory, Income, Wallet
from .tests import API, APITestCase, make_user


def usd_wallet(user, summa=1_000_000, name="Dollar"):
    return Wallet.objects.create(user=user, name=name, summa=summa, currency="USD")


def uzs_wallet(user, summa=1_000_000, name="So'm"):
    return Wallet.objects.create(user=user, name=name, summa=summa, currency="UZS")


class RateOnSaveTests(APITestCase):
    """Kurs yozuv yaratilganda olinadi; tahrirda faqat boshqa valyutali hamyonga ko'chganda almashadi"""

    def setUp(self):
        super().setUp()
        ExchangeRate.objects.create(currency="USD", rate=Decimal("12000"))
        self.user = make_user("ali")
        self.uzs = uzs_wallet(self.user)
        self.usd = usd_wallet(self.user)
        self.usd2 = usd_wallet(self.user, name="Dollar 2")
        self.income_cat = Category.objects.create(name="Oylik")
        self.expense_cat = ExpenseCategory.objects.create(name="Ovqat")
        self.login_as(self.user)

    def post(self, kind, wallet, summa=100):
        cat = self.income_cat if kind == "incomes" else self.expense_cat
        res = self.api.post(f"{API}/{kind}/", {"wallet": wallet.id, "summa": summa, "category": cat.id}, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        model = Income if kind == "incomes" else Expense
        return model.objects.get(pk=res.json()["id"])

    def patch(self, kind, obj, **data):
        res = self.api.patch(f"{API}/{kind}/{obj.pk}/", data, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        obj.refresh_from_db()
        return obj

    def set_usd_rate(self, rate):
        ExchangeRate.objects.filter(currency="USD").update(rate=Decimal(rate))

    def test_rate_is_stored_on_create(self):
        for kind in ("incomes", "expenses"):
            with self.subTest(kind=kind):
                self.assertEqual(self.post(kind, self.usd).uzs_rate, Decimal("12000"))
                self.assertEqual(self.post(kind, self.uzs).uzs_rate, Decimal(1))

    def test_rate_is_not_exposed_or_writable_in_api(self):
        res = self.api.post(
            f"{API}/incomes/", {"wallet": self.usd.id, "summa": 5, "category": self.income_cat.id, "uzs_rate": "1"}, format="json"
        )
        self.assertEqual(res.status_code, 201)
        self.assertNotIn("uzs_rate", res.json())
        self.assertEqual(Income.objects.get(pk=res.json()["id"]).uzs_rate, Decimal("12000"))

    def test_rate_is_unchanged_by_other_edits(self):
        for kind in ("incomes", "expenses"):
            with self.subTest(kind=kind):
                self.set_usd_rate("12000")
                obj = self.post(kind, self.usd)
                self.set_usd_rate("13000")
                obj = self.patch(kind, obj, summa=250)
                self.assertEqual(obj.summa, 250)
                self.assertEqual(obj.uzs_rate, Decimal("12000"))
                obj = self.patch(kind, obj, description="izoh")
                self.assertEqual(obj.uzs_rate, Decimal("12000"))
                # Shu valyutadagi boshqa hamyonga ko'chirish ham kursni o'zgartirmaydi
                obj = self.patch(kind, obj, wallet=self.usd2.id)
                self.assertEqual(obj.wallet_id, self.usd2.id)
                self.assertEqual(obj.uzs_rate, Decimal("12000"))

    def test_rate_is_reset_when_moved_to_other_currency_wallet(self):
        for kind in ("incomes", "expenses"):
            with self.subTest(kind=kind):
                obj = self.post(kind, self.uzs)
                self.assertEqual(obj.uzs_rate, Decimal(1))
                self.set_usd_rate("12500")
                obj = self.patch(kind, obj, wallet=self.usd.id)
                self.assertEqual(obj.uzs_rate, Decimal("12500"))
                obj = self.patch(kind, obj, wallet=self.uzs.id)
                self.assertEqual(obj.uzs_rate, Decimal(1))

    def test_missing_rate_saves_null_and_does_not_block_operation(self):
        def only_uzs(code):
            if code == "UZS":
                return Decimal(1)
            raise CurrencyRateError("kurs yo'q")

        with mock.patch("mainapp.currency.get_rate_to_uzs", side_effect=only_uzs):
            income = self.post("incomes", self.usd, 100)
            expense = self.post("expenses", self.usd, 30)
            self.assertIsNone(income.uzs_rate)
            self.assertIsNone(expense.uzs_rate)
            # Kurs bo'lmasa ham balans o'zgargan
            self.usd.refresh_from_db()
            self.assertEqual(self.usd.summa, 1_000_000 + 100 - 30)
            # Boshqa valyutaga ko'chirishda kurs olinmasa so'mning eski kursi (1) qolib ketmaydi
            uzs_income = self.post("incomes", self.uzs)
            self.assertEqual(uzs_income.uzs_rate, Decimal(1))
            moved = self.patch("incomes", uzs_income, wallet=self.usd.id)
            self.assertIsNone(moved.uzs_rate)

    def test_missing_rate_without_stored_rate_saves_null(self):
        # Saqlangan kurs ham, internet ham yo'q (testlarda _fetch_cbu o'chirilgan) — haqiqiy yo'l
        ExchangeRate.objects.all().delete()
        with self.assertLogs("mainapp.currency", "WARNING"):  # kutilgan ogohlantirish test chiqishini to'ldirmasin
            income = self.post("incomes", self.usd)
        self.assertIsNone(income.uzs_rate)

    def test_explicit_rate_on_create_is_kept(self):
        income = Income.objects.create(user=self.user, wallet=self.usd, summa=10, uzs_rate=Decimal("11111.5"))
        self.assertEqual(income.uzs_rate, Decimal("11111.5"))

    def test_rate_is_looked_up_before_the_transaction(self):
        """Kurs olish tarmoqqa chiqishi mumkin — save() ning atomic blokidan oldin bajarilishi kerak"""
        base_depth = len(connection.savepoint_ids)
        seen = []

        def fake_rate(code):
            seen.append(len(connection.savepoint_ids))
            return Decimal("12000")

        with mock.patch("mainapp.currency.get_rate_to_uzs", side_effect=fake_rate):
            Income.objects.create(user=self.user, wallet=self.usd, summa=10)
            Expense.objects.create(user=self.user, wallet=self.usd, summa=10)
        self.assertEqual(seen, [base_depth, base_depth])


class StatsUseStoredRateTests(APITestCase):
    def setUp(self):
        super().setUp()
        ExchangeRate.objects.create(currency="USD", rate=Decimal("12000"))
        self.user = make_user("vali")
        self.uzs = uzs_wallet(self.user)
        self.usd = usd_wallet(self.user)
        self.salary = Category.objects.create(name="Oylik")
        self.food = ExpenseCategory.objects.create(name="Ovqat")
        self.login_as(self.user)

    def monthly(self):
        res = self.api.get(f"{API}/stats/monthly/")
        self.assertEqual(res.status_code, 200)
        return res.json()

    def summary(self):
        res = self.api.get(f"{API}/wallets/summary/")
        self.assertEqual(res.status_code, 200)
        return res.json()

    def set_today_rate(self, rate):
        ExchangeRate.objects.filter(currency="USD").update(rate=Decimal(rate))

    def test_monthly_total_does_not_change_when_rate_changes(self):
        Income.objects.create(user=self.user, wallet=self.uzs, category=self.salary, summa=1_000_000)
        Income.objects.create(user=self.user, wallet=self.usd, category=self.salary, summa=100)
        Expense.objects.create(user=self.user, wallet=self.usd, category=self.food, summa=30)
        before = self.monthly()
        self.assertEqual(before["total_income"], 2_200_000)
        self.assertEqual(before["total_expense"], 360_000)

        self.set_today_rate("15000")
        after = self.monthly()
        self.assertEqual(after["total_income"], 2_200_000)
        self.assertEqual(after["total_expense"], 360_000)
        self.assertEqual(after["category_incomes"], before["category_incomes"])
        self.assertEqual(sum(d["income"] for d in after["daily_trend"]), 2_200_000)
        # Asl valyutadagi summalar o'zgarishsiz
        self.assertEqual(after["category_incomes"][0]["parts"], [
            {"currency": "UZS", "total": 1_000_000}, {"currency": "USD", "total": 100},
        ])

        summary = self.summary()
        self.assertEqual(summary["total_income"], 2_200_000)
        self.assertEqual(summary["monthly_income"], 2_200_000)
        self.assertEqual(summary["monthly_expense"], 360_000)
        self.assertEqual(sum(d["expense"] for d in summary["weekly_expenses"]), 360_000)

    def test_rows_with_different_stored_rates_are_summed_each_at_own_rate(self):
        Income.objects.create(user=self.user, wallet=self.usd, category=self.salary, summa=100)  # 1 200 000
        self.set_today_rate("13000")
        Income.objects.create(user=self.user, wallet=self.usd, category=self.salary, summa=100)  # 1 300 000
        self.set_today_rate("99999")
        data = self.monthly()
        self.assertEqual(data["total_income"], 2_500_000)
        self.assertEqual(data["category_incomes"][0]["parts"], [{"currency": "USD", "total": 200}])

    def test_null_rate_rows_fall_back_to_todays_rate(self):
        with mock.patch("mainapp.currency.get_rate_to_uzs", side_effect=CurrencyRateError("kurs yo'q")):
            Income.objects.create(user=self.user, wallet=self.usd, category=self.salary, summa=100)
        self.assertIsNone(Income.objects.get().uzs_rate)
        self.assertEqual(self.monthly()["total_income"], 1_200_000)
        self.set_today_rate("15000")
        self.assertEqual(self.monthly()["total_income"], 1_500_000)

    def test_mixed_stored_and_null_rows(self):
        Income.objects.create(user=self.user, wallet=self.usd, category=self.salary, summa=100)  # saqlangan: 1 200 000
        Income.objects.create(user=self.user, wallet=self.usd, category=self.salary, summa=10)
        Income.objects.filter(summa=10).update(uzs_rate=None)
        self.set_today_rate("15000")
        # 100 * 12 000 (saqlangan) + 10 * 15 000 (bugungi)
        self.assertEqual(self.monthly()["total_income"], 1_350_000)

    def test_missing_rates_are_reported_only_for_null_rows(self):
        Income.objects.create(user=self.user, wallet=self.usd, category=self.salary, summa=100)
        ExchangeRate.objects.all().delete()
        data = self.monthly()
        # Kurs qatorning o'zida saqlangan — bugungi kurs yo'qligi jamga ta'sir qilmaydi
        self.assertEqual(data["total_income"], 1_200_000)
        self.assertEqual(data["missing_rates"], [])
        Income.objects.update(uzs_rate=None)
        with self.assertLogs("mainapp.currency", "WARNING"):  # bugungi kursni olishga urinish kutilgan holda yiqiladi
            data = self.monthly()
        self.assertEqual(data["total_income"], 0)
        self.assertEqual(data["missing_rates"], ["USD"])

    def test_large_sums_stay_exact(self):
        """SQLite float bilan emas: 15 xonadan oshgan jami ham aniq"""
        for i in range(3):  # hamyon balansi MAX_AMOUNT dan oshmasligi uchun har biri o'z hamyonida
            big_wallet = uzs_wallet(self.user, summa=0, name=f"Katta {i}")
            Income.objects.create(user=self.user, wallet=big_wallet, category=self.salary, summa=MAX_AMOUNT - 1)
        self.assertEqual(self.monthly()["total_income"], 3 * (MAX_AMOUNT - 1))
        Income.objects.all().delete()
        Income.objects.create(user=self.user, wallet=self.usd, category=self.salary, summa=123_456_789_012,
                              uzs_rate=Decimal("12345.67891234"))
        # 123456789012 * 12345.67891234 = 1524157868563849103.78... -> yaxlitlangan
        expected = int((Decimal(123_456_789_012) * Decimal("12345.67891234")).quantize(Decimal(1)))
        self.assertEqual(self.monthly()["total_income"], expected)


class FillUzsRateMigrationTests(TestCase):
    """0016 ma'lumot migratsiyasi: mavjud qatorlarga ExchangeRate jadvalidagi kurs bir marta yoziladi"""

    def run_fill(self):
        migration = importlib.import_module("mainapp.migrations.0016_fill_uzs_rate")
        migration.fill_uzs_rate(apps, None)

    def test_fills_existing_rows_per_currency(self):
        user = make_user("migr")
        ExchangeRate.objects.create(currency="USD", rate=Decimal("12012.3"))
        wallets = {
            "uzs": uzs_wallet(user),
            "usd": usd_wallet(user),
            "xyz": Wallet.objects.create(user=user, name="XYZ", summa=1000, currency="XYZ"),
        }
        made = {}
        for name, wallet in wallets.items():
            made[name] = (
                Income.objects.create(user=user, wallet=wallet, summa=10, uzs_rate=Decimal("7")),
                Expense.objects.create(user=user, wallet=wallet, summa=5, uzs_rate=Decimal("7")),
            )
            Income.objects.filter(pk=made[name][0].pk).update(uzs_rate=None)
            Expense.objects.filter(pk=made[name][1].pk).update(uzs_rate=None)
        # Allaqachon kursi bor qatorga tegilmaydi
        kept = Income.objects.create(user=user, wallet=wallets["usd"], summa=1, uzs_rate=Decimal("11000"))

        with mock.patch("mainapp.currency._fetch_cbu", side_effect=AssertionError("migratsiya tarmoqqa chiqmasligi kerak")):
            self.run_fill()

        def rate(obj):
            return type(obj).objects.get(pk=obj.pk).uzs_rate

        self.assertEqual([rate(o) for o in made["uzs"]], [Decimal(1), Decimal(1)])
        self.assertEqual([rate(o) for o in made["usd"]], [Decimal("12012.3"), Decimal("12012.3")])
        self.assertEqual([rate(o) for o in made["xyz"]], [None, None])
        self.assertEqual(rate(kept), Decimal("11000"))

    def test_does_not_overwrite_and_reverse_is_noop(self):
        user = make_user("migr2")
        ExchangeRate.objects.create(currency="USD", rate=Decimal("12000"))
        income = Income.objects.create(user=user, wallet=usd_wallet(user), summa=10)
        self.run_fill()
        ExchangeRate.objects.filter(currency="USD").update(rate=Decimal("14000"))
        self.run_fill()  # qayta bajarilsa ham mavjud kurs qayta yozilmaydi
        self.assertEqual(Income.objects.get(pk=income.pk).uzs_rate, Decimal("12000"))
        migration = importlib.import_module("mainapp.migrations.0016_fill_uzs_rate")
        reverse = migration.Migration.operations[0].reverse_code
        self.assertIsNone(reverse(apps, None))
