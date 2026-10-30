import hashlib
import logging
from contextlib import nullcontext

from django.contrib.auth.backends import ModelBackend
from django.core.cache import DEFAULT_CACHE_ALIAS, cache, caches
from django.core.cache.backends.db import BaseDatabaseCache
from django.db import router, transaction
from rest_framework.authentication import SessionAuthentication

from .models import User
from .security_log import log_event
from .throttles import client_ip
from .validators import normalize_login

# Parolni tanlab topishdan (brute-force) himoya. Cheklov backendda turadi — API orqali kirish ham,
# admin panelga kirish ham bir xil himoyalangan. Ikki qavat:
# 1) bitta (akkaunt + IP) juftligi uchun 15 daqiqada 5 ta noto'g'ri urinish — begona odam loginni bilib,
#    egasini bloklab qo'ya olmaydi: u faqat o'z IP'sidan kirishni yopadi;
# 2) akkauntga barcha IP'lardan jami 30 ta urinish — ko'p IP'dan taqsimlab tanlashga qarshi.
#    Bitta IP bu hisoblagichga 5 tadan ko'p qo'sha olmaydi (o'z juftligi bloklangach to'xtaydi);
# 3) bitta IP'dan 15 daqiqada jami 30 ta noto'g'ri urinish (har xil loginlar bo'yicha) — bitta parolni ko'p loginda
#    sinash (password spraying) har bir juftlikni alohida 5 tagacha ushlab turgan 1-qavatdan o'tib ketmasligi uchun.
#    Admin panelning kirish sahifasida DRF "auth" cheklovi yo'q — shu qavat uni ham yopadi
LOGIN_MAX_FAILS = 5
LOGIN_ACCOUNT_MAX_FAILS = 30
LOGIN_IP_MAX_FAILS = 30
LOGIN_LOCK_SECONDS = 15 * 60


def find_user_by_login(identifier):
    """Foydalanuvchini nomi yoki elektron pochtasi bo'yicha topadi (kirish va parolni tiklashda ishlatiladi)"""
    identifier = (identifier or "").strip()
    normalized = normalize_login(identifier)
    if not normalized:
        return None
    user = None
    if "@" in normalized:
        user = User.objects.filter(email__iexact=normalized).order_by("id").first()
    if user is None:
        # Ro'yxatdan o'tishda "Ali" va "ali" (kirillda "Али" va "али" ham) bir xil nom hisoblanadi — kirishda ham shunday.
        # Qidiruv username_key bo'yicha: u NFKC + casefold ("ＡＤＭＩＮ" -> "admin"), SQL iexact esa kirill harflarini
        # tushirmaydi. Kalit noyob, shuning uchun bittadan ortiq akkaunt chiqmaydi
        user = User.objects.filter(username_key=User.make_username_key(normalized)).first()
    return user


def _lock_owner_id(identifier):
    """Hisoblagich egasi bo'lgan hisob (topilmasa None). Login va elektron pochta, katta-kichik harfdan qat'i nazar,
    bitta hisobga olib keladi — aks holda login bilan 5 ta, elektron pochta bilan yana 5 ta urinish qilish mumkin edi"""
    identifier = normalize_login(identifier)
    if not identifier:
        return None
    ids = User.objects.order_by("id").values_list("pk", flat=True)
    pk = ids.filter(email__iexact=identifier).first() if "@" in identifier else None
    return pk if pk is not None else ids.filter(username_key=User.make_username_key(identifier)).first()


def _account_key(identifier):
    # Hisoblagich akkaunt bor-yo'qligidan qat'i nazar yuritiladi — begona odam login mavjudligini bilib ololmaydi
    owner_id = _lock_owner_id(identifier)
    if owner_id is not None:
        return f"login_fail:user:{owner_id}"
    digest = hashlib.sha256(User.make_username_key(normalize_login(identifier)).encode("utf-8")).hexdigest()
    return f"login_fail:{digest}"


def _login_keys(identifier, request):
    """(hisob + IP) juftligi va hisob bo'yicha umumiy hisoblagich kalitlari"""
    account_key = _account_key(identifier)
    return f"{account_key}:ip:{client_ip(request) or 'noip'}", account_key


