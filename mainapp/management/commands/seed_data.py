from django.core.management.base import BaseCommand
from mainapp.models import User, Category, ExpenseCategory, Wallet, Income, Expense


class Command(BaseCommand):
    help = "Boshlang'ich kategoriyalar va test foydalanuvchini yaratish"

    def handle(self, *args, **options):
        # 1. Admin foydalanuvchi
        admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@example.com",
                "first_name": "Admin",
                "last_name": "Kalkulator",
                "is_staff": True,
                "is_superuser": True,
            }
        )
        if created:
            admin_user.set_password("admin123")
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("Superuser 'admin' yaratildi (parol: admin123)"))
        else:
            self.stdout.write("Superuser 'admin' allaqachon mavjud.")

        # 2. Daromad kategoriyalari (Income Category)
        income_cats = [
            ("Oylik maosh", "salary", "Har oylik doimiy maosh"),
            ("Freelance / Qo'shimcha ish", "laptop", "Loyiha va qo'shimcha daromadlar"),
            ("Sovg'a / Yordam", "gift", "Oila a'zolari yoki do'stlardan"),
            ("Investitsiya / Dividendlari", "trending-up", "Investitsiyalar va depozit daromadlari"),
            ("Boshqa daromadlar", "plus-circle", "Boshqa manbalardan tushumlar"),
        ]
        for name, icon, desc in income_cats:
            Category.objects.get_or_create(name=name, defaults={"icon": icon, "description": desc})

        # 3. Harajat kategoriyalari (ExpenseCategory)
        expense_cats = [
            ("Oziq-ovqat va bozor", "shopping-cart", "Supermarket, bozor, yegulik"),
            ("Transport va yo'l kira", "truck", "Taksi, metro, benzin, avtobus"),
            ("Uy-joy va kommunal", "home", "Ijara, gaz, svet, suv, internet"),
            ("Kiyim-kechak", "tag", "Kiyim, poyabzal, aksessuarlar"),
            ("Ko'ngilochar va dam olish", "coffee", "Kafe, restoran, kinoteatr"),
            ("Salomatlik va dorixona", "activity", "Shifokor, dorilar, tibbiy xizmat"),
            ("Ta'lim va kitoblar", "book", "Kurslar, repetitor, kitob"),
            ("Kutilmagan harajatlar", "alert-circle", "Favqulodda va kutilmagan harajatlar"),
        ]
        for name, icon, desc in expense_cats:
            ExpenseCategory.objects.get_or_create(name=name, defaults={"icon": icon, "description": desc})

        # 4. Standart hamyonlar
        wallet1, w1_created = Wallet.objects.get_or_create(
            user=admin_user,
            name="Naqd pul",
            defaults={"summa": 0, "currency": "UZS"}
        )
        wallet2, w2_created = Wallet.objects.get_or_create(
            user=admin_user,
            name="Plastik karta (Uzcard/Humo)",
            defaults={"summa": 0, "currency": "UZS"}
        )

        self.stdout.write(self.style.SUCCESS("Boshlang'ich kategoriyalar va hamyonlar muvaffaqiyatli yuklandi!"))
