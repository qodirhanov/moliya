from datetime import timedelta
from decimal import Decimal as D

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from mainapp.models import (
    Category, Debt, Expense, ExpenseCategory, Income, Member, RecurringPayment, SavingsGoal, Transfer, User, Wallet,
)


class Command(BaseCommand):
    help = ("Berilgan akkauntga namunaviy ma'lumotlar qo'shadi (hamyon, kirim, chiqim, o'tkazma, qarz, a'zo, doimiy to'lov, maqsad). "
            "Faqat ko'rgazma uchun. Akkauntda allaqachon hamyon bo'lsa, --force bermaguncha hech narsa qilmaydi")

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--force", action="store_true", help="Akkauntda ma'lumot bor bo'lsa ham qo'shadi")

    def handle(self, *args, username, force, **options):
        try:
            u = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"{username!r} akkaunti topilmadi")
        if Wallet.objects.filter(user=u).exists() and not force:
            raise CommandError("Akkauntda allaqachon hamyonlar bor — takror qo'shilmadi (kerak bo'lsa --force)")
        now = timezone.now()
        today = timezone.localdate()
        with transaction.atomic():
            self.fill(u, now, today)
        self.stdout.write(self.style.SUCCESS(f"{username}: namunaviy ma'lumotlar qo'shildi"))

    def fill(self, u, now, today):
        naqd = Wallet.objects.create(user=u, name="Naqd pul", summa=D("500000"), currency="UZS")
        karta = Wallet.objects.create(user=u, name="Uzcard karta", summa=D("3000000"), currency="UZS")
        bank = Wallet.objects.create(user=u, name="Jamg'arma (Humo)", summa=D("8000000"), currency="UZS")
        usd = Wallet.objects.create(user=u, name="Dollar", summa=D("350"), currency="USD")

        maosh = Category.objects.create(user=u, name="Oylik maosh")
        frl = Category.objects.create(user=u, name="Qo'shimcha ish")
        sovga = Category.objects.create(user=u, name="Sovg'a")
        oziq = ExpenseCategory.objects.create(user=u, name="Oziq-ovqat")
        trans = ExpenseCategory.objects.create(user=u, name="Transport")
        kommunal = ExpenseCategory.objects.create(user=u, name="Kommunal to'lovlar")
        kiyim = ExpenseCategory.objects.create(user=u, name="Kiyim-kechak")
        dori = ExpenseCategory.objects.create(user=u, name="Salomatlik")
        dam = ExpenseCategory.objects.create(user=u, name="Dam olish")

        ona = Member.objects.create(user=u, name="Onam", kind="person")
        uka = Member.objects.create(user=u, name="Abdulaziz ukam", kind="person")
        oila = Member.objects.create(user=u, name="Butun oila", kind="family")

        for m in range(3):
            d = now - timedelta(days=30 * m + 2)
            Income.objects.create(user=u, wallet=karta, category=maosh, summa=D("6500000"), description="Oylik maosh", date=d)
        Income.objects.create(user=u, wallet=karta, category=frl, summa=D("1200000"), description="Sayt buyurtmasi", date=now - timedelta(days=12))
        Income.objects.create(user=u, wallet=naqd, category=sovga, summa=D("300000"), description="Tug'ilgan kun sovg'asi", date=now - timedelta(days=20))

        rows = [
            (naqd, oziq, oila, "85000", "Bozor", 1), (karta, oziq, oila, "240000", "Supermarket", 3),
            (naqd, trans, None, "12000", "Metro", 1), (karta, trans, None, "150000", "Benzin", 6),
            (karta, kommunal, oila, "420000", "Elektr va gaz", 8), (karta, kommunal, oila, "95000", "Internet", 9),
            (karta, kiyim, uka, "380000", "Ukamga kurtka", 14), (naqd, dori, ona, "110000", "Onamga dori", 5),
            (karta, dam, None, "180000", "Kafe", 7), (naqd, oziq, oila, "60000", "Non va sut", 2),
            (karta, trans, None, "45000", "Taksi", 4), (karta, dam, oila, "260000", "Kinoteatr va ovqat", 18),
            (naqd, oziq, oila, "130000", "Bozorlik", 10), (karta, dori, None, "75000", "Vitaminlar", 16),
            (karta, oziq, oila, "310000", "Haftalik xarid", 22),
        ]
        for w, c, mem, s, desc, ago in rows:
            Expense.objects.create(user=u, wallet=w, category=c, member=mem, summa=D(s), description=desc, date=now - timedelta(days=ago))

        Transfer.objects.create(user=u, from_wallet=karta, to_wallet=naqd, summa=D("400000"), to_summa=D("400000"), rate=1,
                                description="Naqd pulga yechildi", date=now - timedelta(days=11))
        Transfer.objects.create(user=u, from_wallet=karta, to_wallet=bank, summa=D("1000000"), to_summa=D("1000000"), rate=1,
                                description="Jamg'armaga", date=now - timedelta(days=13))

        Debt.objects.create(user=u, person_name="Jasur (do'st)", debt_type="give", summa=D("700000"), currency="UZS",
                            wallet=naqd, due_date=today + timedelta(days=20))
        Debt.objects.create(user=u, person_name="Akam", debt_type="take", summa=D("1500000"), currency="UZS",
                            wallet=karta, due_date=today + timedelta(days=45))

        for name, kind, w, s, fr, cat, mem, nxt in [
            ("Internet", "expense", karta, "95000", "monthly", ("e", kommunal), None, 9),
            ("Elektr va gaz", "expense", karta, "420000", "monthly", ("e", kommunal), oila, 8),
            ("Sport zali", "expense", karta, "250000", "monthly", ("e", dam), None, 15),
            ("Maosh", "income", karta, "6500000", "monthly", ("i", maosh), None, 25),
        ]:
            RecurringPayment.objects.create(
                user=u, kind=kind, name=name, wallet=w, summa=D(s), frequency=fr,
                expense_category=cat[1] if cat[0] == "e" else None, income_category=cat[1] if cat[0] == "i" else None,
                member=mem, start_date=today + timedelta(days=nxt), next_date=today + timedelta(days=nxt), remind_days=2)

        SavingsGoal.objects.create(user=u, name="Ta'til (Turkiya)", target=D("15000000"), wallet=bank, deadline=today + timedelta(days=200))
