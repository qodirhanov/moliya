"""Qidiruv uchun Unicode'ga mos SQL funksiya. SQLite lower() va LIKE faqat ASCII harflarni tushiradi: "али" so'rovi
"Али"ni topmaydi. Casefold SQLite'da Python funksiyasini (unicode_casefold) chaqiradi, boshqa bazalarda esa LOWER().
FAQAT qidiruv uchun: indeks yoki cheklovda ishlatilmasin — Python funksiyasi bilan qurilgan indeks bazani
shu funksiyasiz ochgan vosita (sqlite3 CLI, DB Browser) uchun buzilgan bo'lib qoladi. Noyoblik uchun User.username_key bor"""
import unicodedata

from django.db import connections
from django.db.backends.signals import connection_created
from django.db.models import CharField, Func, Q
from django.db.models.lookups import Contains

SQLITE_CASEFOLD = "unicode_casefold"


def fold(value):
    """Qidiruv kaliti: NFKC + casefold (User.make_username_key bilan bir xil). None -> None (SQL NULL)"""
    if value is None:
        return None
    return unicodedata.normalize("NFKC", str(value)).casefold()


class Casefold(Func):
    """Ustunni katta-kichik harfga qaramaydigan ko'rinishga keltiradi (NULL -> NULL).
    Postgres va boshqalarda LOWER(): u ß/ſ kabi maxsus harflarni casefold() kabi yig'maydi, lekin kirill va o'zbek harflari to'g'ri"""
    function = "LOWER"
    arity = 1
    output_field = CharField()

    def as_sqlite(self, compiler, connection, **extra_context):
        return self.as_sql(compiler, connection, function=SQLITE_CASEFOLD, **extra_context)


def casefold_contains_q(fields, term):
    """Maydonlardan birida term bor (katta-kichik harf va Unicode'ga qaramasdan). Annotatsiya qo'shmaydi:
    SELECT/GROUP BY o'zgarmaydi, shuning uchun annotatsiyali querysetlarda (panel) ham xavfsiz"""
    folded = fold(term)
    condition = Q()
    for field in fields:
        condition |= Q(Contains(Casefold(field), folded))
    return condition


def register_sqlite_functions(sender=None, connection=None, **kwargs):
    """Har bir yangi SQLite ulanishiga unicode_casefold ni o'rnatadi (connection_created signali)"""
    if connection.vendor == "sqlite":
        connection.connection.create_function(SQLITE_CASEFOLD, 1, fold, deterministic=True)


def install():
    """Signalni ulaydi va allaqachon ochiq ulanishlarga (masalan, ready()dan oldin ochilgan) funksiyani darrov o'rnatadi"""
    connection_created.connect(register_sqlite_functions, dispatch_uid="mainapp.unicode_casefold")
    for conn in connections.all(initialized_only=True):
        if conn.connection is not None:
            register_sqlite_functions(connection=conn)
