"""Qurilmalar (Sozlamalar → Qurilmalar): akkauntga qaysi qurilmalardan kirilgani va ularni chiqarish.

Qurilma = sessiya. Ro'yxatda faqat hali haqiqiy sessiyalar ko'rsatiladi: parol almashgani, "barcha qurilmalardan
chiqish" (session_epoch) yoki sessiya muddati tugagani sababli yaroqsiz bo'lgan yozuvlar ro'yxat so'ralganda
tozalanadi — har bir bekor qilish yo'liga alohida kod yozish shart emas."""
import re
from datetime import datetime, timedelta, timezone as dt_timezone

from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.utils.crypto import constant_time_compare

from .models import UserDevice
from .throttles import client_ip

# Sessiyada kirish vaqti (unix soniya) saqlanadigan kalit — middleware.remember_login_time yozadi
LOGIN_TIME_KEY = "_login_time"
# Oxirgi faollik har so'rovda emas, shuncha vaqtda bir marta yoziladi (bazaga ortiqcha yozuv bo'lmasin)
LAST_SEEN_STEP = timedelta(minutes=5)


def _user_agent(request):
    return (request.META.get("HTTP_USER_AGENT") or "")[:512]


def login_time(session):
    """Sessiyaga yozilgan kirish vaqti; yo'q bo'lsa (eski sessiyalar) — None"""
    value = session.get(LOGIN_TIME_KEY)
    if not isinstance(value, int):
        return None
    return datetime.fromtimestamp(value, tz=dt_timezone.utc)


def register_device(request, user):
    """Joriy sessiya uchun qurilma yozuvini yaratadi yoki yangilaydi. Kirishda va kalit almashgandan keyingi
    birinchi so'rovda (parol o'zgartirish sessiya kalitini yangilaydi) chaqiriladi"""
    key = request.session.session_key
    if not key:
        return None
    now = timezone.now()
    device, _ = UserDevice.objects.update_or_create(
        session_key=key,
        defaults={"user": user, "user_agent": _user_agent(request), "ip": client_ip(request), "last_seen": now},
        # Kirish vaqti sessiyadan olinadi: kalit almashganda ham asl kirish vaqti saqlanadi.
        # Vaqti noma'lum eski sessiya hozir kirilgan deb hisoblanadi (15 kunlik qoida uchun xavfsizroq tomoni)
        create_defaults={"user": user, "user_agent": _user_agent(request), "ip": client_ip(request),
                         "last_seen": now, "created_at": login_time(request.session) or now},
    )
    return device


def touch_device(request):
    """Har bir so'rovda (DeviceTrackingMiddleware): yozuv bo'lmasa yaratadi, bo'lsa oxirgi faollikni yangilaydi"""
    key = request.session.session_key
    if not key:
        return
    device = UserDevice.objects.filter(session_key=key).only("id", "user_id", "last_seen", "ip").first()
    if device is None or device.user_id != request.user.pk:
        register_device(request, request.user)
        return
    now = timezone.now()
    ip = client_ip(request)
    if now - device.last_seen >= LAST_SEEN_STEP or device.ip != ip:
        UserDevice.objects.filter(pk=device.pk).update(last_seen=now, ip=ip, user_agent=_user_agent(request))


def _session_is_valid(device, user, sessions):
    """Sessiya bazada bor, muddati o'tmagan va shu foydalanuvchining hozirgi parol/epoch belgisiga mos"""
    session = sessions.get(device.session_key)
    if session is None:
        return False
    data = session.get_decoded()
    if str(data.get(SESSION_KEY)) != str(user.pk) or not data.get(BACKEND_SESSION_KEY):
        return False
    return constant_time_compare(data.get(HASH_SESSION_KEY) or "", user.get_session_auth_hash())


def active_devices(user):
    """Haqiqiy sessiyasi bor qurilmalar. Yaroqsizlari (va ularning qolgan sessiyalari) shu yerda o'chiriladi"""
    devices = list(user.devices.all())
    sessions = {
        s.session_key: s
        for s in Session.objects.filter(session_key__in=[d.session_key for d in devices], expire_date__gt=timezone.now())
    }
    alive, dead = [], []
    for device in devices:
        (alive if _session_is_valid(device, user, sessions) else dead).append(device)
    if dead:
        keys = [d.session_key for d in dead]
        Session.objects.filter(session_key__in=keys).delete()
        UserDevice.objects.filter(session_key__in=keys).delete()
    return alive


def end_device(device):
    """Qurilmani chiqarish: sessiyasi o'chadi — keyingi so'rovda u qurilma kirish oynasiga qaytadi"""
    Session.objects.filter(session_key=device.session_key).delete()
    device.delete()


def terminate_wait(current):
    """Boshqa qurilmalarni chiqarishgacha qolgan vaqt (timedelta); chiqarish mumkin bo'lsa — None"""
    allowed_at = current.created_at + timedelta(days=UserDevice.MIN_DAYS_TO_TERMINATE)
    left = allowed_at - timezone.now()
    return left if left > timedelta(0) else None


# ---- User-Agent dan qurilma nomi: "Chrome 141 · Windows". To'liq tahlilchi emas — eng ko'p uchraydiganlari
_BROWSERS = [
    ("Edge", r"Edg(?:e|A|iOS)?/(\d+)"),
    ("Opera", r"(?:OPR|Opera)/(\d+)"),
    ("Yandex", r"YaBrowser/(\d+)"),
    ("Samsung Internet", r"SamsungBrowser/(\d+)"),
    ("Firefox", r"(?:Firefox|FxiOS)/(\d+)"),
    ("Chrome", r"(?:Chrome|CriOS)/(\d+)"),
    ("Safari", r"Version/(\d+).*Safari/"),
]
_SYSTEMS = [
    ("iPhone", r"iPhone"),
    ("iPad", r"iPad"),
    ("Android", r"Android"),
    ("Windows", r"Windows NT"),
    ("macOS", r"Mac OS X|Macintosh"),
    ("ChromeOS", r"CrOS"),
    ("Linux", r"Linux"),
]


def describe_device(user_agent):
    ua = user_agent or ""
    browser = next((f"{name} {m.group(1)}" for name, pattern in _BROWSERS if (m := re.search(pattern, ua))), "")
    system = next((name for name, pattern in _SYSTEMS if re.search(pattern, ua)), "")
    if system in ("iPhone", "Android") or "Mobile" in ua:
        kind = "mobile"
    elif system == "iPad" or "Tablet" in ua:
        kind = "tablet"
    else:
        kind = "desktop"
    return {"browser": browser, "os": system, "kind": kind}


def device_payload(device, current_key):
    return {
        "id": device.id,
        **describe_device(device.user_agent),
        "ip": device.ip,
        "created_at": device.created_at.isoformat(),
        "last_seen": device.last_seen.isoformat(),
        "current": device.session_key == current_key,
    }
