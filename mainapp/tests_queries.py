"""plans.md №11 testlari: ro'yxat endpointlari SQL so'rovlari soni qatorlar soniga bog'liq emas (N+1 yo'q)
va ?limit= yuqori chegaraga ega (MaxLimitPagination)."""
from datetime import timedelta
from decimal import Decimal

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from .models import Category, Debt, ExchangeRate, Expense, ExpenseCategory, Income, Member, Transfer, User, Wallet
from .pagination import MaxLimitPagination
from .tests import API, APITestCase, make_user, rows

SMALL, LARGE = 2, 20
# Ro'yxat javobi 10 tadan ortiq qatorni bitta sahifada qaytarishi uchun
BIG_PAGE = "?limit=200"


def seed_operations(user, n):
    """Foydalanuvchiga n tadan hamyon, toifa, a'zo, daromad, harajat, o'tkazma va qarz yaratadi. Har qator o'z
    hamyoni / toifasi / a'zosiga ega — bog'liq obyekt keshdan emas, har safar alohida so'rov bilan olinsa ko'rinib qoladi.
    Valyutalar ikkita (UZS, USD), qatorlar soni bilan o'zgarmaydi: kurs so'rovlari ham doimiy bo'lishi kerak"""
    now = timezone.now()
    for i in range(n):
        currency = "USD" if i % 2 else "UZS"
        wallet = Wallet.objects.create(user=user, name=f"Hamyon {i}", summa=10_000_000, currency=currency)
        other = Wallet.objects.create(user=user, name=f"Boshqa {i}", summa=0, currency=currency)
        income_cat = Category.objects.create(user=user, name=f"Daromad turi {i}")
        expense_cat = ExpenseCategory.objects.create(user=user, name=f"Harajat turi {i}")
        member = Member.objects.create(user=user, name=f"A'zo {i}")
        Income.objects.create(user=user, wallet=wallet, category=income_cat, summa=1000 + i, date=now - timedelta(minutes=i))
        Expense.objects.create(
            user=user, wallet=wallet, category=expense_cat, member=member, summa=500 + i, date=now - timedelta(minutes=i)
        )
        Transfer.objects.create(
            user=user, from_wallet=wallet, to_wallet=other, summa=100 + i, to_summa=100 + i, date=now - timedelta(minutes=i)
        )
        Debt.objects.create(user=user, wallet=wallet, person_name=f"Shaxs {i}", debt_type="give" if i % 2 else "take",
                            summa=300 + i, currency=currency)


def app_queries(ctx):
    """Faqat mainapp jadvallariga tegishli so'rovlar (DRF so'rovlar cheklovi hisoblagichi django_cache jadvalida
    yashaydi va SAVEPOINT bilan o'raladi — ular ro'yxat hajmiga bog'liq emas)"""
    return [q["sql"] for q in ctx if '"mainapp_' in q["sql"]]


