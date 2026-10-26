"""Bepul Moliya yordamchisi: savolga assistant_knowledge.md (Ma'lumotnoma nusxasi) dan eng mos javobni topadi.
Tashqi xizmat yo'q — kalit so'zlar bo'yicha qidiruv: so'zlar qo'shimchasiz solishtiriladi ("hamyonni" = "hamyon"),
kam uchraydigan so'z (masalan "qarz") ko'p uchraydiganidan ("qanday") og'irroq hisoblanadi (IDF).
Cheklovi: savol ma'nosini tushunmaydi — ma'lumotnomada yo'q mavzuga javob topa olmaydi"""
import math
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

# Shunchalik ball to'planmasa javob "topilmadi" hisoblanadi (bitta o'rtacha muhim so'z savolda uchrashi kifoya)
MIN_SCORE = 1.2

NOT_FOUND_MESSAGE = ("Bu savolga ma'lumotnomadan javob topa olmadim. Savolni boshqacha yozib ko'ring "
                     "yoki «Yordam» bo'limida adminga yozing — u shaxsan javob beradi.")
GREETING_MESSAGE = "Salom! Men Moliya yordamchisiman. Ilovadan foydalanish bo'yicha savolingizni yozing."
THANKS_MESSAGE = "Arzimaydi! Yana savol bo'lsa, yozavering."

GREETINGS = {"salom", "assalomu", "alaykum", "assalom", "hello", "hi", "privet", "salam"}
THANKS = {"rahmat", "raxmat", "tashakkur", "spasibo", "thanks", "thank"}

# Savolning ma'nosiga ta'sir qilmaydigan so'zlar (so'roq so'zlari, olmoshlar, yordamchi fe'llar)
STOPWORDS = {
    "qanday", "qanaqa", "qilib", "qilaman", "qilsam", "qilsa", "qilish", "qilay", "qilamiz", "nima", "nimaga", "nega",
    "qayerda", "qayerdan", "qayerga", "qachon", "qaysi", "nechta", "qancha", "men", "menga", "mening", "meni", "mendan",
    "siz", "sizga", "biz", "bu", "shu", "u", "unga", "uni", "va", "yoki", "bilan", "uchun", "mumkin", "bo'ladimi",
    "bo'ladi", "bo'lsa", "bo'lmaydi", "bo'lyapti", "kerak", "bormi", "yo'qmi", "ham", "edi", "emas", "chi", "mi",
    "iltimos", "ayting", "aytib", "bering", "bersangiz", "ber", "yordam", "kerakmi", "agar", "endi", "hozir",
    "ilova", "ilovada", "ilovani", "dastur", "dasturda", "da", "ga", "ni", "dan", "lar", "ekan", "nimadir",
}

# Bir ma'nodagi so'zlar ma'lumotnomadagi atamaga keltiriladi
SYNONYMS = {
    "chiqim": "harajat", "xarajat": "harajat", "xarajatlar": "harajat", "sarf": "harajat", "rasxod": "harajat",
    "daromad": "kirim", "dohod": "kirim", "maosh": "kirim", "oylik": "kirim",
    "karta": "hamyon", "kartam": "hamyon", "koshelek": "hamyon", "hisob": "hamyon", "schyot": "hamyon",
    "kategoriya": "toifa", "kategoriyalar": "toifa",
    "kurs": "valyuta", "dollar": "valyuta", "usd": "valyuta", "so'm": "valyuta",
    "parolni": "parol", "login": "kirish", "akkount": "akkaunt", "akkauntni": "akkaunt", "profilni": "profil",
    "delete": "o'chir", "udalit": "o'chir", "tahrir": "o'zgartir", "tahrirlash": "o'zgartir", "tuzat": "o'zgartir",
    "almashtir": "o'zgartir", "yangila": "o'zgartir",
    "tema": "rang", "dizayn": "rang", "tun": "qorong'u", "dark": "qorong'u",
}

# O'zbek kirill yozuvi lotinga (foydalanuvchi kirillcha yozsa ham topilsin)
CYRILLIC = str.maketrans({
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "j", "з": "z", "и": "i", "й": "y",
    "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f",
    "х": "x", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "'", "ь": "", "ы": "i", "э": "e", "ю": "yu", "я": "ya",
    "ў": "o'", "қ": "q", "ғ": "g'", "ҳ": "h",
})
APOSTROPHES = re.compile(r"[ʻʼ’‘`´]")
WORD = re.compile(r"[a-z0-9']+")


@dataclass
class Entry:
    topic: str
    question: str
    answer: str
    t_tokens: list  # mavzu nomi
    q_tokens: list
    a_tokens: list


# Ko'p uchraydigan qo'shimchalar (uzunidan qisqasiga): "hamyonlarimni" → "hamyon", "o'chiraman" → "o'chir"
SUFFIXES = sorted({
    "larimizni", "laringizni", "larimni", "larini", "lardan", "larga", "larda", "larni", "lari", "lar",
    "imizni", "ingizni", "imizga", "ingizga", "imni", "imga", "imda", "imiz", "ingiz", "ning", "dagi", "dan",
    "ni", "ga", "da",
    "yapman", "yapti", "moqchiman", "moqchi", "ilgan", "gan", "aman", "amiz", "asiz", "adi", "ish", "sam", "sak",
}, key=len, reverse=True)
# "i", "im", "ta", "si" kabi qisqa qo'shimchalar ataylab yo'q: "kirim" → "kir", "karta" → "kar" bo'lib qolardi.
# Ular qoldirgan farqni similarity() umumiy bosh bo'yicha yopadi ("tilini" ~ "til")


