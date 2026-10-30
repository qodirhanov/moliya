"""Ikki marta (eskirgan nusxa orqali) o'chirish pulni ikki marta qaytarmasligi kerak.
Parallel DELETE ni ikki xil nusxa bilan taqlid qilamiz: ikkalasi ham status=True ni ko'rgan."""
from decimal import Decimal

from .models import Debt, Expense, Income, Transfer
from .tests_balance import BalanceTestCase


class DoubleDeleteTests(BalanceTestCase):
    def two_copies(self, model, pk):
        first, second = model.objects.get(pk=pk), model.objects.get(pk=pk)
        self.assertIsNot(first, second)
        return first, second

    def test_income_double_delete(self):
        self.a.add_money(1000)
        pk = self.income(self.a, 100)["id"]  # 1100
        first, second = self.two_copies(Income, pk)
        first.delete()
        second.delete()
        self.assertEqual(self.balance(self.a), Decimal("1000"))
        self.assertFalse(Income.objects.get(pk=pk).status)

    def test_expense_double_delete(self):
        self.a.add_money(1000)
        pk = self.expense(self.a, 100)["id"]  # 900
        first, second = self.two_copies(Expense, pk)
        first.delete()
        second.delete()
        self.assertEqual(self.balance(self.a), Decimal("1000"))

    def test_transfer_double_delete(self):
        self.a.add_money(1000)
        pk = self.transfer(self.a, self.b, 100)["id"]
        first, second = self.two_copies(Transfer, pk)
        first.delete()
        second.delete()
        self.assertEqual(self.balance(self.a), Decimal("1000"))
        self.assertEqual(self.balance(self.b), Decimal("0"))

    def test_debt_give_double_delete(self):
        self.a.add_money(1000)
        pk = self.debt(self.a, 100, "give")["id"]  # 900
        first, second = self.two_copies(Debt, pk)
        first.delete()
        second.delete()
        self.assertEqual(self.balance(self.a), Decimal("1000"))

    def test_debt_take_double_delete(self):
        self.a.add_money(1000)
        pk = self.debt(self.a, 100, "take")["id"]  # 1100
        first, second = self.two_copies(Debt, pk)
        first.delete()
        second.delete()
        self.assertEqual(self.balance(self.a), Decimal("1000"))

    def test_stale_debt_after_repay_uses_fresh_remaining(self):
        self.a.add_money(1000)
        pk = self.debt(self.a, 100, "give")["id"]  # 900
        stale = Debt.objects.get(pk=pk)
        res = self.post(f"debts/{pk}/repay", {"amount": 40, "wallet": self.a.id})  # 940
        self.assertEqual(res.status_code, 200, res.content)
        stale.delete()  # qoldiq 60 qaytadi, eskirgan 100 emas
        self.assertEqual(self.balance(self.a), Decimal("1000") - Decimal("100") + Decimal("40") + Decimal("60"))

    def test_stale_debt_after_repay_through_fresh_instance(self):
        self.a.add_money(1000)
        pk = self.debt(self.a, 100, "take")["id"]  # 1100
        stale = Debt.objects.get(pk=pk)
        fresh = Debt.objects.get(pk=pk)
        fresh.paid_summa = Decimal("30")
        fresh.save()
        stale.delete()  # qoldiq 70 yechiladi
        self.assertEqual(self.balance(self.a), Decimal("1030"))

    def test_single_delete_still_works(self):
        self.a.add_money(1000)
        pk = self.expense(self.a, 100)["id"]
        obj = Expense.objects.get(pk=pk)
        before = obj.updated_at
        self.assertEqual(obj.delete(), (1, {"mainapp.Expense": 1}))
        self.assertFalse(obj.status)
        self.assertEqual(self.balance(self.a), Decimal("1000"))
        self.assertGreaterEqual(Expense.objects.get(pk=pk).updated_at, before)