class QueryCountTests(APITestCase):
    """Har bir ro'yxat uchun: 2 qatorli va 20 qatorli javobdagi SQL so'rovlar soni bir xil bo'lishi kerak"""

    def setUp(self):
        super().setUp()
        ExchangeRate.objects.create(currency="USD", rate=Decimal("12000"))
        self.small_user = make_user("kichik")
        self.large_user = make_user("katta")
        seed_operations(self.small_user, SMALL)
        seed_operations(self.large_user, LARGE)

    def count_queries(self, user, url):
        self.login_as(user)
        with CaptureQueriesContext(connection) as ctx:
            response = self.api.get(f"{API}/{url}")
        self.assertEqual(response.status_code, 200, response.content)
        return len(ctx), response

    def assert_constant(self, url, expected_rows=None):
        small_count, small_resp = self.count_queries(self.small_user, url)
        large_count, large_resp = self.count_queries(self.large_user, url)
        self.assertEqual(
            small_count, large_count,
            f"/{url}: {SMALL} qatorda {small_count}, {LARGE} qatorda {large_count} ta SQL so'rov — N+1",
        )
        if expected_rows is not None:
            self.assertEqual(len(rows(small_resp)), expected_rows[0])
            self.assertEqual(len(rows(large_resp)), expected_rows[1])
        return large_count

    def test_wallets_list_constant(self):
        # Har foydalanuvchida SMALL * 2 va LARGE * 2 ta hamyon (asosiy + "boshqa")
        self.assert_constant("wallets/", (SMALL * 2, LARGE * 2))

    def test_incomes_list_constant(self):
        self.assert_constant(f"incomes/{BIG_PAGE}", (SMALL, LARGE))

    def test_expenses_list_constant(self):
        self.assert_constant(f"expenses/{BIG_PAGE}", (SMALL, LARGE))

    def test_transfers_list_constant(self):
        self.assert_constant(f"transfers/{BIG_PAGE}", (SMALL, LARGE))

    def test_debts_list_constant(self):
        self.assert_constant(f"debts/{BIG_PAGE}", (SMALL, LARGE))

    def test_members_list_constant(self):
        self.assert_constant("members/", (SMALL, LARGE))

    def test_categories_list_constant(self):
        # Umumiy toifalar ham bor (migratsiyadan), shuning uchun faqat soni emas, o'sishi tekshiriladi
        self.assert_constant("categories/")
        self.assert_constant("expense-categories/")

    def test_categories_with_hidden_and_search_constant(self):
        for user, n in ((self.small_user, SMALL), (self.large_user, LARGE)):
            user.hidden_income_categories.add(*Category.objects.filter(user__isnull=True)[:n])
            user.hidden_expense_categories.add(*ExpenseCategory.objects.filter(user__isnull=True)[:n])
        self.assert_constant("categories/?include_hidden=1")
        self.assert_constant("expense-categories/?include_hidden=1")

    def test_filtered_and_searched_lists_constant(self):
        # Qidiruv va filtr (category__name, wallet__name bo'yicha JOIN) qo'shimcha so'rov qo'shmasligi kerak
        self.assert_constant(f"incomes/{BIG_PAGE}&search=Daromad")
        self.assert_constant(f"expenses/{BIG_PAGE}&search=A'zo")
        self.assert_constant(f"transfers/{BIG_PAGE}&search=Hamyon")
        self.assert_constant(f"expenses/{BIG_PAGE}&ordering=-summa")

    def test_users_list_constant(self):
        # Xodim barcha foydalanuvchilarni ko'radi: SMALL va LARGE ta foydalanuvchi qo'shiladi
        staff = make_user("xodim", is_staff=True)
        self.login_as(staff)
        User.objects.filter(username__in=("kichik", "katta")).update(status=False)
        for i in range(SMALL):
            make_user(f"u_kichik_{i}")
        with CaptureQueriesContext(connection) as small_ctx:
            small = self.api.get(f"{API}/users/{BIG_PAGE}")
        for i in range(LARGE):
            make_user(f"u_katta_{i}")
        with CaptureQueriesContext(connection) as large_ctx:
            large = self.api.get(f"{API}/users/{BIG_PAGE}")
        self.assertEqual(len(rows(large)) - len(rows(small)), LARGE)
        self.assertEqual(len(small_ctx), len(large_ctx))

    def test_wallets_summary_constant(self):
        self.assert_constant("wallets/summary/")

    def test_monthly_stats_constant(self):
        self.assert_constant("stats/monthly/")

    def test_detail_endpoints_do_not_load_relations_lazily(self):
        """Bitta yozuv: wallet / category / member / user alohida so'rovlarsiz bitta SQL (JOIN) bilan olinadi"""
        self.login_as(self.small_user)
        for url, model in (("incomes", Income), ("expenses", Expense), ("transfers", Transfer), ("debts", Debt)):
            pk = model.objects.filter(user=self.small_user).first().pk
            with CaptureQueriesContext(connection) as ctx:
                response = self.api.get(f"{API}/{url}/{pk}/")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(app_queries(ctx)), 1, f"/{url}/{pk}/:\n" + "\n".join(app_queries(ctx)))

    def test_list_endpoints_use_joins_not_lazy_loading(self):
        """Ro'yxat: faqat asosiy SELECT (+ sahifalash COUNT'i) — bog'liq jadvallar JOIN orqali keladi"""
        self.login_as(self.large_user)
        for url, expected in (("wallets/", 1), (f"incomes/{BIG_PAGE}", 2), (f"expenses/{BIG_PAGE}", 2),
                              (f"transfers/{BIG_PAGE}", 2), (f"debts/{BIG_PAGE}", 2), ("members/", 1)):
            with CaptureQueriesContext(connection) as ctx:
                self.assertEqual(self.api.get(f"{API}/{url}").status_code, 200)
            self.assertEqual(len(app_queries(ctx)), expected, f"/{url}:\n" + "\n".join(app_queries(ctx)))


