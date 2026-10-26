import logging

from .throttles import client_ip

# Xavfsizlik hodisalari alohida "security" loggerga yoziladi (settings.LOGGING) — server logidan
# `grep security` bilan topiladi va kerak bo'lsa alohida faylga yo'naltiriladi
logger = logging.getLogger("security")


def _clean(value):
    # repr(): foydalanuvchi kiritgan qatordagi yangi qator va boshqaruv belgilari logda soxta qator yarata olmaydi
    return repr(str(value)[:100])


def log_event(event, request=None, level=logging.INFO, **fields):
    """Hodisani "event key='value' ... ip='...'" ko'rinishida yozadi. Faqat identifikatorlar (login nomi, user_id)
    beriladi — parol va tiklash kodi bu yerga HECH QACHON yuborilmaydi"""
    parts = [event]
    parts += [f"{key}={_clean(value)}" for key, value in fields.items() if value not in (None, "")]
    parts.append(f"ip={_clean(client_ip(request) or '-')}")
    logger.log(level, " ".join(parts))
