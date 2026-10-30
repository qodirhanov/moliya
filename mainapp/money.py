"""Pul miqdorlarini qat'iy o'qish va yaxlitlash (barcha valyutalar uchun 2 xonali kasr — tiyin)"""
import math
import re
from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")
MONEY_DECIMALS_MESSAGE = "Miqdorda ko'pi bilan 2 ta kasr xonasi bo'lishi mumkin"
MONEY_INVALID_MESSAGE = "Miqdor son bo'lishi kerak (masalan: 100 yoki 12.50)"

# Faqat ASCII raqamlar va nuqta: "1e5", "NaN", "Infinity", "١٢" va vergulli yozuv qabul qilinmaydi
_AMOUNT_RE = re.compile(r"-?[0-9]+(?:\.[0-9]+)?")


def quantize_money(value):
    """Decimal (yoki son) ni 2 xonaga yaxlitlaydi, 0.005 yuqoriga (ROUND_HALF_UP)"""
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def parse_amount(value):
    """So'rovdagi miqdorni qat'iy o'qiydi: int, float yoki ASCII raqamli satr ("12.5", "100"). Yaroqsiz qiymat
    (bool, NaN, Infinity, 1e5, bo'sh satr, None, ro'yxat) uchun ValueError(MONEY_INVALID_MESSAGE), 2 tadan ko'p
    kasr xonasi uchun ValueError(MONEY_DECIMALS_MESSAGE). Decimal qaytaradi (chegara tekshiruvi chaqiruvchida).
    Decimal(float) emas, float'ning qisqa yozuvi olinadi: 0.1 -> "0.1", 0.10000000000000001 emas"""
    if isinstance(value, bool):
        raise ValueError(MONEY_INVALID_MESSAGE)
    try:
        if isinstance(value, int):
            text = str(value)  # 4300+ xonali son str() da ValueError beradi
        elif isinstance(value, float):
            if not math.isfinite(value):
                raise ValueError(MONEY_INVALID_MESSAGE)
            text = format(Decimal(repr(value)), "f")
        elif isinstance(value, str):
            text = value.strip()
        else:
            raise ValueError(MONEY_INVALID_MESSAGE)
    except ValueError:
        raise ValueError(MONEY_INVALID_MESSAGE)
    if not _AMOUNT_RE.fullmatch(text):
        raise ValueError(MONEY_INVALID_MESSAGE)
    fraction = text.partition(".")[2]
    if len(fraction.rstrip("0")) > 2:
        raise ValueError(MONEY_DECIMALS_MESSAGE)
    return Decimal(text)