def stem(word):
    """Qo'shimchalarni ketma-ket olib tashlaydi, o'zak kamida 3 harf qoladi. Aniq grammatik tahlil emas —
    faqat bir so'zning turli shakllari bir xil o'zakka kelishi uchun"""
    changed = True
    while changed:
        # Sinonim lug'atidagi shaklga yetilsa to'xtaydi: "chiqimni" → "chiqim" (→ harajat), "chiq" gacha qisqarmaydi
        if word in SYNONYMS:
            return SYNONYMS[word]
        for suffix in SUFFIXES:
            if word.endswith(suffix) and word[:-len(suffix)] in SYNONYMS:
                return SYNONYMS[word[:-len(suffix)]]
        changed = False
        for suffix in SUFFIXES:
            if word.endswith(suffix) and len(word) - len(suffix) >= 3:
                word = word[:-len(suffix)].rstrip("'")
                changed = True
                break
    return word


def tokens(text):
    text = APOSTROPHES.sub("'", text.lower()).translate(CYRILLIC)
    words = (w.strip("'") for w in WORD.findall(text))
    result = []
    for w in words:
        if len(w) < 2 or w in STOPWORDS:
            continue
        w = stem(w)
        result.append(SYNONYMS.get(w, w))
    return result


def similarity(a, b):
    """1 — bir xil so'z; qo'shimchasi farq qilsa (hamyon / hamyonni, o'chiraman / o'chirsam) — umumiy boshi ulushi.
    O'zbek tilida qo'shimchalar so'z oxiriga qo'shiladi, shuning uchun umumiy bosh — o'zak"""
    if a == b:
        return 1.0
    short = min(len(a), len(b))
    if short < 3:
        return 0.0
    common = 0
    for x, y in zip(a, b):
        if x != y:
            break
        common += 1
    if common < max(3, short - 2):
        return 0.0
    return common / max(len(a), len(b))


def best_match(word, words):
    return max((similarity(word, w) for w in words), default=0.0)


@lru_cache(maxsize=1)
def entries():
    text = Path(__file__).with_name("assistant_knowledge.md").read_text(encoding="utf-8")
    result, topic = [], ""
    for block in re.split(r"\n\s*\n(?=S: |## )", text):
        block = block.strip()
        if block.startswith("## "):
            topic, _, block = block[3:].partition("\n")
            topic, block = topic.strip(), block.strip()
        if not block.startswith("S: ") or "\nJ: " not in block:
            continue
        question, answer = block[3:].split("\nJ: ", 1)
        result.append(Entry(topic, question.strip(), answer.strip(),
                            tokens(topic), tokens(question), tokens(answer)))
    return result


@lru_cache(maxsize=1)
def idf():
    """Har so'z nechta yozuvda uchraydi: kam uchraydigani muhimroq"""
    docs = entries()
    counts = {}
    for e in docs:
        for w in set(e.t_tokens + e.q_tokens + e.a_tokens):
            counts[w] = counts.get(w, 0) + 1
    return {w: math.log(1 + len(docs) / c) for w, c in counts.items()}


def word_weight(word, weights):
    if word in weights:
        return weights[word]
    # Ma'lumotnomada aynan shu shakl yo'q — eng yaqin shaklining og'irligi
    close = [weights[w] for w in weights if similarity(word, w)]
    return max(close, default=0.0)


def score(entry, query, weights):
    """Savoldagi moslik — to'liq, mavzu nomidagi — 0.8 (bir mavzudagi savollar teng bo'lib qolmasin),
    javob matnidagi — 0.5. Oxirida: savol so'zlarining qanchasi so'ralgani (bir xil ballda qisqa, aniq savol yutadi)"""
    # Mavzusiz to'liq bo'lmagan savol ("Qanday qo'shaman?") faqat fe'l bo'yicha boshqa mavzu savollarini yutmasin
    q_weight, t_weight = (0.6, 1.0) if len(entry.q_tokens) <= 1 else (1.0, 0.8)
    total = 0.0
    for word in query:
        match = max(q_weight * best_match(word, entry.q_tokens), t_weight * best_match(word, entry.t_tokens),
                    0.5 * best_match(word, entry.a_tokens))
        total += match * word_weight(word, weights)
    if entry.q_tokens and total:
        covered = sum(1 for w in entry.q_tokens if best_match(w, query))
        total += 0.3 * covered / len(entry.q_tokens)
    return total


def answer(question):
    """Javob matnini qaytaradi"""
    raw = APOSTROPHES.sub("'", question.lower()).translate(CYRILLIC)
    raw_words = set(w.strip("'") for w in WORD.findall(raw))
    query = list(dict.fromkeys(tokens(question)))  # takrorlar olib tashlanadi, tartib saqlanadi

    if raw_words and raw_words <= GREETINGS | STOPWORDS:
        return GREETING_MESSAGE
    if raw_words & THANKS and len(query) <= 2:
        return THANKS_MESSAGE

    weights = idf()
    ranked = sorted(((score(e, query, weights), i) for i, e in enumerate(entries())), reverse=True)
    if not ranked or ranked[0][0] < MIN_SCORE:
        return NOT_FOUND_MESSAGE

    best = entries()[ranked[0][1]]
    # Mavzu nomi qisqa savolni tushunarli qiladi: "Qanday qo'shaman?" → "Takroriy to'lovlar: Qanday qo'shaman?"
    title = best.question if best.topic.lower().split()[0] in best.question.lower() else f"{best.topic}: {best.question}"
    return f"{title}\n\n{best.answer}"
