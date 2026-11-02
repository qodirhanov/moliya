"""Modellar/serializer/money.py ko'rigidan topilgan xatolar uchun regressiya testlari."""
from decimal import Decimal

from .models import Expense, Income, Transfer
from .money import quantize_money
from .tests_balance import BalanceTestCase


class StaleDeleteTests(BalanceTestCase):
    """O'chirish eskirgan nusxa orqali kelsa (view get_object() dan keyin boshqa so'rov tahrirlagan),
    hamyonga tahrirdan OLDINGI summa/hamyon emas, bazadagi joriy qiymat qaytarilishi kerak"""

    def test_expense_delete_after_summa_edit(self):
        self.a.add_money(1000)
        pk = self.expense(self.a, 100)["id"]  # 900
        stale = Expense.objects.get(pk=pk)
        self.assertEqual(self.patch("expenses", pk, {"summa": 300}).status_code, 200)  # 700
        stale.delete()
        self.assertEqual(self.balance(self.a), Decimal("1000"))

    def test_expense_delete_after_wallet_move(self):
        self.a.add_money(1000)
        self.b.add_money(500)
        pk = self.expense(self.a, 100)["id"]
        stale = Expense.objects.get(pk=pk)
        self.assertEqual(self.patch("expenses", pk, {"wallet": self.b.id}).status_code, 200)
        stale.delete()
        self.assertEqual(self.balance(self.a), Decimal("1000"))
        self.assertEqual(self.balance(self.b), Decimal("500"))

    def test_income_delete_after_summa_edit(self):
        self.a.add_money(1000)
        pk = self.income(self.a, 100)["id"]  # 1100
        stale = Income.objects.get(pk=pk)
        self.assertEqual(self.patch("incomes", pk, {"summa": 300}).status_code, 200)  # 1300
        stale.delete()
        self.assertEqual(self.balance(self.a), Decimal("1000"))

    def test_transfer_delete_after_summa_edit(self):
        self.a.add_money(1000)
        pk = self.transfer(self.a, self.b, 100)["id"]
        stale = Transfer.objects.get(pk=pk)
        self.assertEqual(self.patch("transfers", pk, {"summa": 300}).status_code, 200)
        stale.delete()
        self.assertEqual(self.balance(self.a), Decimal("1000"))
        self.assertEqual(self.balance(self.b), Decimal("0"))


class QuantizeMoneyTests(BalanceTestCase):
    def test_float_uses_short_repr(self):
        self.assertEqual(quantize_money(1.005), Decimal("1.01"))
        self.assertEqual(quantize_money(0.285), Decimal("0.29"))
        self.assertEqual(quantize_money(Decimal("1.005")), Decimal("1.01"))
        self.assertEqual(quantize_money(5), Decimal("5.00"))
