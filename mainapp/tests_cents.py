"""Miqdorlar tiyin bilan (2 xonali kasr) saqlanadi: kiritish, aniq qoldiq, chegaralar, hisobot va JSON ko'rinishi.
Tarmoq har doim mock: haqiqiy cbu.uz ga murojaat qilinmaydi."""
from decimal import Decimal
from unittest import mock

from django.test import SimpleTestCase

from .models import MAX_AMOUNT, MAX_AMOUNT_MESSAGE, Debt, Expense, ExpenseCategory, Income, Transfer, Wallet
from .money import MONEY_DECIMALS_MESSAGE, parse_amount
from .tests_balance import API, BalanceTestCase

RATES = {"USD": (Decimal("12000"), "08.10.2026")}


class CreateWithCentsTests(BalanceTestCase):
    def test_wallet_with_cents(self):
        res = self.post("wallets", {"name": "Karta", "summa": "12.34", "currency": "UZS"})
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(Wallet.objects.get(pk=res.json()["id"]).summa, Decimal("12.34"))

    def test_income_expense_with_cents(self):
        self.income(self.a, 12.34)
        self.assertEqual(self.balance(self.a), Decimal("12.34"))
        self.expense(self.a, "2.34")
        self.assertEqual(self.balance(self.a), Decimal("10.00"))
        self.assertEqual(Income.objects.get().summa, Decimal("12.34"))
        self.assertEqual(Expense.objects.get().summa, Decimal("2.34"))

    def test_transfer_same_currency_with_cents(self):
        self.income(self.a, "100.55")
        self.transfer(self.a, self.b, "40.25")
        self.assertEqual((self.balance(self.a), self.balance(self.b)), (Decimal("60.30"), Decimal("40.25")))
        self.assertEqual(Transfer.objects.get().to_summa, Decimal("40.25"))

    def test_debt_and_repay_with_cents(self):
        self.a.summa = 1000
        self.a.save()
        data = self.debt(self.a, "100.50")
        self.assertEqual(self.balance(self.a), Decimal("899.50"))
        res = self.post(f"debts/{data['id']}/repay", {"amount": 0.5, "wallet": self.a.id})
        self.assertEqual(res.status_code, 200, res.content)
        debt = Debt.objects.get()
        self.assertEqual((debt.paid_summa, debt.remaining_summa), (Decimal("0.50"), Decimal("100.00")))
        self.assertEqual(self.balance(self.a), Decimal("900.00"))
        self.assertEqual(res.json()["debt"]["remaining_summa"], 100.0)
        res = self.post(f"debts/{data['id']}/repay", {"amount": "100", "wallet": self.a.id})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertTrue(Debt.objects.get().is_settled)
        self.assertEqual(self.balance(self.a), Decimal("1000.00"))

    def test_repay_more_than_remaining_with_cents(self):
        self.a.summa = 100
        self.a.save()
        data = self.debt(self.a, "10.10")
        res = self.post(f"debts/{data['id']}/repay", {"amount": "10.11", "wallet": self.a.id})
        self.assertEqual(res.status_code, 400, res.content)

    def test_patch_accepts_cents_too(self):
        inc = self.income(self.a, 100)
        res = self.patch("incomes", inc["id"], {"summa": "100.75"})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(self.balance(self.a), Decimal("100.75"))
        exp = self.expense(self.a, 10)
        res = self.patch("expenses", exp["id"], {"summa": "10.25"})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(self.balance(self.a), Decimal("90.50"))
        res = self.patch("expenses", exp["id"], {"summa": "10.255"})
        self.assertEqual(res.status_code, 400, res.content)
        debt = self.debt(self.a, "5.5")
        res = self.patch("debts", debt["id"], {"summa": "5.55"})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(self.balance(self.a), Decimal("84.95"))
        tr = self.transfer(self.a, self.b, "1.10")
        res = self.patch("transfers", tr["id"], {"summa": "1.15"})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual((self.balance(self.a), self.balance(self.b)), (Decimal("83.80"), Decimal("1.15")))
        # Hamyon summasi tahrirda to'g'ridan-to'g'ri o'zgartiriladi (tiyin bilan); 3 xonali kasr rad etiladi
        res = self.patch("wallets", self.a.id, {"name": "Yangi", "summa": "83.81"})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(self.balance(self.a), Decimal("83.81"))
        res = self.patch("wallets", self.a.id, {"summa": "83.815"})
        self.assertEqual(res.status_code, 400, res.content)