class PaginationLimitTests(APITestCase):
    """?limit= yuqori chegaradan oshmaydi (frontend _fetchAllPages 200 tadan so'raydi — shu chegara ham 200)"""

    def setUp(self):
        super().setUp()
        self.user = make_user("sahifa")
        self.wallet = Wallet.objects.create(user=self.user, name="Hamyon", summa=0)
        # bulk_create — save() chaqirilmaydi: balansga tegmaydi va 205 ta yozuv tez yaratiladi
        Income.objects.bulk_create(
            [Income(user=self.user, wallet=self.wallet, summa=1 + i) for i in range(MaxLimitPagination.max_limit + 5)]
        )
        self.login_as(self.user)

    def test_max_limit_is_what_frontend_requests(self):
        # static/js/app.js: _fetchAllPages har so'rovda limit=200 so'raydi va 200 dan kam qator kelganda to'xtaydi
        self.assertEqual(MaxLimitPagination.max_limit, 200)

    def test_huge_limit_is_capped(self):
        data = self.api.get(f"{API}/incomes/?limit=10000").json()
        self.assertEqual(len(data["results"]), MaxLimitPagination.max_limit)
        self.assertEqual(data["count"], MaxLimitPagination.max_limit + 5)
        self.assertIn(f"limit={MaxLimitPagination.max_limit}", data["next"])

    def test_limit_200_returns_full_page_then_rest(self):
        # _fetchAllPages shu ketma-ketlikka tayanadi: 200 → 5 (kam) → to'xtaydi
        first = self.api.get(f"{API}/incomes/?limit=200&offset=0").json()
        second = self.api.get(f"{API}/incomes/?limit=200&offset=200").json()
        self.assertEqual((len(first["results"]), len(second["results"])), (200, 5))
        self.assertIsNone(second["next"])

    def test_default_page_size_unchanged(self):
        data = self.api.get(f"{API}/incomes/").json()
        self.assertEqual(len(data["results"]), 10)

    def test_small_and_invalid_limits(self):
        self.assertEqual(len(self.api.get(f"{API}/incomes/?limit=3").json()["results"]), 3)
        # Noto'g'ri limit standart sahifa hajmiga qaytadi (DRF xatti-harakati o'zgarmadi)
        self.assertEqual(len(self.api.get(f"{API}/incomes/?limit=abc").json()["results"]), 10)


class PanelQueryTests(APITestCase):
    """Admin panel akkauntlar ro'yxati: operatsiyalar soni annotatsiya (subquery) bilan, har foydalanuvchiga alohida so'rovsiz"""

    def test_accounts_list_constant(self):
        boss = make_user("boss", is_staff=True, is_superuser=True)
        self.client.force_login(boss)
        url = reverse("panel-accounts")
        # Birinchi so'rovda DeviceTrackingMiddleware qurilma IP manzilini bir marta yozadi — o'lchovga kirmasin
        self.client.get(url)
        counts = []
        for n in (SMALL, LARGE):
            for i in range(n):
                user = make_user(f"panel_{n}_{i}")
                seed_operations(user, 1)
            with CaptureQueriesContext(connection) as ctx:
                self.assertEqual(self.client.get(url).status_code, 200)
            counts.append(len(ctx))
        self.assertEqual(counts[0], counts[1], f"Panel: {SMALL} akkauntda {counts[0]}, {LARGE} akkauntda {counts[1]} ta SQL so'rov")
