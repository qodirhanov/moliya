"""Ovozli yordamchi (voice.py) uchun gapni qoidalar bo'yicha tahlil qilish: bepul, internetsiz va tez.
Brauzerning nutqni tanish xizmati o'zbekcha gapni lotin yoki kirill yozuvida, sonlarni raqam yoki so'z bilan
qaytarishi mumkin ("45 ming", "qirq besh ming", "1,5 million") — hammasi bir xil ko'rinishga keltiriladi.
Natija — buyruq lug'ati (intent + summa, sana, hamyon/toifa/odam so'zlari); bazadagi yozuvlarga bog'lash voice.py da"""
import re
from datetime import date, timedelta
from decimal import Decimal

# O'zbek (va rus) kirill harflari -> lotin. Tanish xizmati ba'zan o'zbekcha gapni kirillda qaytaradi
_CYR = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "j", "з": "z", "и": "i",
    "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
    "у": "u", "ф": "f", "х": "x", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "'", "ы": "i", "ь": "",
    "э": "e", "ю": "yu", "я": "ya", "ў": "o'", "қ": "q", "ғ": "g'", "ҳ": "h",
}
_APOSTROPHES = re.compile(r"[ʻʼ‘’`´ʹ′]")


def normalize(text):
    """Kichik harf, lotin yozuvi, bitta xil tutuq belgisi ('), ortiqcha belgilar va bo'shliqlarsiz"""
    text = str(text or "").lower()
    text = "".join(_CYR.get(ch, ch) for ch in text)
    text = _APOSTROPHES.sub("'", text)
    text = re.sub(r"[^\w\s'$.,\-?]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def loose(text):
    """Kalit so'zlarni solishtirish uchun: tutuq belgisisiz ("to'ladim" va "toladim" bir xil), tinish belgilarsiz"""
    text = normalize(text).replace("'", "")
    text = re.sub(r"(?<!\d)[.,]|[.,](?!\d)|[?\-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# ---------- Sonlar ----------

_UNITS = {"bir": 1, "ikki": 2, "uch": 3, "tort": 4, "besh": 5, "olti": 6, "yetti": 7, "sakkiz": 8, "toqqiz": 9,
          "on": 10, "yigirma": 20, "ottiz": 30, "qirq": 40, "ellik": 50, "oltmish": 60, "yetmish": 70,
          "sakson": 80, "toqson": 90}
# Ruscha sonlar (kirilldan lotinga o'girilgan ko'rinishda: "сорок пять тысяч" -> "sorok pyat tisyach"). Toshkentda
# ko'pchilik pulni ruscha aytadi; brauzer ham o'zbekchani tanimasa ru-RU ga o'tadi. Yuzliklar ham qo'shiladigan son
_UNITS.update({
    "odin": 1, "odna": 1, "odnu": 1, "dva": 2, "dve": 2, "tri": 3, "chetire": 4, "pyat": 5, "shest": 6, "sem": 7,
    "vosem": 8, "devyat": 9, "desyat": 10, "odinnadtsat": 11, "dvenadtsat": 12, "trinadtsat": 13, "chetirnadtsat": 14,
    "pyatnadtsat": 15, "shestnadtsat": 16, "semnadtsat": 17, "vosemnadtsat": 18, "devyatnadtsat": 19,
    "dvadtsat": 20, "tridtsat": 30, "sorok": 40, "pyatdesyat": 50, "shestdesyat": 60, "semdesyat": 70,
    "vosemdesyat": 80, "devyanosto": 90, "sto": 100, "dvesti": 200, "trista": 300, "chetiresta": 400, "pyatsot": 500,
    "shestsot": 600, "semsot": 700, "vosemsot": 800, "devyatsot": 900,
})
_UNITS_DECIMAL = {"poltora": Decimal("1.5"), "poltori": Decimal("1.5")}
_MULTS = {"ming": 1000, "million": 10 ** 6, "mln": 10 ** 6, "milion": 10 ** 6, "milliard": 10 ** 9,
          "mlrd": 10 ** 9, "miliard": 10 ** 9,
          "tisyach": 1000, "tisyachi": 1000, "tisyacha": 1000, "tis": 1000, "tisch": 1000,
          "milliona": 10 ** 6, "millionov": 10 ** 6, "milliarda": 10 ** 9, "milliardov": 10 ** 9}
_HALF_WORDS = ("yarim", "pol")
# "ellikta", "mingga", "yuzlik" — son so'zidan keyingi qo'shimchalar
_NUM_SUFFIX = r"(?:ta|tasi|ga|ka|lik|dan|ni|ning|i|si)?"
_NUM_WORD_RE = re.compile(rf"^({'|'.join(sorted(list(_UNITS) + list(_UNITS_DECIMAL) + list(_MULTS) + ['yuz'] + list(_HALF_WORDS), key=len, reverse=True))}){_NUM_SUFFIX}$")
# "45k" / "1.5m" — yozib yuborilgan buyruqlarda qisqartma
# "45.000" / "1.200.000" / "1,500,000" — 3 xonali guruhlar minglik ajratgich (butun son); "1.5", "2.50" — kasr
_DIGITS_RE = re.compile(rf"^([1-9]\d{{0,2}}(?:[.,]\d{{3}})+|\d+(?:[.,]\d+)?)(k|m)?{_NUM_SUFFIX}$")
_GROUPED_RE = re.compile(r"^[1-9]\d{0,2}(?:[.,]\d{3})+$")

CURRENCY_WORDS = {
    "UZS": ("som", "sum", "sumlik", "somlik", "sumga", "somga", "sumni", "somni", "uzs", "sumov", "suma"),
    "USD": ("dollar", "dollor", "dollarga", "dollarni", "dollardan", "usd", "$", "dollarlik", "bucks", "dollarov",
            "dollara"),
    "EUR": ("yevro", "evro", "euro", "eur", "yevroga", "evroga"),
    "RUB": ("rubl", "rubli", "rub", "rublga", "rubldan", "rubley", "rublya"),
    "KZT": ("tenge", "tengе", "kzt"),
    "TRY": ("lira", "try"),
    "CNY": ("yuan", "cny"),
    "AED": ("dirham", "aed"),
    "KRW": ("von", "won", "krw"),
    "JPY": ("iyena", "yena", "jpy"),
    "CHF": ("frank", "chf"),
    "GBP": ("funt", "gbp"),
}
_CURRENCY_BY_WORD = {w: code for code, words in CURRENCY_WORDS.items() for w in words}


def _num_token(tok):
    """('num', Decimal) | ('unit', int) | ('yuz',) | ('mult', int) | ('half',) | None"""
    m = _DIGITS_RE.match(tok)
    if m:
        raw = m.group(1)
        value = Decimal(re.sub(r"[.,]", "", raw) if _GROUPED_RE.match(raw) else raw.replace(",", "."))
        scale = {"k": 1000, "m": 10 ** 6}.get(m.group(2) or "", 1)
        return ("num", value * scale)
    m = _NUM_WORD_RE.match(tok)
    if not m:
        return None
    word = m.group(1)
    if word in _UNITS:
        return ("unit", _UNITS[word])
    if word in _UNITS_DECIMAL:
        return ("unit", _UNITS_DECIMAL[word])
    if word in _MULTS:
        return ("mult", _MULTS[word])
    return ("yuz",) if word == "yuz" else ("half",)


_COUNTER_RE = re.compile(r"^(ta|dona|marta|kishi\w*|kun\w*|hafta\w*|oy\w*|yil\w*|soat\w*|kilo\w*|kg|litr\w*)$")


def _continues_after_mult(tokens, i, tok, kind):
    """"ming/million" dan keyingi son summaning davomimi: "45 ming 500" ha, "45 ming 2 ta non", "20 ming 2 kishiga" yo'q"""
    following = tokens[i + 1] if i + 1 < len(tokens) else ""
    if _COUNTER_RE.match(following):
        return False
    if kind == "unit":
        return True
    parsed = _num_token(following)
    if parsed and parsed[0] in ("mult", "yuz"):
        return True  # "2 million 500 ming", "20 ming 5 yuz"
    return bool(re.fullmatch(r"\d{3}", tok) or _GROUPED_RE.match(tok))


def find_amounts(text):
    """Gapdagi barcha summalar: [{value, currency, start, end, strong}] (start/end — loose() so'zlari indeksi).
    strong — raqam, ming/million yoki valyuta bor: "bir kilo" dagi "bir" kabi tasodifiy sondan ajratish uchun"""
    tokens = text.split() if isinstance(text, str) else text
    found = []
    i = 0
    while i < len(tokens):
        # "$100"
        currency = None
        tok = tokens[i]
        if tok.startswith("$") and len(tok) > 1:
            currency, tok = "USD", tok[1:]
        if tok.endswith("$") and len(tok) > 1:
            currency, tok = "USD", tok[:-1]
        if not _num_token(tok):
            i += 1
            continue
        start = i
        total, cur, last_mult = Decimal(0), Decimal(0), None
        strong = currency is not None
        prev_kind = None
        while i < len(tokens):
            t = tokens[i] if i != start else tok
            if i != start and t.startswith("$") and len(t) > 1:
                break
            parsed = _num_token(t.rstrip("$"))
            if not parsed:
                break
            kind = parsed[0]
            if prev_kind == "mult" and kind in ("num", "unit") and not _continues_after_mult(tokens, i, t, kind):
                break
            if kind == "num":
                strong = True
                value = parsed[1]
                # "45 000" — tanish xizmati minglarni bo'shliq bilan ajratadi
                if prev_kind == "num" and re.fullmatch(r"\d{3}", t):
                    cur = cur * 1000 + value
                elif prev_kind == "num":
                    break  # ikki alohida son ("2 ta 10 ming" emas, "5 7") — keyingisi yangi summa
                else:
                    cur += value
            elif kind == "unit":
                if prev_kind == "num":
                    break
                cur += parsed[1]
            elif kind == "yuz":
                cur = (cur or 1) * 100
            elif kind == "mult":
                strong = True
                total += (cur or 1) * parsed[1]
                cur, last_mult = Decimal(0), parsed[1]
            elif kind == "half":
                if cur:
                    cur += Decimal("0.5")
                elif last_mult:
                    total += last_mult * Decimal("0.5")
                else:
                    cur = Decimal("0.5")
            if t.endswith("$"):
                currency = "USD"
            prev_kind = kind
            i += 1
        value = total + cur
        if i < len(tokens) and tokens[i] in _CURRENCY_BY_WORD:
            currency = _CURRENCY_BY_WORD[tokens[i]]
            strong = True
            i += 1
        if value > 0:
            found.append({"value": value, "currency": currency, "start": start, "end": i, "strong": strong})
    return found


def best_amount(amounts):
    """Bir nechta son bo'lsa — valyuta yoki ming/million bilan aytilgani, bo'lmasa eng kattasi"""
    if not amounts:
        return None
    strong = [a for a in amounts if a["strong"]]
    return max(strong or amounts, key=lambda a: a["value"])


def currency_in(text_loose):
    for tok in text_loose.split():
        if tok in _CURRENCY_BY_WORD:
            return _CURRENCY_BY_WORD[tok]
    return None


# ---------- Sanalar ----------

MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"]
_MONTH_ALIASES = {"sentyabr": 9, "oktyabr": 10, "yanvr": 1, "fevrl": 2, "iyn": 6, "iyl": 7}
_MONTH_RE = "|".join(MONTHS + list(_MONTH_ALIASES))
# Oy nomidan keyin faqat qo'shimcha: `\w*` bo'lsa "3 marta" 3-mart sanasi deb o'qilardi
_DAY_MONTH_RE = re.compile(rf"\b(\d{{1,2}})(?:\s*(?:chi|inchi|nchi))?\s*({_MONTH_RE})(?:dagi|gacha|ning|dan|da|ga|ni|i)?\b")
_AGO_RE = re.compile(r"\b(\d+|bir|ikki|uch|tort|besh|olti|yetti|sakkiz|toqqiz|on|yarim)\s*(kun|hafta|oy|yil)\s*(?:oldin|avval|burun)\b")
_DAY_OF_MONTH_RE = re.compile(r"\b(\d{1,2})\s*(?:chi|inchi|nchi)?\s*(?:sana\w*|chisi\w*|kuni)\b")
_IN_PERIOD_RE = re.compile(r"\b(\d+|bir|ikki|uch|tort|besh|olti|yetti|sakkiz|toqqiz|on|yarim)\s*(kun|hafta|oy|yil)\w*\s*(?:ga|dan keyin|keyin|ichida)?\b")


def _month_number(word):
    for i, name in enumerate(MONTHS, start=1):
        if word.startswith(name):
            return i
    for alias, n in _MONTH_ALIASES.items():
        if word.startswith(alias):
            return n
    return None


def _safe_date(year, month, day):
    try:
        return date(year, month, day)
    except ValueError:
        return None


def find_date(text_loose, today, future=False):
    """Operatsiya sanasi (future=False) yoki qarz muddati (future=True). (date, [band so'z indekslari]) qaytaradi"""
    m = _DAY_MONTH_RE.search(text_loose)
    if m:
        month = _month_number(m.group(2))
        d = _safe_date(today.year, month, int(m.group(1))) if month else None
        if d:
            if future and d < today:
                d = _safe_date(today.year + 1, month, int(m.group(1))) or d
            elif not future and d > today:
                d = _safe_date(today.year - 1, month, int(m.group(1))) or d
            return d, m.span()
    words = text_loose.split()
    if future:
        m = _IN_PERIOD_RE.search(text_loose)
        if m:
            n = m.group(1)
            count = Decimal("0.5") if n == "yarim" else Decimal(n) if n.isdigit() else Decimal(_UNITS.get(n, 1))
            unit = m.group(2)
            days = {"kun": 1, "hafta": 7, "oy": 30, "yil": 365}[unit] * count
            return today + timedelta(days=int(days)), m.span()
        if "ertaga" in words or "zavtra" in words:
            return today + timedelta(days=1), None
        if "indinga" in words or "indin" in words:
            return today + timedelta(days=2), None
        return None, None
    m = _AGO_RE.search(text_loose)
    if m:
        n = m.group(1)
        count = Decimal("0.5") if n == "yarim" else Decimal(n) if n.isdigit() else Decimal(_UNITS.get(n, 1))
        days = {"kun": 1, "hafta": 7, "oy": 30, "yil": 365}[m.group(2)] * count
        # Juda katta son (masalan tanishdagi xato) sana chegarasidan chiqib ketmasin
        if days <= 3650:
            return today - timedelta(days=int(days)), m.span()
    if "kecha" in words or "kechagi" in words or "vchera" in words:
        return today - timedelta(days=1), None
    if "pozavchera" in words:
        return today - timedelta(days=2), None
    if re.search(r"\b(otgan|oldingi) kun", text_loose):
        return today - timedelta(days=2), None
    return None, None


def find_day_of_month(text_loose):
    m = _DAY_OF_MONTH_RE.search(text_loose)
    if m and 1 <= int(m.group(1)) <= 31:
        return int(m.group(1)), m.span()
    return None, None


def find_period(text_loose):
    """Savollar uchun davr: today | yesterday | week | last_week | month | last_month | year"""
    if re.search(r"\bbugun|\bsegodnya", text_loose):
        return "today"
    if re.search(r"\bkecha|\bvchera", text_loose):
        return "yesterday"
    if re.search(r"\b(otgan|oldingi|otkan) hafta|proshl\w* nedel", text_loose):
        return "last_week"
    if re.search(r"\bhafta|nedel", text_loose):
        return "week"
    if re.search(r"\b(otgan|oldingi|otkan) oy|proshl\w* mesyats", text_loose):
        return "last_month"
    if re.search(r"\b(bu|shu|joriy) yil|\byil davomida|\byilda", text_loose):
        return "year"
    return "month"


def period_bounds(period, today):
    if period == "today":
        return today, today
    if period == "yesterday":
        d = today - timedelta(days=1)
        return d, d
    if period == "week":
        return today - timedelta(days=today.weekday()), today
    if period == "last_week":
        start = today - timedelta(days=today.weekday() + 7)
        return start, start + timedelta(days=6)
    if period == "last_month":
        last = today.replace(day=1) - timedelta(days=1)
        return last.replace(day=1), last
    if period == "year":
        return today.replace(month=1, day=1), today
    return today.replace(day=1), today


PERIOD_PHRASES = {
    "today": "Bugun", "yesterday": "Kecha", "week": "Shu hafta", "last_week": "O'tgan hafta",
    "month": "Shu oy", "last_month": "O'tgan oy", "year": "Shu yil",
}


# ---------- Niyat (intent) ----------

def _has(text, pattern):
    return re.search(pattern, text) is not None


_WAKE_RE = re.compile(r"^(?:(?:hi|hey|hay|xay|xey|ey|ay|salom|assalomu alaykum)\s+)?(?:moliya|maliya|molia|moliyo|mollia)\b\s*")
_QUESTION_RE = (r"\b(qancha|nechpul|nech pul|necha|nechi|nechchi|nechta|qanaqa|qanday|bormi|qani|qaysi|nima|qachon|"
                r"kim|kimga|kimdan|kimlar|qayer\w*|skolko|kakoy|kakaya|kogda)\b|\?")
# Ruscha fe'llar (lotinga o'girilgan): потратил -> potratil, взял в долг -> vzyal v dolg
_RU_EXPENSE = r"potrat|zaplati|kupil|oplati|rasxod|istratil"
_RU_INCOME = r"poluchil|zarplat|prishl|doxod|zarabotal|premi"
# Oxirgi amalni tuzatish belgilari: "yo'q, 50 ming edi", "kartadan edi", "summasini 60 mingga o'zgartir"
_EDIT_WORDS = r"\b(edi|emas)\b|ozgartir|tuzat|almashtir(?!d)|ispravi|izmeni"
_EDIT_TARGETS = r"oxirgi|summa|miqdor|hamyon|turkum|sana|kecha|vchera|\w+dan\b|\w+(ga|ka|qa)\b"
_ACTION_VERBS = (r"sarf|ishlatd|ketdi|toladim|tolab|sotib|xarid|berdim|oldim|tushdi|keldi|qosh|yoz|otkaz|"
                 r"yechd|yechib|qaytar|uzd")


def strip_wake(text_loose):
    """«Salom Moliya, ...» — chaqiruv so'zlari tashlanadi (brauzer ham olib tashlaydi, lekin matn yozib yuborilganda qoladi)"""
    return _WAKE_RE.sub("", text_loose, count=1).strip()


def detect_intent(t):
    """t — loose() matn. Natija: intent nomi yoki None"""
    words = t.split()
    n = len(words)

    if not t:
        return "wake"
    # "bir kilo", "uch kun" dagi yolg'iz son so'zi summa hisoblanmaydi — raqam, ming/million yoki valyuta kerak
    has_amount = any(a["strong"] for a in find_amounts(words))
    # Oxirgi amalni tuzatish ("yo'q, 50 ming edi") — "yo'q" bilan boshlangani uchun bekor qilishdan oldin tekshiriladi
    # "kecha 100 ming ketgan edi" — oddiy o'tgan zamon (yangi chiqim), tuzatish emas: amal fe'li bo'lsa tuzatish deb olinmaydi
    action_verb = _has(t, r"sarf|ishlat|ketdi|ketgan|tolad|tolag|sotib|xarid|oldim|olgan|berdim|bergan|tushdi|tushgan|"
                          r"keldi|kelgan|otkazdim|yechd|qarz|potrat|kupil|zaplati|poluchil")
    if (_has(t, r"^(yoq|aslida|togrisi|xato|net)\b") and (has_amount or _has(t, r"\w+dan\b|\b(kecha|vchera)\b"))) or \
            (_has(t, _EDIT_WORDS) and (has_amount or _has(t, _EDIT_TARGETS)) and not action_verb
             and not _has(t, r"rejim|mavzu|til\b|tilni|parol")):
        return "edit_last"
    # Yangi hamyon ochish ("yangi hamyon och Humo", "Seyf degan hamyon yarat") — bo'lim ochishdan oldin
    if _has(t, r"\byangi\b.{0,25}\bhamyon|\bhamyon\w*\s+(qosh|yarat)|\bhamyon (ochib ber|och)\b|novi\w* koshel") and \
            not _has(t, r"hamyonlar|sahifa|bolim"):
        return "wallet_create"
    # Qisqa yopish / rad etish
    if n <= 4 and _has(t, r"^(toxta|toxtat|yop|yopil|xayr|boldi|kerak emas|kerakmas|yoq|stop|jim|bekor|bekor qil\w*|qoy|qoyaver)\b"):
        return "cancel"
    if _has(t, r"(oxirgi\w*|hozirgi\w*|xato\w*|adashib)\b.{0,30}\b(ochir|bekor|qaytar)|^(ortga|orqaga) qaytar|^(undo|otmena)$"):
        return "undo"

    # Suhbat
    if _has(t, r"eshit\w*(san|siz)\w*|eshityap|meni eshit|bormisan|bormisiz|shu yerdamisan|uyg[ao]qmisan"):
        return "chat_hear"
    if _has(t, r"^(salom|assalomu|assalom|hello|privet|qalesan|qalaysan|qalaysiz|yaxshimisan|yaxshimisiz)\b") and n <= 5:
        return "chat_hello"
    if _has(t, r"^(rahmat|raxmat|tashakkur|barakalla|zor|ofarin|yashavor|spasibo|thanks)\b") and n <= 5:
        return "chat_thanks"
    if _has(t, r"\b(kimsan|kimsiz|isming|ismingiz|sen kim|siz kim|oting nima)\b"):
        return "chat_who"
    if _has(t, r"nima(lar)? (qila olasan|qilasan|qila olasiz|qilolasan|bilasan)|nima qila olasan|qanday buyruq|yordam ber\b|imkoniyat"):
        return "chat_help"
    if _has(t, r"soat (necha|nechchi|qancha)|vaqt (necha|qancha)|soat nech"):
        return "chat_time"
    if _has(t, r"bugun (nechanchi|necha|qaysi kun|qanaqa kun)|sana (necha|qancha)|bugungi sana"):
        return "chat_date"

    question = _has(t, _QUESTION_RE)

    # Kun xulosasi va taqqoslash — savol shaklida bo'lmasa ham ("bugungi xulosa", "hisobot ber")
    if not has_amount and _has(t, r"xulosa|umumiy holat|ahvol|hisobot ber|nima boldi|svodka|itog"):
        return "query_summary"
    if not has_amount and _has(t, r"(otgan|oldingi) oy\w* (nisbatan|qaraganda|kora|bilan)|solishtir|kopaydimi|kamaydimi|sravni"):
        return "query_compare"
    if not has_amount and _has(t, r"eng kop|nimaga kop|qayerga kop|nimalarga ket|turkumlar boyicha|na chto bolshe|"
                                  r"eng katta (xarajat|harajat|chiqim)|qaysi turkum\w* kop|qayerga ket\w*"):
        return "query_top"

    # Ko'rinish
    if _has(t, r"(qorongi|qorongu|tungi|dark)\b.{0,15}(rejim|mavzu|qil|yoq|ot)|^(qorongi|tungi) rejim"):
        return "theme_dark"
    if _has(t, r"(yorug|kunduzgi|light)\b.{0,15}(rejim|mavzu|qil|yoq|ot)|^(yorug|kunduzgi) rejim"):
        return "theme_light"
    if _has(t, r"(balans|qoldi[qg])\w*.{0,15}(yashir|berkit|yop)"):
        return "balance_hide"
    if _has(t, r"(balans|qoldi[qg])\w*.{0,15}(korinsin|ochib qoy|ochib qo|yashirma)"):
        return "balance_show"

    # Bo'limlarni ochish
    if not has_amount and _has(t, r"\b(och|ochib|ochgin|ochin|korsat\w*|kir|kirgin|ot|otgin|sahifa\w*|bolim\w*)\b"):
        if _has(t, r"statist|hisobot"):
            return "nav_stats"
        if _has(t, r"\bqarz"):
            return "nav_debts"
        if _has(t, r"\b(kirim|daromad)"):
            return "nav_incomes"
        if _has(t, r"\b(chiqim|xarajat|harajat)"):
            return "nav_expenses"
        if _has(t, r"\bhamyon"):
            return "nav_wallets"
        if _has(t, r"\b(kurs|valyuta)"):
            return "nav_rates"
        if _has(t, r"\bsozlama"):
            return "nav_settings"
        if _has(t, r"malumotnoma|qollanma"):
            return "nav_help"
        if _has(t, r"bosh sahifa|asosiy sahifa|\buy(ga)?\b"):
            return "nav_home"

    # Savollar (summa so'ralmasa)
    if question and not _has(t, r"\b(berdim|oldim|toladim|sarfladim|qosh|yoz|otkaz\w*)\b") or (question and not has_amount):
        if _has(t, r"\bkurs|(dollar|yevro|evro|rubl|tenge|lira|yuan|funt|dirham)\w* (qancha|necha|nechpul|kursi)"):
            return "query_rate"
        if _has(t, r"maqsad|jamgarma|tsel"):
            return "query_goals"
        if _has(t, r"doimiy|takroriy|keyingi tolov|tolovlar\w*|qachon tola|obuna|ijara qachon|platezh"):
            return "query_recurring"
        if _has(t, r"\bqarz|\bdolg"):
            return "query_debts"
        if _has(t, r"eng kop|nimaga kop|qayerga kop|nimalarga|turkumlar boyicha|na chto bolshe|turkum\w* kop"):
            return "query_top"
        if _has(t, rf"sarf|ishlat|xarajat|harajat|chiqim|ketdi|ketgan|ketibdi|{_RU_EXPENSE}"):
            return "query_spent"
        if _has(t, rf"kirim|daromad|tushdi|tushgan|topdim|ishlab topdim|oylik|{_RU_INCOME}"):
            return "query_income"
        if _has(t, r"balans|qoldiq|qoldig|pulim|mablag|qancha pul|qancha qoldi|qolgan|\bqoldi\b|hisob(im|imda|da)\b|"
                   r"hamyon\w*\s*(da|ida)?\s*qancha|qancha bor|\bpul bor|ostat|deneg"):
            return "query_balance"
    if not has_amount and _has(t, r"^(balans\w*|balansim\w*|qoldiq\w*|qoldig\w*|pulim qancha|mablagim)\b|^umumiy (qoldiq|balans)"):
        return "query_balance"
    if not has_amount and _has(t, r"^(qarzlar\w*|qarzlarim\w*)$|^qarzlar\w* royxat"):
        return "query_debts"
    # Ro'yxat so'rash — fe'lsiz ot ("bugungi xarajatlarim", "bu oylik kirimlarim"): yangi amal emas, savol
    if not has_amount and n <= 4 and not _has(t, r"\b(qosh|yoz|kirit|ochir|bekor|qil)\w*"):
        if _has(t, r"\b(xarajat|harajat|chiqim)lar"):
            return "query_spent"
        if _has(t, r"\b(kirim|daromad)lar"):
            return "query_income"
        if _has(t, r"\bmaqsad\w*|\bjamgarma\w*"):
            return "query_goals"
        if _has(t, r"doimiy tolov|tolovlar\w*|obunalar\w*"):
            return "query_recurring"
        if _has(t, r"\bkurs\w*|valyuta\w*"):
            return "query_rate"

    # Amallar
    if (_has(t, r"\bqarz") and _has(t, r"qaytar|uzd|uzib|tolad|toladi|berib qoydi|qaytib")) or \
            _has(t, r"\bdolg") and _has(t, r"vernul|otdal|pogasil"):
        return "debt_repay"
    if _has(t, r"\bqarz\w*\s*(ber|beribman|bergan)|\bqarz\w* \w+ ?berdim|qarzga ber|dal v dolg|odoljil|odolzhil"):
        return "debt_give"
    if _has(t, r"\bqarz\w*\s*(ol|oldim|olibman|bol|boldim|olgan)|qarzga ol|qarzdor boldim|vzyal v dolg|zanyal"):
        return "debt_take"
    if _has(t, r"maqsad|jamgarma|jamgar") and _has(t, r"qosh|sol|otkaz|yig|tashla|ajrat"):
        return "goal_fund"
    if _has(t, r"\bhar (kuni|hafta|haftada|oy|oyda|yil|yilda)\b") and has_amount:
        return "recurring"
    if _has(t, r"otkaz|yechd|yechib|naqdlashtir|almashtird|ayirbosh|konvert|\bsol(dim|ib qoydim)\b|perevel|perevedi|perevod|snyal"):
        return "transfer"
    if _has(t, r"\b(kirim|daromad)\b.{0,20}\b(qosh|yoz|kirit|qil)|\b(qosh|yoz)\w* (kirim|daromad)"):
        return "income"
    if _has(t, r"\b(chiqim|xarajat|harajat)\b.{0,20}\b(qosh|yoz|kirit|qil)|\b(qosh|yoz)\w* (chiqim|xarajat|harajat)"):
        return "expense"
    if _has(t, rf"sotib|xarid|sarf|ishlatd|ketdi|ketkazd|toladim|tolab|tolov|xarajat|harajat|chiqim|uzatdim|\bberdim\b|\bberib\b|olib berdim|kupit|quyd|zapravka|{_RU_EXPENSE}"):
        return "expense"
    if _has(t, r"tushdi|tushgan|tushib|keldi|kelib tushdi|kirim|daromad|oylik|maosh|ish haqi|ishhaqi|zarplata|avans|"
                rf"bonus|mukofot|premiya|topdim|ishladim|ishlab topdim|qoshildi|hadya|sovga oldim|dividend|{_RU_INCOME}"):
        return "income"
    if _has(t, r"\boldim\b"):
        # "non oldim 5 ming" — sotib oldim; "Akmaldan 100 ming oldim" — kimdandir pul oldim (daromad)
        return "income" if _has(t, r"\w+dan \d|\w+dan (bir|ikki|uch|tort|besh|olti|yetti|sakkiz|toqqiz|on|yigirma|ottiz|qirq|ellik|yuz)") else "expense"
    if has_amount:
        # "tushlikka 45 ming" — nimagadir sarflandi; "kartaga 45 ming" esa hamyon, uni kirim ham bo'lishi mumkin
        wallet_words = tuple(loose(w) for _, ws in WALLET_HINTS for w in ws) + ("hamyon",)
        if any(re.fullmatch(r"\w+(ga|ka|qa)", w) and not w.startswith(wallet_words) and not _num_token(w) for w in words):
            return "expense"
        return "ask_kind"
    return None


# ---------- Hamyon, toifa, odam so'zlari ----------

# Toifa nomidagi so'z -> gapda uchrashi mumkin bo'lgan so'zlar (o'zak, loose ko'rinishda)
CATEGORY_HINTS = [
    (r"oziq|ovqat|bozor", ["ovqat", "tushlik", "nonushta", "kechki ovqat", "non", "gosht", "bozor", "oziq", "restoran",
                          "kafe", "choyxona", "osh", "somsa", "lavash", "shashlik", "pizza", "burger", "magazin", "dokon",
                          "supermarket", "makro", "korzinka", "havas", "meva", "sabzavot", "sut", "tuxum", "un ", "guruch",
                          "yog", "shakar", "choy", "kofe", "suv ichdim", "ichimlik", "produkt", "obed", "fastfud", "taom",
                          "ujin", "zavtrak", "eda", "produkti", "kushat"]),
    (r"transport|yol", ["taksi", "taxi", "yandex", "avtobus", "metro", "benzin", "yoqilgi", "metan", "propan", "gaz quy",
                        "zapravka", "transport", "yol kira", "yolkira", "poyezd", "samolyot", "avia", "bilet", "marshrut",
                        "damas", "moshina", "mashina", "avtomobil", "parkovka", "moyka", "remont mashina", "shina",
                        "proezd", "bilet"]),
    (r"uy|kommunal|ijara", ["svet", "elektr", "gaz", "suv puli", "kommunal", "ijara", "kvartira", "uy puli", "musor",
                            "chiqindi", "issiqlik", "otoplenie", "remont", "internet", "telefon", "aloqa", "paynet", "mobil",
                            "uydagi", "mebel", "texnika"]),
    (r"kiyim", ["kiyim", "oyoq kiyim", "poyabzal", "tufli", "krossovka", "koylak", "shim", "kurtka", "palto", "futbolka",
                "kostyum", "libos", "sumka", "kepka", "paypoq"]),
    (r"kongil|dam", ["kino", "teatr", "oyin", "konsert", "dam olish", "sayohat", "safar", "otdix", "park", "muzey",
                     "bowling", "sport zal", "obuna", "netflix", "spotify", "kafe dam"]),
    (r"salomat|dori|sogliq", ["dori", "apteka", "dorixona", "shifokor", "doktor", "vrach", "kasalxona", "klinika",
                             "poliklinika", "tish", "stomatolog", "analiz", "massaj", "davolan"]),
    (r"talim|kitob|oqish", ["kurs", "kitob", "oqish", "kontrakt", "maktab", "universitet", "institut", "repetitor",
                            "dars", "talim", "bogcha", "daftar", "ruchka", "trening"]),
    (r"kutilmagan|boshqa", ["kutilmagan", "boshqa", "har xil", "turli"]),
    # Daromad toifalari
    (r"maosh|oylik|ish haqi", ["oylik", "maosh", "ish haqi", "ishhaqi", "zarplata", "avans", "oyligim", "maoshim",
                              "ishdan", "bonus", "premiya", "mukofot"]),
    (r"qoshimcha|frilans|freelance", ["qoshimcha ish", "frilans", "freelance", "buyurtma", "zakaz", "proyekt",
                                     "loyiha", "mijoz", "halturka", "subbotnik", "kechki ish"]),
    (r"sovga|yordam", ["sovga", "hadya", "yordam", "tuhfa", "toyona", "pul berishdi", "dadam", "oyim", "onam", "otam",
                       "akam", "opam", "ukam", "singlim", "buvim", "bobom"]),
    (r"dividend|foiz|aksiya", ["dividend", "foiz", "aksiya", "depozit", "vklad", "keshbek", "cashback"]),
]

_FALLBACK_CATEGORY_RE = r"kutilmagan|boshqa|other|prochee|turli"

# Hamyon nomidagi so'z -> gapda shu hamyonni bildiradigan so'zlar
WALLET_HINTS = [
    (r"naqd|naxt|nalich|cash|naqt", ["naqd", "naqt", "naxt", "nalichka", "nalichniy", "nal", "cash", "qolda", "chontak",
                                     "cho'ntak", "nalichnimi", "nalichnie", "nalichkoy"]),
    (r"karta|card|plastik|humo|uzcard|visa|master|bank", ["karta", "kartochka", "kartam", "plastik", "kartadagi",
                                                         "karti", "kartoy", "karte", "kartu"]),
    (r"humo", ["humo", "xumo"]),
    (r"uzcard|uzkard", ["uzcard", "uzkard", "uzkart"]),
    (r"visa", ["visa", "viza"]),
    (r"master", ["master", "mastercard"]),
    (r"seyf|sejf", ["seyf", "sejf"]),
    (r"dollar|usd|\$", ["dollar", "dollarli", "dollarlik"]),
    (r"jamgarma|zaxira|nakopl", ["jamgarma", "zaxira", "nakopitel"]),
]

_GENERIC_WALLET_WORDS = {"hamyon", "hamyoni", "asosiy", "mening", "pul", "pullar", "uzs", "som", "the", "and"}
_CASE_SUFFIX_RE = re.compile(r"(dagi|dan|idan|ga|ka|qa|iga|da|ida|ni|ini|ning|im|imdan|imga|imda|imni|lar|larim)$")


def alias_forms(name, hints):
    """Yozuv nomidan solishtirish uchun so'zlar: nomning o'zi va so'zlari + mos ma'nodosh so'zlar"""
    name_l = loose(name)
    forms = set()
    if len(name_l) >= 2:
        forms.add(name_l)
    for word in re.split(r"[\s|/()\-]+", name_l):
        if len(word) >= 3 and word not in _GENERIC_WALLET_WORDS:
            forms.add(word)
    for pattern, words in hints:
        if re.search(pattern, name_l):
            forms.update(loose(w) for w in words)
    return {f for f in forms if f}


def mentions(text_loose, forms):
    """forms dagi so'zlar gapda qayerda uchraydi: [(so'z indeksi, qo'shimcha)] — "naqddan" -> (3, "dan")"""
    words = text_loose.split()
    result = []
    for form in sorted(forms, key=len, reverse=True):
        form_words = form.split()
        k = len(form_words)
        for i in range(len(words) - k + 1):
            chunk = words[i:i + k]
            if chunk[:-1] != form_words[:-1]:
                continue
            last, target = chunk[-1], form_words[-1]
            if last == target:
                result.append((i, ""))
            elif last.startswith(target) and len(target) >= 3:
                suffix = last[len(target):]
                if len(suffix) <= 6 and _CASE_SUFFIX_RE.fullmatch(suffix) or suffix in ("i", "si", "im", "dagi", "da"):
                    result.append((i, suffix))
    return result


# "s karti" (kartadan), "na kartu" (kartaga) — ruscha gapda rol qo'shimchada emas, oldingi so'zda
_FROM_PREPS = {"s", "so", "iz"}
_TO_PREPS = {"na", "v", "vo"}


def role_by_preposition(words, pos):
    prev = words[pos - 1] if pos > 0 else ""
    if prev in _FROM_PREPS:
        return "from"
    if prev in _TO_PREPS:
        return "to"
    return None


# Bir gapda bir nechta buyruq: "tushlikka 45 ming, taksiga 20 ming sarfladim", "oylik 5 million va bonus 1 million tushdi"
_SPLIT_RE = re.compile(r"\s*(?:[,;]|\bva\b|\bhamda\b|\bkeyin\b|\byana\b|\bi\b|\ba takje\b)\s*")


def split_segments(norm):
    """Gapni bo'laklarga ajratadi (ajratgich bo'lmasa — bitta bo'lak). Raqamlar ichidagi vergul ("1,5 million")
    ajratgich emas"""
    protected = re.sub(r"(\d),(\d)", r"\1§\2", norm)
    parts = [p.replace("§", ",").strip() for p in _SPLIT_RE.split(protected)]
    return [p for p in parts if p]


# Izohdan tashlanadigan so'zlar: fe'llar, to'ldiruvchilar, sanalar. Qolgani — "nimaga" ("tushlikka" -> "Tushlik")
_ITEM_DROP = re.compile(
    r"^(sarf\w*|ishlat\w*|ketdi|ketgan|ketibdi|ketkazdim|toladim|tolab|toladik|tolandi|sotib|oldim|olib|berdim|berib|"
    r"xarid\w*|qildim|qilindi|tushdi|tushgan|tushib|keldi|kelib|yozib|yoz|qosh\w*|kirit\w*|chiqim|kirim|xarajat\w*|"
    r"harajat\w*|daromad|bilan|pul\w*|som|sum|bugun|kecha|ertaga|indinga|hozir|uzatdim|otkaz\w*|yechdim|"
    r"potratil\w*|zaplatil\w*|kupil\w*|oplatil\w*|poluchil\w*|perevel|na|za|v|s|iz|segodnya|vchera|"
    r"har|kuni|hafta\w*|oy|oyda|yil\w*|sana\w*|men|ham|edi|deb|degan|ga)$")


def item_phrase(norm, skip_prefixes=()):
    """Izoh uchun qisqa ibora: "tushlikka 45 ming naqddan sarfladim" -> "Tushlik". skip_prefixes — hamyon nomlari"""
    kept = []
    for word in norm.split():
        bare = word.strip(".,!?«»\"")
        low = bare.lower().replace("'", "")
        if not low or _num_token(low) or low in _CURRENCY_BY_WORD or _ITEM_DROP.match(low) or re.search(r"\d", low):
            continue
        if any(m in low for m in MONTHS):
            continue
        if skip_prefixes and low.startswith(tuple(skip_prefixes)):
            continue
        kept.append(bare)
    while kept and kept[-1].lower() == "uchun":  # "tushlik uchun 45 ming" -> "Tushlik", lekin "Akmal uchun sovg'a" qoladi
        kept.pop()
    if not kept:
        return ""
    # Birinchi so'zdagi yo'nalish qo'shimchasi: "tushlikka" -> "tushlik", "taksiga" -> "taksi", "bozorga" -> "bozor"
    first = kept[0]
    for suffix, cut in (("kka", 2), ("qqa", 2), ("ga", 2), ("ka", 2), ("qa", 2)):
        if first.lower().endswith(suffix) and len(first) - cut >= 3:
            first = first[:-cut]
            break
    kept[0] = first
    phrase = " ".join(kept[:6])
    return (phrase[:1].upper() + phrase[1:])[:255]


def role_of(suffix):
    if suffix.endswith("dan"):
        return "from"
    if re.search(r"(ga|ka|qa)$", suffix):
        return "to"
    return None


_PERSON_STOP = {"qarz", "qarzga", "qarzim", "qarzimni", "qarzini", "men", "menga", "mendan", "unga", "undan", "bugun",
                "kecha", "ertaga", "pul", "pulni", "ming", "million", "som", "dollar", "berdim", "oldim", "hamyon",
                "hamyondan", "hamyonga", "karta", "kartadan", "kartaga", "naqd", "naqddan", "naqdga", "uchun", "va",
                "oyga", "kunga", "haftaga", "yilga", "muddat", "muddatga", "gacha"}


def find_person(text_norm, debt_kind):
    """Qarz kimga berildi / kimdan olindi: "Akmalga qarz berdim" -> "Akmal". text_norm — normalize() matni"""
    words = [w.strip(".,?") for w in text_norm.split()]
    wanted = ("ga", "ka", "qa") if debt_kind == "give" else ("dan",)
    if debt_kind == "repay":
        wanted = ("ga", "ka", "qa", "dan", "ning", "ni")
    for w in words:
        lw = w.replace("'", "")
        if lw in _PERSON_STOP or _num_token(lw) or lw in _CURRENCY_BY_WORD:
            continue
        for suf in sorted(wanted, key=len, reverse=True):
            if lw.endswith(suf) and len(lw) - len(suf) >= 2:
                base = w[: len(w) - len(suf)]
                if lw.endswith("ning") and suf == "ni":
                    continue
                if base.replace("'", "") in _PERSON_STOP:
                    continue
                return base[:1].upper() + base[1:]
    # "qarzini qaytardi Akmal" / "Akmal qarzini qaytardi" — egalik qo'shimchasi qarzda
    if debt_kind == "repay":
        for i, w in enumerate(words):
            if w.replace("'", "").startswith("qarz") and i > 0:
                base = words[i - 1]
                if base.replace("'", "") not in _PERSON_STOP and not _num_token(base):
                    return base[:1].upper() + base[1:]
    return None


def clean_person_answer(text_norm):
    """«Kimga?» savoliga javob: "Akmalga" -> "Akmal", "akam Botirga" -> "Akam Botir" """
    words = [w.strip(".,?") for w in text_norm.split() if w.strip(".,?")]
    if not words or len(words) > 4:
        return None
    last = words[-1]
    words[-1] = re.sub(r"(ga|ka|qa|dan|ning)$", "", last) or last
    name = " ".join(words)
    return name[:1].upper() + name[1:] if len(name) >= 2 else None


_ORDINALS = {"birinchi": 0, "1": 0, "bir": 0, "ikkinchi": 1, "2": 1, "ikki": 1, "uchinchi": 2, "3": 2, "uch": 2,
             "tortinchi": 3, "4": 3, "tort": 3, "beshinchi": 4, "5": 4, "besh": 4}


def ordinal_choice(text_loose):
    """«Birinchisi», «ikkinchisidan» — taklif qilingan ro'yxatdan tanlash"""
    for w in text_loose.split():
        base = re.sub(r"(si|sidan|siga|sini|dan|ga)$", "", w)
        if base in _ORDINALS and (base.endswith("inchi") or w != base or len(text_loose.split()) == 1):
            return _ORDINALS[base]
    return None


_FREQ_RE = [(r"\bhar kun", "daily"), (r"\bhar hafta", "weekly"), (r"\bhar oy", "monthly"), (r"\bhar yil", "yearly")]


def find_frequency(text_loose):
    for pattern, freq in _FREQ_RE:
        if re.search(pattern, text_loose):
            return freq
    return None


# ---------- Ovozda o'qish uchun sonlar so'z bilan ----------

_SAY_UNITS = ["", "bir", "ikki", "uch", "to'rt", "besh", "olti", "yetti", "sakkiz", "to'qqiz"]
_SAY_TENS = ["", "o'n", "yigirma", "o'ttiz", "qirq", "ellik", "oltmish", "yetmish", "sakson", "to'qson"]


def _say_hundreds(n):
    parts = []
    h, rest = divmod(n, 100)
    if h:
        # 100 — "yuz", 122 — "bir yuz yigirma ikki" (katta sonlarda shunday ravonroq: "bir yuz yigirma ikki million")
        parts.append("yuz" if h == 1 and not rest else f"{_SAY_UNITS[h]} yuz")
    t, u = divmod(rest, 10)
    if t:
        parts.append(_SAY_TENS[t])
    if u:
        parts.append(_SAY_UNITS[u])
    return " ".join(parts)


# Shundan katta sonlarda xona guruhlari (milliard, million, ming) orasida vergul — ovoz nafas olgandek to'xtaydi:
# "bir yuz yigirma ikki million, to'qqiz yuz to'qqiz ming, uch yuz oltmish yetti". Kichiklari ("bir ming besh yuz")
# pauzasiz ravonroq
PAUSE_FROM = 10 ** 6


def number_words(value, pause=True):
    """1250000 -> "bir million, ikki yuz ellik ming". Ovoz sintezatori o'zbekcha raqamlarni o'qiy olmasligi mumkin"""
    n = int(value)
    if n == 0:
        return "nol"
    joiner = ", " if pause and n >= PAUSE_FROM else " "
    parts = []
    for size, name in ((10 ** 9, "milliard"), (10 ** 6, "million"), (1000, "ming")):
        chunk, n = divmod(n, size)
        if chunk:
            parts.append(f"{_say_hundreds(chunk) if chunk > 1 or size > 1000 else 'bir'} {name}".strip())
    if n:
        parts.append(_say_hundreds(n))
    return joiner.join(parts)


_ORDINAL_VOWEL_END = ("i", "a")


def ordinal_words(value):
    """29 -> "yigirma to'qqizinchi", 2 -> "ikkinchi" (unli bilan tugasa -nchi, aks holda -inchi)"""
    words = number_words(value, pause=False)
    return words + ("nchi" if words.endswith(_ORDINAL_VOWEL_END) else "inchi")


_MONTH_SHORT = {"yan": "yanvar", "fev": "fevral", "mar": "mart", "apr": "aprel", "may": "may", "iyn": "iyun",
                "iyl": "iyul", "avg": "avgust", "sen": "sentabr", "okt": "oktabr", "noy": "noyabr", "dek": "dekabr"}
# 122 909 367 · 1,234,567 · 1.500.000 (xonalar bo'sh joy, vergul yoki nuqta bilan) va 1,5 · 2.75 (o'nli kasr)
_SEP = "[ \u00a0\u202f\u2009,.]"
_NUMBER_RE = re.compile(rf"(?<![\w.,])([−\-–]\s?)?(\d{{1,3}}(?:{_SEP}\d{{3}})+|\d+)(?:[.,](\d{{1,2}}))?(?![\d\w])")
_ORDINAL_RE = re.compile(r"(?<![\w])(\d{1,4})-(?=[^\W\d]|$)")
_TIME_RE = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")
_FRACTION_PLACES = {1: "o'ndan", 2: "yuzdan"}
# Pul: "12 650,45 so'm" -> "... so'm qirq besh tiyin" (kasr — tiyin/sent, "butun yuzdan" emas)
_MONEY_WORDS = {"uzs": "UZS", "so'm": "UZS", "som": "UZS", "usd": "USD", "dollar": "USD", "eur": "EUR", "yevro": "EUR",
                "rub": "RUB", "rubl": "RUB"}
_MONEY_RE = re.compile(rf"(\d{{1,3}}(?:{_SEP}\d{{3}})+|\d+)[.,](\d{{1,2}})\s*({'|'.join(_MONEY_WORDS)})\b",
                       re.IGNORECASE)


def _say_money_match(m):
    code = _MONEY_WORDS[m.group(3).lower()]
    cents = int(m.group(2).ljust(2, "0"))
    words = f"{number_words(int(re.sub(r'[^0-9]', '', m.group(1))))} {CURRENCY_SAY[code]}"
    return words + (f", {number_words(cents)} {_CENTS_SAY.get(code, 'sent')}" if cents else "")


def _say_number_match(m):
    sign, whole, frac = m.group(1), re.sub(r"\D", "", m.group(2)), m.group(3)
    words = number_words(int(whole))
    if frac and int(frac):
        words += f" butun {_FRACTION_PLACES[len(frac)]} {number_words(int(frac))}"
    return ("minus " if sign else "") + words


def spell_numbers(text):
    """Ovozda o'qish uchun: raqamlar o'zbekcha so'z bilan. Ovoz sintezatorlari raqamni o'zicha o'qib, xato qiladi
    ("bir yuzi yigirma ikki"). "122 909 367 UZS" -> "bir yuz yigirma ikki million ... so'm", "29-okt" ->
    "yigirma to'qqizinchi oktabr", "15%" -> "o'n besh foiz", "14:30" -> "o'n to'rt o'ttiz", "1,5" -> "bir butun o'ndan besh"
    """
    text = str(text or "")
    text = _TIME_RE.sub(lambda m: f"{number_words(int(m.group(1)))} {number_words(int(m.group(2)))}"
                        if int(m.group(2)) else f"{number_words(int(m.group(1)))}", text)

    def ordinal(m):
        return ordinal_words(int(m.group(1))) + " "
    text = _ORDINAL_RE.sub(ordinal, text)
    text = re.sub(r"\b(" + "|".join(_MONTH_SHORT) + r")\b\.?", lambda m: _MONTH_SHORT[m.group(1).lower()], text,
                  flags=re.IGNORECASE)
    text = re.sub(r"(\d)\s*%", r"\1 foiz", text)
    text = _MONEY_RE.sub(_say_money_match, text)
    text = re.sub(r"(?<![\w])\+\s?(?=\d)", "plyus ", text)
    text = _NUMBER_RE.sub(_say_number_match, text)
    text = re.sub(r"\b(" + "|".join(CURRENCY_SAY) + r")\b", lambda m: CURRENCY_SAY[m.group(1)], text)
    return " ".join(text.split())


CURRENCY_SAY = {"UZS": "so'm", "USD": "dollar", "EUR": "yevro", "RUB": "rubl", "KZT": "tenge", "GBP": "funt sterling",
                "CNY": "yuan", "TRY": "lira", "AED": "dirham", "KRW": "von", "JPY": "iyena", "CHF": "frank"}
_CENTS_SAY = {"UZS": "tiyin", "USD": "sent", "EUR": "sent", "RUB": "kopeyka"}


def say_money(amount, currency):
    amount = Decimal(amount)
    whole = int(amount)
    cents = int((amount - whole) * 100)
    text = f"{number_words(whole)} {CURRENCY_SAY.get(currency, currency)}"
    if cents:
        text += f", {number_words(cents)} {_CENTS_SAY.get(currency, 'sent')}"
    return text


def today_local():
    from django.utils import timezone
    return timezone.localdate()
