from datetime import datetime

from django import template
from django.utils import timezone

register = template.Library()

UZ_MONTHS = [
    "yanvar", "fevral", "mart", "aprel", "may", "iyun",
    "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr",
]


def _local(value):
    if isinstance(value, datetime) and timezone.is_aware(value):
        return timezone.localtime(value)
    return value


@register.filter
def uz_date(value, with_time=True):
    """2026-10-11 21:47 -> "11-oktabr, 2026, 21:47" (Toshkent vaqtida). Django'ning date filtri
    oy nomini inglizcha yozadi, shuning uchun o'zimizniki"""
    if not value:
        return "—"
    value = _local(value)
    text = f"{value.day}-{UZ_MONTHS[value.month - 1]}, {value.year}"
    if with_time and isinstance(value, datetime):
        text += f", {value:%H:%M}"
    return text


@register.filter
def uz_ago(value):
    """Qachon bo'lganini qisqa aytadi: "bugun, 14:05", "kecha, 09:12", "5 kun oldin", "2 oy oldin" """
    if not value:
        return "hech qachon"
    value = _local(value)
    days = (timezone.localdate() - value.date()).days
    if days <= 0:
        return f"bugun, {value:%H:%M}"
    if days == 1:
        return f"kecha, {value:%H:%M}"
    if days < 30:
        return f"{days} kun oldin"
    if days < 365:
        return f"{days // 30} oy oldin"
    return f"{days // 365} yil oldin"


@register.filter
def initial(user):
    """Avatar uchun bosh harf: ism yoki login"""
    return (str(user)[:1] or "?").upper()


@register.simple_tag(takes_context=True)
def query_url(context, **params):
    """Joriy qidiruv/filtr parametrlarini saqlab, ba'zilarini almashtiradi: {% query_url page=2 %}.
    Qiymat None bo'lsa parametr olib tashlanadi (masalan filtr o'zgarganda sahifa raqami)"""
    query = context["request"].GET.copy()
    for key, value in params.items():
        if value is None or value == "":
            query.pop(key, None)
        else:
            query[key] = value
    return f"?{query.urlencode()}" if query else "?"


@register.simple_tag
def support_unread_total():
    """Navbardagi "Yordam" havolasi uchun: javob kutayotgan (o'qilmagan) foydalanuvchi xabarlari soni"""
    from mainapp.models import SupportMessage
    return SupportMessage.objects.filter(from_admin=False, is_read=False).count()
