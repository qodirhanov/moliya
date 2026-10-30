"""Valyuta kurslari — O'zbekiston Markaziy banki (cbu.uz) rasmiy kursi.

Kurslar ExchangeRate jadvalida saqlanadi va RATES_TTL dan eski bo'lsa qayta olinadi
(saqlangan kurs bo'lsa — fonda, so'rov eski kurs bilan darhol javob oladi).
Markaziy bank javob bermasa (internet yo'q va h.k.) oxirgi saqlangan kurs ishlatiladi;
umuman kurs bo'lmasa CurrencyRateError ko'tariladi.
"""
import json
import logging
import re
import threading
import urllib.request
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from django.conf import settings
from django.core.cache import cache
from django.db import connection, transaction
from django.utils import timezone

from .models import ExchangeRate
from .money import quantize_money

logger = logging.getLogger(__name__)

CBU_URL = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"
RATES_TTL = timedelta(hours=1)
# Markaziy bank javob bermasa, har so'rovda kutib qolmaslik uchun shuncha vaqt qayta urinilmaydi
REFRESH_RETRY_SECONDS = 5 * 60
_REFRESH_FAILED_KEY = "cbu_refresh_failed"
# Markaziy bank ro'yxatida yo'q kod ("XYZ") uchun "bu kod yo'q" natijasi shuncha vaqt eslab qolinadi: aks holda har so'rov
# (/wallets/summary/, /rates/convert/) 10 soniyagacha kutib, ~75 qatorni qayta yozardi
_MISSING_CODE_KEY = "cbu_rate_missing:"
MISSING_CODE_SECONDS = int(RATES_TTL.total_seconds())
# O'tgan kunlarning kursi (arxiv) o'zgarmaydi — uzoq keshlanadi; arxivga ulanib bo'lmasa shuncha vaqt qayta urinilmaydi
_HISTORY_KEY = "cbu_rates_on:"
_HISTORY_FAILED_KEY = "cbu_history_failed"
HISTORY_CACHE_SECONDS = 365 * 24 * 60 * 60
HISTORY_RETRY_SECONDS = 5 * 60
BASE_CURRENCY = "UZS"

# Foydalanuvchilar yozishi mumkin bo'lgan so'm nomlari -> ISO kodi
CURRENCY_ALIASES = {
    "SO'M": "UZS", "SO‘M": "UZS", "SOʻM": "UZS", "SOM": "UZS", "SUM": "UZS", "СУМ": "UZS", "СЎМ": "UZS",
    "$": "USD", "€": "EUR", "₽": "RUB",
}
_ISO_RE = re.compile(r"^[A-Z]{3}$")


class CurrencyRateError(Exception):
    """Kursni aniqlab bo'lmadi"""


def normalize_currency(value):
    """Valyuta nomini ISO kodiga keltiradi ("so'm" -> "UZS", "usd" -> "USD")"""
    code = str(value or "").strip().upper()
    return CURRENCY_ALIASES.get(code, code)


def is_valid_currency_code(code):
    return bool(_ISO_RE.match(code or ""))


