"""i18n/translations.js (yagona manba) dan har til uchun alohida lug'at yaratadi: static/js/i18n/<til>.js.

Nega: hamma tillar bitta faylda bo'lsa (~465 KB) o'zbekcha foydalanuvchi ham 6 tilning tarjimasini yuklardi.
Endi o'zbekchada lug'at umuman yuklanmaydi, boshqa tilda esa faqat o'sha tilning fayli (~70 KB) yuklanadi.

    python manage.py build_i18n          # fayllarni yaratadi / yangilaydi
    python manage.py build_i18n --check  # faqat tekshiradi: eskirgan bo'lsa xato (testlarda ishlatiladi)
"""
import json
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

# translations.js dagi ustunlar tartibi — i18n.js dagi COLS bilan bir xil
COLS = ["ru", "en", "tr", "kk", "ky", "tg"]

SOURCE = Path(settings.BASE_DIR) / "i18n" / "translations.js"
OUT_DIR = Path(settings.BASE_DIR) / "static" / "js" / "i18n"

HEADER = (
    "// AVTOMATIK YARATILGAN — qo'lda o'zgartirmang. Manba: i18n/translations.js, buyruq: python manage.py build_i18n\n"
)


def load_dict():
    """translations.js ni o'qiydi: izoh qatorlari tashlanadi, ortiqcha vergullar olinadi, qolgani JSON."""
    text = SOURCE.read_text(encoding="utf-8")
    start = text.index("{", text.index("DICT"))
    end = text.rindex("}")
    lines = [ln for ln in text[start:end + 1].split("\n") if not ln.strip().startswith("//")]
    body = re.sub(r",(\s*[}\]])", r"\1", "\n".join(lines))
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        raise CommandError(f"i18n/translations.js o'qilmadi ({e}). Kalit/matnlar qo'shtirnoqda bo'lishi kerak.")
    for key, row in data.items():
        if not isinstance(row, list) or len(row) != len(COLS):
            raise CommandError(f"{key!r}: {len(COLS)} ta tarjima bo'lishi kerak ({', '.join(COLS)})")
    return data


def render(data, col):
    rows = [
        f"{json.dumps(key, ensure_ascii=False)}:{json.dumps(row[col], ensure_ascii=False)}"
        for key, row in data.items() if row[col]
    ]
    # i18n.js lug'atni MOLIYA_I18N dan oladi; u allaqachon kutib turgan bo'lsa (lug'at kech kelgan) — darhol qo'llanadi
    return (
        HEADER
        + "window.MOLIYA_I18N={\n" + ",\n".join(rows) + "\n};\n"
        + "if (window.__moliyaI18nReady) window.__moliyaI18nReady();\n"
    )


def build_outputs():
    data = load_dict()
    return {OUT_DIR / f"{lang}.js": render(data, i) for i, lang in enumerate(COLS)}


class Command(BaseCommand):
    help = "i18n/translations.js dan har til uchun static/js/i18n/<til>.js lug'atini yaratadi"

    def add_arguments(self, parser):
        parser.add_argument("--check", action="store_true", help="Faqat tekshirish: fayllar eskirgan bo'lsa xato")

    def handle(self, *args, **opts):
        outputs = build_outputs()
        if opts["check"]:
            stale = [p.name for p, content in outputs.items()
                     if not p.exists() or p.read_text(encoding="utf-8") != content]
            if stale:
                raise CommandError(f"Eskirgan: {', '.join(stale)} — `python manage.py build_i18n` ni ishga tushiring")
            self.stdout.write("i18n lug'atlari yangi")
            return
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        for path, content in outputs.items():
            # newline="\n": Windows'da ham LF — --check va git farq ko'rmasin
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            self.stdout.write(f"{path.name}: {len(content.encode('utf-8')) // 1024} KB")
