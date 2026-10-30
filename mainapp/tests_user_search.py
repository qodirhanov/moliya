"""plans.md №4: /users/ (faqat xodimlar) — parallel so'rovda bir xil login nomi 500 emas 400 beradi; /users/?search= va
paneldagi qidiruv kirill harflarida katta-kichikni farqlamaydi (SQLite lower()/LIKE faqat ASCII'ni tushiradi)"""
import sqlite3
from contextlib import contextmanager
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth.models import Permission
from django.db import connection, IntegrityError
from django.db.backends.signals import connection_created
from django.db.models import Value
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from .db_functions import Casefold, SQLITE_CASEFOLD, casefold_contains_q, fold, register_sqlite_functions
from .models import USERNAME_TAKEN_MESSAGE, User, is_username_conflict
from .tests import API, PASSWORD, APITestCase, make_user, rows
from .tests_usernames import key_of, register

TAKEN = {"username": USERNAME_TAKEN_MESSAGE}
# Tekshiruv o'tib ketgan holatni taqlid qiladi: ikki so'rov bir vaqtda "nom bo'sh" deb hisoblagan
@contextmanager
def passes_validation():
    """username_error ham, serializerning avtomatik UniqueValidator'i (aynan bir xil nom) ham "bo'sh" deb o'tkazadi"""
    with (
        mock.patch("mainapp.serializers.username_error", return_value=None),
        mock.patch("rest_framework.validators.UniqueValidator.__call__", return_value=None),
    ):
        yield


class UsersEndpointRaceTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.boss = make_user("boss", is_staff=True, is_superuser=True)
        self.login_as(self.boss)
        self.ali = make_user("ali")

    def test_create_race_returns_400_not_500(self):
        make_user("жасур")
        # "ЖАСУР" faqat username_key bo'yicha to'qnashadi, aynan "жасур" esa username ustunida ham: ikkalasi 400
        for name in ("ЖАСУР", "жасур"):
            with self.subTest(name=name), passes_validation():
                res = self.api.post(f"{API}/users/", {"username": name, "password": PASSWORD}, format="json")
                self.assertEqual(res.status_code, 400, res.content)
                self.assertEqual(res.json(), TAKEN)
        self.assertEqual(User.objects.filter(username_key="жасур").count(), 1)

    def test_exact_duplicate_gets_uzbek_message(self):
        # Poygasiz holat: aynan bir xil nomni modelning UniqueValidator'i ushlaydi — xabari ham o'zbekcha bo'lsin
        res = self.api.post(f"{API}/users/", {"username": "ali", "password": PASSWORD}, format="json")
        self.assertEqual(res.status_code, 400, res.content)
        self.assertEqual(res.json(), {"username": [USERNAME_TAKEN_MESSAGE]})
        res = self.api.patch(f"{API}/users/{self.boss.pk}/", {"username": "ali"}, format="json")
        self.assertEqual(res.json(), {"username": [USERNAME_TAKEN_MESSAGE]})

    def test_create_race_does_not_break_following_requests(self):
        """atomic() savepoint'i xatodan keyin tashqi tranzaksiyani yaroqli qoldiradi: keyingi yozuv ishlaydi"""
        make_user("жасур")
        with passes_validation():
            self.assertEqual(
                self.api.post(f"{API}/users/", {"username": "ЖАСУР", "password": PASSWORD}, format="json").status_code, 400)
        res = self.api.post(f"{API}/users/", {"username": "vali", "password": PASSWORD}, format="json")
        self.assertEqual(res.status_code, 201, res.content)

    def test_put_race_returns_400_not_500(self):
        make_user("жасур")
        with passes_validation():
            res = self.api.put(f"{API}/users/{self.ali.pk}/", {"username": "ЖАСУР", "first_name": "Ali"}, format="json")
        self.assertEqual(res.status_code, 400, res.content)
        self.assertEqual(res.json(), TAKEN)
        self.ali.refresh_from_db()
        self.assertEqual((self.ali.username, self.ali.first_name, key_of(self.ali)), ("ali", "", "ali"))

    def test_patch_race_returns_400_not_500(self):
        make_user("жасур")
        with passes_validation():
            res = self.api.patch(f"{API}/users/{self.ali.pk}/", {"username": "Жасур", "first_name": "Ali"}, format="json")
        self.assertEqual(res.status_code, 400, res.content)
        self.assertEqual(res.json(), TAKEN)
        self.ali.refresh_from_db()
        self.assertEqual((self.ali.username, self.ali.first_name, key_of(self.ali)), ("ali", "", "ali"))

    def test_patch_without_conflict_still_works(self):
        res = self.api.patch(f"{API}/users/{self.ali.pk}/", {"username": "ALI", "first_name": "Ali"}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.ali.refresh_from_db()
        self.assertEqual((self.ali.username, self.ali.first_name, key_of(self.ali)), ("ALI", "Ali", "ali"))

    def test_other_integrity_error_is_not_swallowed(self):
        error = IntegrityError("UNIQUE constraint failed: mainapp_user.email")
        # django.request xatoni logga yozadi (500) — testlar chiqishi shovqinsiz bo'lishi uchun ushlanadi
        with mock.patch.object(User, "save", side_effect=error), self.assertLogs("django.request", "ERROR"):
            with self.assertRaises(IntegrityError):
                self.api.post(f"{API}/users/", {"username": "vali", "password": PASSWORD}, format="json")
            with self.assertRaises(IntegrityError):
                self.api.patch(f"{API}/users/{self.ali.pk}/", {"first_name": "Ali"}, format="json")
            with self.assertRaises(IntegrityError):
                self.api.put(f"{API}/users/{self.ali.pk}/", {"username": "ali", "first_name": "Ali"}, format="json")
            # register ham endi faqat nom to'qnashuvini 400 ga aylantiradi
            with self.assertRaises(IntegrityError):
                register("vali")

    def test_is_username_conflict_recognises_both_unique_columns(self):
        for message in ("UNIQUE constraint failed: mainapp_user.username_key",
                        "UNIQUE constraint failed: mainapp_user.username",
                        'duplicate key value violates unique constraint "mainapp_user_username_key_a1b2_uniq"'):
            with self.subTest(message=message):
                self.assertTrue(is_username_conflict(IntegrityError(message)))
        for message in ("UNIQUE constraint failed: mainapp_user.email",
                        "NOT NULL constraint failed: mainapp_wallet.user_id", "FOREIGN KEY constraint failed"):
            with self.subTest(message=message):
                self.assertFalse(is_username_conflict(IntegrityError(message)))


class UsersSearchTests(APITestCase):
    def setUp(self):
        super().setUp()
        staff = make_user("xodim", is_staff=True)
        staff.user_permissions.add(*Permission.objects.filter(codename="view_user"))
        self.login_as(staff)
        # phone bo'sh (NULL) — Casefold NULL'da yiqilmasligi kerak
        self.ali = make_user("Ali_u", first_name="Али", last_name="Каримов", email="ALI@Почта.uz")
        self.vali = make_user("Бахтиёр", first_name="Рустам", last_name="ЖАСУРОВ", phone="+998901112233")
        self.sher = make_user("sher", first_name="Sherzod", last_name="O'ktamov", email="Sher@Mail.com")

    def search(self, term):
        res = self.api.get(f"{API}/users/", {"search": term})
        self.assertEqual(res.status_code, 200, res.content)
        return {row["username"] for row in rows(res)}

    def test_first_name_ignores_cyrillic_case(self):
        for term in ("али", "АЛИ", "Али", "аЛи"):
            with self.subTest(term=term):
                self.assertEqual(self.search(term), {"Ali_u"})

    def test_last_name_ignores_cyrillic_case(self):
        for term in ("жасуров", "ЖАСУРОВ", "Жасуров"):
            with self.subTest(term=term):
                self.assertEqual(self.search(term), {"Бахтиёр"})
        self.assertEqual(self.search("КАРИМ"), {"Ali_u"})

    def test_email_ignores_cyrillic_case(self):
        for term in ("почта", "ПОЧТА", "@Почта.UZ"):
            with self.subTest(term=term):
                self.assertEqual(self.search(term), {"Ali_u"})

    def test_username_ignores_cyrillic_case(self):
        for term in ("бахтиёр", "БАХТИЁР", "Бахт"):
            with self.subTest(term=term):
                self.assertEqual(self.search(term), {"Бахтиёр"})

    def test_ascii_phone_and_normalization(self):
        self.assertEqual(self.search("SHERZOD"), {"sher"})
        self.assertEqual(self.search("o'KTAMOV"), {"sher"})
        self.assertEqual(self.search("901112233"), {"Бахтиёр"})
        self.assertEqual(self.search("ＳＨＥＲ"), {"sher"})  # to'liq enli lotin harflari (NFKC)

    def test_decomposed_cyrillic_matches_stored_composed_letter(self):
        make_user("kiy", first_name="Кий")  # "й" bir belgi (U+0439)
        self.assertEqual(self.search("кий"), {"kiy"})  # "и" + U+0306 (breve) = "й"
        self.assertEqual(self.search("КИЙ"), {"kiy"})

    def test_multiple_terms_are_anded_and_fields_ored(self):
        self.assertEqual(self.search("РУСТАМ жасуров"), {"Бахтиёр"})
        self.assertEqual(self.search("али ЖАСУРОВ"), set())
        self.assertEqual(self.search("али почта"), {"Ali_u"})

    def test_wildcards_are_literal(self):
        self.assertEqual(self.search("%"), set())
        self.assertEqual(self.search("_"), {"Ali_u"})  # username'dagi haqiqiy "_"

    def test_empty_and_missing_search_return_everything(self):
        self.assertEqual(len(rows(self.api.get(f"{API}/users/"))), 4)
        self.assertEqual(len(rows(self.api.get(f"{API}/users/", {"search": ""}))), 4)

    def test_search_query_count_is_constant(self):
        def count():
            with CaptureQueriesContext(connection) as ctx:
                self.assertEqual(self.api.get(f"{API}/users/", {"search": "АЛИ почта"}).status_code, 200)
            return len(ctx)

        count()  # birinchi so'rov xodim huquqlarini keshga yuklaydi (qo'shimcha so'rovlar)
        before = count()
        for i in range(10):
            make_user(f"ali_{i}", first_name="Али", email=f"a{i}@почта.uz")
        self.assertEqual(count(), before)


class PanelSearchTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(make_user("boss", is_staff=True, is_superuser=True))
        make_user("Ali_u", first_name="Али", last_name="Каримов", email="ALI@Почта.uz")
        make_user("Бахтиёр", first_name="Рустам", last_name="ЖАСУРОВ", phone="+998901112233")
        make_user("sher", first_name="Sherzod", last_name="O'ktamov", email="Sher@Mail.com")

    def panel(self, term):
        res = self.client.get(reverse("panel-accounts"), {"q": term})
        self.assertEqual(res.status_code, 200)
        return {user.username for user in res.context["page"]}

    def test_first_name_last_name_email_username_ignore_cyrillic_case(self):
        cases = {
            "али": "Ali_u", "АЛИ": "Ali_u",                      # ism
            "жасуров": "Бахтиёр", "ЖасуроВ": "Бахтиёр",          # familiya
            "почта": "Ali_u", "ПОЧТА.UZ": "Ali_u",               # email
            "бахтиёр": "Бахтиёр", "БАХТИЁР": "Бахтиёр",          # login nomi
            "SHERZOD": "sher", "mail.COM": "sher",               # ASCII oldingidek ishlaydi
            "901112233": "Бахтиёр",                              # telefon
        }
        for term, username in cases.items():
            with self.subTest(term=term):
                self.assertEqual(self.panel(term), {username})

    def test_no_match_and_wildcards(self):
        self.assertEqual(self.panel("йўқ"), set())
        self.assertEqual(self.panel("%"), set())

    def test_search_does_not_duplicate_rows_with_stats(self):
        """Annotatsiyali (subquery) querysetda qidiruv qatorlarni ko'paytirmaydi va sonlar saqlanadi"""
        res = self.client.get(reverse("panel-accounts"), {"q": "РУСТАМ"})
        self.assertEqual([u.username for u in res.context["page"]], ["Бахтиёр"])


class CasefoldFunctionTests(APITestCase):
    def test_sql_function_handles_null_empty_and_unicode(self):
        if connection.vendor != "sqlite":
            self.skipTest("unicode_casefold faqat SQLite uchun")
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT {SQLITE_CASEFOLD}(NULL), {SQLITE_CASEFOLD}(''), {SQLITE_CASEFOLD}('АЛИ Ўзбек'), "
                           f"{SQLITE_CASEFOLD}('ＡＬＩ'), {SQLITE_CASEFOLD}('Straße')")
            self.assertEqual(cursor.fetchone(), (None, "", "али ўзбек", "ali", "strasse"))

    def test_orm_casefold_on_null_and_empty_columns(self):
        user = make_user("nullish")  # first_name "", phone None
        row = User.objects.filter(pk=user.pk).annotate(first=Casefold("first_name"), phone_f=Casefold("phone")) \
            .values_list("first", "phone_f").get()
        self.assertEqual(row, ("", None))
        # NULL ustun "contains" bilan hech narsa topmaydi, xato ham bermaydi
        self.assertFalse(User.objects.filter(pk=user.pk).filter(casefold_contains_q(["phone"], "9")).exists())
        self.assertTrue(User.objects.filter(pk=user.pk).filter(casefold_contains_q(["first_name", "phone"], "")).exists())

    def test_fold(self):
        self.assertIsNone(fold(None))
        self.assertEqual(fold(""), "")
        self.assertEqual(fold("АЛИ"), "али")
        self.assertEqual(fold("ＡＬＩ"), "ali")
        self.assertEqual(fold(User.make_username_key("Straße")), "strasse")
        self.assertEqual(fold("Али"), User.make_username_key("Али"))

    def test_compiles_to_python_function_on_sqlite_and_lower_elsewhere(self):
        compiler = User.objects.all().query.get_compiler(connection=connection)
        sql, _ = compiler.compile(Casefold(Value("x")))
        expected = f"{SQLITE_CASEFOLD}(" if connection.vendor == "sqlite" else "LOWER("
        self.assertTrue(sql.startswith(expected), sql)
        # Boshqa bazalar uchun standart shablon (as_sql) LOWER()
        generic_sql, _ = Casefold(Value("x")).as_sql(compiler, connection)
        self.assertTrue(generic_sql.startswith("LOWER("), generic_sql)

    def test_signal_registers_function_on_every_new_sqlite_connection(self):
        """connection_created signali ready() da ulangan: yangi ulanish funksiyasiz qolmaydi"""
        raw = sqlite3.connect(":memory:")
        self.addCleanup(raw.close)
        fake = SimpleNamespace(vendor="sqlite", connection=raw)
        connection_created.send(sender=type(connection), connection=fake)
        self.assertEqual(raw.execute(f"SELECT {SQLITE_CASEFOLD}('ЖАСУР'), {SQLITE_CASEFOLD}(NULL)").fetchone(),
                         ("жасур", None))

    def test_register_ignores_non_sqlite_connections(self):
        register_sqlite_functions(connection=SimpleNamespace(vendor="postgresql", connection=None))