def _ip_fail_key(request):
    """IP bo'yicha noto'g'ri urinishlar hisoblagichi kaliti. IP noma'lum bo'lsa (so'rovsiz chaqiruv: konsol, testlar)
    None — hamma bitta "noip" chelakka tushib bir-birini bloklab qo'ymasligi uchun"""
    ip = client_ip(request)
    return f"login_fail_ip:{ip}" if ip else None


def login_attempts_left(identifier, request=None):
    """Bloklanishgacha qolgan urinishlar: juftlik, hisob va IP chegaralarining kichigi (0 — bloklangan)"""
    pair_key, account_key = _login_keys(identifier, request)
    ip_key = _ip_fail_key(request)
    counts = cache.get_many([key for key in (pair_key, account_key, ip_key) if key])
    left = min(
        LOGIN_MAX_FAILS - counts.get(pair_key, 0),
        LOGIN_ACCOUNT_MAX_FAILS - counts.get(account_key, 0),
    )
    if ip_key:
        left = min(left, LOGIN_IP_MAX_FAILS - counts.get(ip_key, 0))
    return left


def is_login_locked(identifier, request=None):
    return login_attempts_left(identifier, request) <= 0


def _atomic_cache():
    """Baza keshida incr() "o'qi -> +1 -> yoz" ketma-ketligi: bir nechta worker'da parallel urinishlar bir-birining
    yozuvini yo'qotib, limitdan oshib ketardi. SQLite'da atomic() bloki `transaction_mode=IMMEDIATE` (settings.py)
    bilan boshlanadi — yozish qulfi darrov olinadi, shuning uchun hisoblagich jarayonlar orasida ketma-ket
    yangilanadi. Redis'da INCR o'zi atomik — qo'shimcha blok kerak emas"""
    backend = caches[DEFAULT_CACHE_ALIAS]
    if isinstance(backend, BaseDatabaseCache):
        return transaction.atomic(using=router.db_for_write(backend.cache_model_class))
    return nullcontext()


def _bump_counter(key, seconds=LOGIN_LOCK_SECONDS):
    """Urinishlar sonini oshiradi va yangi qiymatini qaytaradi"""
    with _atomic_cache():
        if cache.add(key, 1, seconds):
            return 1
        try:
            attempts = cache.incr(key)
        except ValueError:  # kalit shu orada muddati o'tib o'chib ketgan
            cache.set(key, 1, seconds)
            return 1
        # Baza keshida incr() muddatni standart 5 daqiqaga tushirib yuboradi — kerakli muddatni qayta o'rnatamiz
        cache.touch(key, seconds)
        return attempts


def over_limit(key, limit, seconds):
    """Kalit bo'yicha urinishni sanaydi; limitdan oshgan bo'lsa True (parol tiklash so'rovlari uchun ham ishlatiladi)"""
    return _bump_counter(key, seconds) > limit


def refund_limit(key, seconds):
    """over_limit() bilan sanalgan urinishni qaytaradi (masalan, xat yuborilmagan bo'lsa)"""
    with _atomic_cache():
        try:
            cache.decr(key)
        except ValueError:  # kalit muddati o'tib o'chib ketgan
            return
        cache.touch(key, seconds)  # decr() ham muddatni standartga tushirib yuboradi


def _register_login_attempt(identifier, request):
    """Urinishni hisoblaydi (parol tekshirilishidan oldin). True — limitdan oshgan, kirish rad etiladi"""
    pair_key, account_key = _login_keys(identifier, request)
    ip_key = _ip_fail_key(request)
    if ip_key and cache.get(ip_key, 0) >= LOGIN_IP_MAX_FAILS:
        return True
    if _bump_counter(pair_key) > LOGIN_MAX_FAILS:
        # Bu IP allaqachon bloklangan: umumiy hisoblagichni oshirmaymiz, aks holda bitta IP undan 30 ga
        # yetkazib akkaunt egasini ham to'sib qo'yardi
        return True
    return _bump_counter(account_key) > LOGIN_ACCOUNT_MAX_FAILS