def _fetch_cbu(day=None):
    """Markaziy bankdan kurslarni oladi: {"USD": (Decimal("11809.19"), "08.10.2026", Decimal("-12.4")), ...}.
    Uchinchi qiymat — oldingi kunga nisbatan o'zgarish (Diff) yoki None.
    day berilsa (date) — o'sha kunning arxiv kursi (.../json/all/YYYY-MM-DD/), bo'lmasa joriy kurs"""
    url = CBU_URL if day is None else f"{CBU_URL}all/{day:%Y-%m-%d}/"
    req = urllib.request.Request(url, headers={"User-Agent": "Moliya/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    rates = {}
    for item in data:
        try:
            code = str(item["Ccy"]).upper()
            nominal = Decimal(str(item.get("Nominal") or "1"))
            rate = Decimal(str(item["Rate"])) / nominal
        except (KeyError, InvalidOperation, ZeroDivisionError):
            continue
        try:
            diff = Decimal(str(item["Diff"])) / nominal
        except (KeyError, InvalidOperation):
            diff = None
        if rate > 0:
            rates[code] = (rate, str(item.get("Date") or ""), diff)
    if not rates:
        raise CurrencyRateError("Markaziy bank bo'sh javob qaytardi")
    return rates


def _refresh_rates():
    """Kurslarni bazaga yozadi. Markaziy bank ro'yxatidagi kodlarni qaytaradi"""
    rates = _fetch_cbu()
    with transaction.atomic():
        for code, (rate, rate_date, *extra) in rates.items():
            diff = extra[0] if extra else None
            ExchangeRate.objects.update_or_create(
                currency=code, defaults={"rate": rate, "rate_date": rate_date, "diff": diff}
            )
    return set(rates)


def _try_refresh(code=None):
    """Kurslarni yangilaydi. Tarmoq xatosida REFRESH_RETRY_SECONDS davomida qayta urinilmaydi. Natija: muvaffaqiyatli bo'ldimi.
    Yangilash o'tib ham `code` Markaziy bank ro'yxatida chiqmasa, u MISSING_CODE_SECONDS davomida qayta so'ralmaydi"""
    try:
        listed = _refresh_rates()
    except Exception:
        logger.warning("Markaziy bank kursini yangilab bo'lmadi", exc_info=True)
        cache.set(_REFRESH_FAILED_KEY, True, REFRESH_RETRY_SECONDS)
        return False
    if code and code not in listed:
        cache.set(_MISSING_CODE_KEY + code, True, MISSING_CODE_SECONDS)
    return True


_refresh_lock = threading.Lock()


def _refresh_in_background(code=None):
    """Eskirgan kurs fonda yangilanadi — foydalanuvchi so'rovi Markaziy bank javobini (10 soniyagacha) kutib qolmaydi.
    Bir jarayonda bir vaqtda faqat bitta yangilash ishlaydi"""
    if not _refresh_lock.acquire(blocking=False):
        return

    def run():
        try:
            _try_refresh(code)
        finally:
            connection.close()  # fon oqimining o'z baza ulanishi
            _refresh_lock.release()

    threading.Thread(target=run, name="cbu-rates-refresh", daemon=True).start()


def get_rate_to_uzs(code):
    """1 birlik `code` necha so'm ekanini qaytaradi (Decimal)"""
    code = normalize_currency(code)
    if code == BASE_CURRENCY:
        return Decimal(1)

    stored = ExchangeRate.objects.filter(currency=code).first()
    if stored is None and not is_valid_currency_code(code):
        # ISO ko'rinishida bo'lmagan nom (masalan ?from=dollar) Markaziy bank ro'yxatida bo'lmaydi: so'rashga ham,
        # keshga (har xil nom keshni to'ldirib yubormasin) yozishga ham arzimaydi
        raise CurrencyRateError(f"{code} valyutasi kursini aniqlab bo'lmadi")
    stale = stored is None or timezone.now() - stored.updated_at > RATES_TTL
    if stale and not cache.get(_REFRESH_FAILED_KEY) and not cache.get(_MISSING_CODE_KEY + code):
        if stored is not None and getattr(settings, "CURRENCY_BACKGROUND_REFRESH", True):
            # Eski kurs bor: hozircha u bilan javob beramiz, yangisi fonda olinadi
            _refresh_in_background(code)
        elif _try_refresh(code):
            stored = ExchangeRate.objects.filter(currency=code).first()

    if stored is None:
        raise CurrencyRateError(f"{code} valyutasi kursini aniqlab bo'lmadi")
    return stored.rate


def _historical_rates(day):
    """O'tgan kunning Markaziy bank kurslari {kod: Decimal} yoki olib bo'lmasa None. O'tgan kun kursi o'zgarmaydi,
    shuning uchun kesh uzoq saqlanadi (bir kun uchun bitta so'rov — barcha valyutalar birga). Tarmoq xatosida
    HISTORY_RETRY_SECONDS davomida qayta urinilmaydi: doimiy to'lovlarni bir necha kunga yozishda
    har kun 10 soniyalab kutib qolmaslik uchun"""
    key = _HISTORY_KEY + day.isoformat()
    cached = cache.get(key)
    if cached:
        return {code: Decimal(rate) for code, rate in cached.items()}
    if cache.get(_HISTORY_FAILED_KEY):
        return None
    try:
        fetched = _fetch_cbu(day)
    except Exception:
        logger.warning("Markaziy bank %s kuni kursini olib bo'lmadi", day, exc_info=True)
        cache.set(_HISTORY_FAILED_KEY, True, HISTORY_RETRY_SECONDS)
        return None
    cache.set(key, {code: str(values[0]) for code, values in fetched.items()}, HISTORY_CACHE_SECONDS)
    return {code: values[0] for code, values in fetched.items()}


def get_rate_to_uzs_on(code, day):
    """1 birlik `code` o'sha kuni (day — mahalliy sana) necha so'm edi. Bugun va kelajak uchun, shuningdek arxivdan
    olib bo'lmasa — joriy kurs (get_rate_to_uzs); u ham bo'lmasa CurrencyRateError"""
    code = normalize_currency(code)
    if code == BASE_CURRENCY:
        return Decimal(1)
    if day < timezone.localdate():
        rate = (_historical_rates(day) or {}).get(code)
        if rate:
            return rate
    return get_rate_to_uzs(code)


def get_rates_snapshot():
    """Kurs sahifasi uchun barcha saqlangan kurslar (ExchangeRate ro'yxati). Markaziy bank hammasini bitta javobda
    beradi, shuning uchun USD kursi orqali o'sha keshlash/yangilash yo'li ishlatiladi; internet bo'lmasa — oxirgi saqlangani"""
    try:
        get_rate_to_uzs("USD")
    except CurrencyRateError:
        pass
    return list(ExchangeRate.objects.order_by("currency"))


def get_rate(from_code, to_code):
    """1 birlik from_code = ? birlik to_code"""
    from_code, to_code = normalize_currency(from_code), normalize_currency(to_code)
    if from_code == to_code:
        return Decimal(1)
    return get_rate_to_uzs(from_code) / get_rate_to_uzs(to_code)


def round_amount(value):
    """Decimal miqdorni 2 xonali kasrga (tiyin) yaxlitlaydi (0.005 yuqoriga)"""
    return quantize_money(value)


def convert(amount, from_code, to_code):
    """Miqdorni bir valyutadan boshqasiga o'tkazadi. (yaxlitlangan_miqdor, kurs) qaytaradi"""
    rate = get_rate(from_code, to_code)
    return round_amount(Decimal(amount) * rate), rate.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)


class UzsConverter:
    """Hisobot uchun: har xil valyutadagi miqdorlarni so'mga o'giradi (Markaziy bank kursi).
    Kurs har bir valyuta uchun bir marta olinadi. Kursi topilmagan valyuta `missing` ga yoziladi
    va jamiga qo'shilmaydi (aks holda dollar so'm bilan bir xil son bo'lib qo'shilib ketardi)"""

    def __init__(self):
        self._rates = {}
        self.missing = set()

    def rate(self, currency):
        code = normalize_currency(currency) or BASE_CURRENCY
        if code not in self._rates:
            try:
                self._rates[code] = get_rate_to_uzs(code)
            except CurrencyRateError:
                self._rates[code] = None
                self.missing.add(code)
        return self._rates[code]

    def to_uzs(self, amount, currency):
        """So'mdagi qiymat (Decimal, yaxlitlanmagan) yoki kurs topilmasa None"""
        rate = self.rate(currency)
        return None if rate is None else Decimal(amount or 0) * rate