class ExactBalanceTests(BalanceTestCase):
    def test_thousand_times_ten_cents_is_exactly_100(self):
        for _ in range(1000):
            self.a.add_money(Decimal("0.10"))
        self.assertEqual(self.balance(self.a), Decimal("100.00"))
        for _ in range(1000):
            self.a.withdraw_money(Decimal("0.10"))
        self.assertEqual(self.balance(self.a), Decimal("0.00"))

    def test_many_api_operations_stay_exact(self):
        for _ in range(50):
            self.income(self.a, "0.10")
            self.income(self.a, "0.20")
        self.assertEqual(self.balance(self.a), Decimal("15.00"))
        category = ExpenseCategory.objects.create(name="T").id
        for _ in range(50):
            res = self.post("expenses", {"wallet": self.a.id, "summa": "0.30", "category": category})
            self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(self.balance(self.a), Decimal("0.00"))
        # Float qoldig'i bo'lmaganligi uchun 0.01 ham yechib bo'lmaydi
        with self.assertRaises(ValueError):
            self.a.withdraw_money(Decimal("0.01"))

    def test_money_conserved_through_transfers(self):
        self.income(self.a, "0.07")
        for _ in range(7):
            self.transfer(self.a, self.b, "0.01")
        self.assertEqual((self.balance(self.a), self.balance(self.b)), (Decimal("0.00"), Decimal("0.07")))


class ValidationTests(BalanceTestCase):
    def test_more_than_two_decimals_rejected(self):
        for value in ("1.234", 1.234, "0.001", 100.005):
            with self.subTest(value=value):
                res = self.post("incomes", {"wallet": self.a.id, "summa": value})
                self.assertEqual(res.status_code, 400, res.content)
                self.assertIn(MONEY_DECIMALS_MESSAGE, res.content.decode())
        self.assertEqual(Income.objects.count(), 0)

    def test_trailing_zeros_are_fine(self):
        self.assertEqual(self.post("incomes", {"wallet": self.a.id, "summa": "5.500"}).status_code, 201)

    def test_one_cent_accepted_zero_rejected(self):
        self.assertEqual(self.post("incomes", {"wallet": self.a.id, "summa": "0.01"}).status_code, 201)
        for path, extra in (("incomes", {}), ("debts", {"person_name": "R", "debt_type": "take"})):
            res = self.post(path, {"wallet": self.a.id, "summa": 0, **extra})
            self.assertEqual(res.status_code, 400, res.content)
        res = self.post("incomes", {"wallet": self.a.id, "summa": "0.00"})
        self.assertEqual(res.status_code, 400, res.content)
        self.assertEqual(self.balance(self.a), Decimal("0.01"))

    def test_wallet_initial_zero_ok_negative_rejected(self):
        self.assertEqual(self.post("wallets", {"name": "Z", "summa": 0, "currency": "UZS"}).status_code, 201)
        self.assertEqual(self.post("wallets", {"name": "Y", "summa": "-0.01", "currency": "UZS"}).status_code, 400)

    def test_garbage_rejected(self):
        for value in ("abc", "NaN", "Infinity", True, [], {}, ""):
            with self.subTest(value=value):
                res = self.post("incomes", {"wallet": self.a.id, "summa": value})
                self.assertEqual(res.status_code, 400, res.content)

    def test_max_amount_boundary(self):
        self.assertEqual(MAX_AMOUNT, 10 ** 12)
        res = self.post("incomes", {"wallet": self.a.id, "summa": MAX_AMOUNT})
        self.assertEqual(res.status_code, 201, res.content)
        for value in (MAX_AMOUNT + 1, "1000000000000.01", 10 ** 15, 10 ** 20):
            with self.subTest(value=value):
                res = self.post("incomes", {"wallet": self.b.id, "summa": value})
                self.assertEqual(res.status_code, 400, res.content)
                self.assertIn(MAX_AMOUNT_MESSAGE, res.content.decode())
        self.assertEqual(self.balance(self.b), 0)

    def test_wallet_balance_cannot_pass_max(self):
        self.a.summa = MAX_AMOUNT
        self.a.save()
        res = self.post("incomes", {"wallet": self.a.id, "summa": "0.01"})
        self.assertEqual(res.status_code, 400, res.content)
        self.assertEqual(self.balance(self.a), MAX_AMOUNT)


class RepayInputTests(BalanceTestCase):
    def setUp(self):
        super().setUp()
        self.a.summa = 1000
        self.a.save()
        self.url = f"debts/{self.debt(self.a, 500)['id']}/repay"

    def test_repay_half(self):
        res = self.post(self.url, {"amount": 0.5, "wallet": self.a.id})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(Debt.objects.get().paid_summa, Decimal("0.50"))

    def test_repay_rejects(self):
        for value in (0, "0.00", "0.001", True, "NaN", "Infinity", "1e2", None, [1], MAX_AMOUNT + 1):
            with self.subTest(value=value):
                res = self.post(self.url, {"amount": value, "wallet": self.a.id})
                self.assertEqual(res.status_code, 400, res.content)
        self.assertEqual(Debt.objects.get().paid_summa, 0)