def _login_failed(identifier, request, user=None):
    """Noto'g'ri urinishni IP hisoblagichiga qo'shadi va xavfsizlik logiga yozadi (kirish ham, admin ham shu yerdan o'tadi)"""
    ip_key = _ip_fail_key(request)
    if ip_key:
        _bump_counter(ip_key)
    log_event("login_failed", request, logging.WARNING, username=identifier, user_id=user.pk if user else None)
    if login_attempts_left(identifier, request) <= 0:
        log_event("login_lockout", request, logging.WARNING, username=identifier)


CURRENT_PASSWORD_LOCKED_MESSAGE = "Juda ko'p noto'g'ri urinish. 15 daqiqadan keyin qayta urinib ko'ring."


def verify_current_password(user, password):
    """Sozlamalarda joriy parolni tasdiqlash (parol/elektron pochta o'zgartirish, hisobni o'chirish).
    Sessiyani qo'lga kiritgan odam joriy parolni tanlab topa olmasligi uchun bu yerda ham
    15 daqiqada 5 ta urinish. Natija: "ok", "wrong" yoki "locked" """
    key = f"pwcheck_fail:{user.pk}"
    if _bump_counter(key) > LOGIN_MAX_FAILS:
        return "locked"
    if user.check_password(password):
        cache.delete(key)
        return "ok"
    return "wrong"


def clear_login_fails(*identifiers, request=None, account=True):
    """Hisoblagichlarni nollaydi: shu so'rovning (hisob + IP) juftligini va (account=True bo'lsa) hisob bo'yicha
    umumiy hisoblagichni. Boshqa IP'lar juftliklarini o'chirib bo'lmaydi — ular 15 daqiqada o'zi tugaydi"""
    keys = []
    for identifier in identifiers:
        if identifier:
            pair_key, account_key = _login_keys(identifier, request)
            keys.append(pair_key)
            if account:
                keys.append(account_key)
    cache.delete_many(keys)


class UsernameOrEmailBackend(ModelBackend):
    """Foydalanuvchi nomi YOKI elektron pochta + parol bilan kirish"""

    def authenticate(self, request, username=None, password=None, email=None, **kwargs):
        identifier = email or username or kwargs.get(User.USERNAME_FIELD)
        if password is None or not identifier:
            return None

        # Urinish parol tekshirilishidan OLDIN hisobga olinadi: bir vaqtda yuborilgan ko'p so'rovlar
        # (parol xeshini tekshirish sekin bo'lgani uchun) limitdan oshib keta olmaydi
        if _register_login_attempt(identifier, request):
            log_event("login_locked", request, logging.WARNING, username=identifier)
            return None

        user = find_user_by_login(identifier)
        if user is None:
            # Vaqt bo'yicha foydalanuvchi mavjudligini bilib olishning oldini olish
            User().set_password(password)
            _login_failed(identifier, request)
            return None

        if user.check_password(password):
            # Faqat shu (akkaunt + IP) hisoblagichi nollanadi. Umumiy hisoblagich saqlanadi: begona odam o'z IP'sidan
            # to'g'ri kirib, boshqa IP'lardagi taxminlari sonini qayta boshlay olmasligi uchun
            clear_login_fails(identifier, request=request, account=False)
            # Bloklangan (is_active=False) akkaunt ham to'g'ri parol bilan qaytariladi (AllowAllUsersModelBackend kabi):
            # login_api unga "Hisob bloklangan" deydi, admin kirish formasi esa o'z xabari bilan rad etadi. Parolni
            # bilmagan odam bu xabarni ko'rmaydi. Sessiyani tiklash (get_user) baribir faol akkauntni talab qiladi
            if not self.user_can_authenticate(user):
                log_event("login_inactive_account", request, logging.WARNING, username=identifier, user_id=user.pk)
            return user
        _login_failed(identifier, request, user)
        return None


class SessionAuthentication401(SessionAuthentication):
    """DRF sessiya tugagan (yoki umuman kirilmagan) so'rovga standart holatda 403 qaytaradi — sahifa uni
    "ruxsat yo'q" deb tushunib, kirish oynasini ochmasdi. WWW-Authenticate sarlavhasi bo'lsa DRF 401 beradi
    va sahifa foydalanuvchini kirish oynasiga qaytaradi. "Session" sxemasi brauzerning login oynasini chiqarmaydi"""

    def authenticate_header(self, request):
        return "Session"
