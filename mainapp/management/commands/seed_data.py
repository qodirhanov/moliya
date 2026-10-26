from django.core.management.base import BaseCommand
from mainapp.models import Category, ExpenseCategory


class Command(BaseCommand):
    help = "Boshlang'ich (umumiy) daromad va harajat toifalarini yaratish"

    def handle(self, *args, **options):
        # Admin akkaunt bu yerda yaratilmaydi: oldin "admin / admin123" yaratilardi va serverda
        # ishga tushirilsa, admin panel hammaga ochiq bo'lib qolardi. Admin uchun: python manage.py createsuperuser

        # 1. Daromad kategoriyalari (Income Category)
        income_cats = [
            ("Oylik maosh", "salary", "Har oylik doimiy maosh"),
            ("Freelance / Qo'shimcha ish", "laptop", "Loyiha va qo'shimcha daromadlar"),
            ("Sovg'a / Yordam", "gift", "Oila a'zolari yoki do'stlardan"),
            ("Investitsiya / Dividendlari", "trending-up", "Investitsiyalar va depozit daromadlari"),
            ("Boshqa daromadlar", "plus-circle", "Boshqa manbalardan tushumlar"),
        ]
        for name, icon, desc in income_cats:
            Category.objects.get_or_create(name=name, user=None, defaults={"icon": icon, "description": desc})

        # 2. Harajat kategoriyalari (ExpenseCategory)
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
            ExpenseCategory.objects.get_or_create(name=name, user=None, defaults={"icon": icon, "description": desc})

        self.stdout.write(self.style.SUCCESS("Boshlang'ich toifalar muvaffaqiyatli yuklandi!"))
        self.stdout.write("Admin akkaunt kerak bo'lsa: python manage.py createsuperuser")