class ParseAmountTests(SimpleTestCase):
    def test_accepts(self):
        for value, expected in (("12.5", "12.5"), (12.5, "12.5"), ("100", "100"), (3, "3"), (" 7.10 ", "7.10"),
                                (0.1, "0.1"), ("1.230", "1.230")):
            self.assertEqual(parse_amount(value), Decimal(expected), value)

    def test_rejects(self):
        for value in (True, None, "", "1e5", "NaN", "inf", float("nan"), float("inf"), "1,5", "١٢",
                      "1.234", 1.2345, "1.", ".5", [1]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_amount(value)


@mock.patch("mainapp.currency._fetch_cbu", return_value=RATES)
class CurrencyCentsTests(BalanceTestCase):
    def setUp(self):
        super().setUp()
        self.usd = self.wallet("USD", 0, "USD")

    def test_transfer_to_summa_rounds_half_up_to_cents(self, _fetch):
        self.a.summa = 1_000_000
        self.a.save()
        # 12 345 / 12 000 = 1.02875 -> 1.03
        res = self.post("transfers", {"from_wallet": self.a.id, "to_wallet": self.usd.id, "summa": 12345})
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()["to_summa"], 1.03)
        self.assertEqual(self.balance(self.usd), Decimal("1.03"))
        # 6 / 12 000 = 0.0005 -> 0.00: "juda kichik" (400)
        res = self.post("transfers", {"from_wallet": self.a.id, "to_wallet": self.usd.id, "summa": 6})
        self.assertEqual(res.status_code, 400, res.content)
        # 60 / 12 000 = 0.005 aniq yarim -> yuqoriga: 0.01
        res = self.post("transfers", {"from_wallet": self.a.id, "to_wallet": self.usd.id, "summa": 60})
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()["to_summa"], 0.01)

    def test_convert_endpoint_accepts_decimals(self, _fetch):
        url = f"{API}/rates/convert/"
        res = self.api.get(url, {"from": "UZS", "to": "USD", "amount": "12.5"})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual((res.json()["amount"], res.json()["result"]), (12.5, 0.0))
        res = self.api.get(url, {"from": "USD", "to": "UZS", "amount": "12.5"})
        self.assertEqual(res.json()["result"], 150000.0)
        res = self.api.get(url, {"from": "UZS", "to": "USD", "amount": "125000"})
        self.assertEqual(res.json()["result"], 10.42)
        for bad in ("1.234", "abc", "0", "1e3", "-5"):
            res = self.api.get(url, {"from": "USD", "to": "UZS", "amount": bad})
            self.assertEqual(res.status_code, 400, (bad, res.content))

    def test_repay_with_fraction(self, _fetch):
        self.usd.summa = 100
        self.usd.save()
        debt = self.post("debts", {"person_name": "R", "debt_type": "take", "summa": 100, "wallet": self.usd.id}).json()
        res = self.post(f"debts/{debt['id']}/repay", {"amount": "1.5", "wallet": self.usd.id})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["wallet_amount"], 1.5)

    def test_stats_are_two_decimals(self, _fetch):
        self.income(self.a, "100.10")
        self.income(self.a, "200.20")
        self.income(self.usd, "1.01")  # 12 120.00 UZS
        cat = ExpenseCategory.objects.create(name="T").id
        self.post("expenses", {"wallet": self.a.id, "summa": "33.33", "category": cat})
        self.post("expenses", {"wallet": self.a.id, "summa": "0.07", "category": cat})
        res = self.api.get(f"{API}/wallets/summary/")
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertEqual(body["total_income"], 12420.30)
        self.assertEqual(body["total_expense"], 33.40)
        self.assertEqual(body["net_savings"], 12386.90)
        uzs = next(b for b in body["balances_by_currency"] if b["currency"] == "UZS")
        self.assertEqual(uzs["total"], 266.90)
        self.assertNotIn("0000000", res.content.decode())  # float qoldig'i (0.30000000000000004) yo'q

        res = self.api.get(f"{API}/stats/monthly/")
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertEqual(body["total_expense"], 33.40)
        self.assertEqual(body["category_expenses"][0]["total"], 33.40)
        self.assertEqual(body["category_expenses"][0]["parts"], [{"currency": "UZS", "total": 33.4}])
        self.assertNotIn("0000000", res.content.decode())


class JsonShapeTests(BalanceTestCase):
    def test_amounts_are_json_numbers_not_strings(self):
        res = self.post("incomes", {"wallet": self.a.id, "summa": "12.50"})
        self.assertIsInstance(res.json()["summa"], (int, float))
        self.assertEqual(res.json()["summa"], 12.5)
        self.assertIn('"summa":12.5', res.content.decode().replace(" ", ""))
        wallet = self.api.get(f"{API}/wallets/{self.a.id}/").json()
        self.assertIsInstance(wallet["summa"], (int, float))
        self.assertEqual(wallet["summa"], 12.5)
        listing = self.api.get(f"{API}/incomes/").json()
        rows = listing["results"] if isinstance(listing, dict) else listing
        self.assertIsInstance(rows[0]["summa"], (int, float))
