from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db import IntegrityError, connections, models, transaction
from django.db.models import BooleanField, Case, F, Q, Sum, Value, When
from django.db.models.functions import Upper
import logging
import re
import secrets
import threading
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from functools import lru_cache, wraps

from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.utils.html import format_html
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.core.validators import validate_email
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, BasePermission, SAFE_METHODS, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from django_filters.rest_framework import DjangoFilterBackend
from django.urls import reverse
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.views import exception_handler as drf_exception_handler

from .panel import can_view_panel
from .models import (
    format_money,
    MAX_AMOUNT, MAX_AMOUNT_MESSAGE, MAX_YEAR, MIN_YEAR, USERNAME_TAKEN_MESSAGE, is_username_conflict,
    User, Category, ExpenseCategory, Wallet, Member, Income, Expense, Transfer, Debt, PasswordResetCode, UserDevice,
    LoginCode, RecurringPayment, SavingsGoal,
)
from .devices import active_devices, device_payload, end_device, register_device, terminate_wait
from .backends import (
    CURRENT_PASSWORD_LOCKED_MESSAGE, clear_login_fails, find_user_by_login, is_login_locked, login_attempts_left,
    over_limit, refund_limit, verify_current_password,
)
from .db_functions import casefold_contains_q, fold
from .currency import CurrencyRateError, UzsConverter, convert, get_rates_snapshot, normalize_currency, round_amount
from .money import MONEY_INVALID_MESSAGE, parse_amount, quantize_money
from .recurring import process_due as process_due_recurring
from .security_log import log_event
from .notices import unread_notice_count
from .support import unread_for_user
from .throttles import AuthRateThrottle, client_ip
from .tts import provider as tts_provider
from .stt import is_enabled as stt_enabled
from .validators import normalize_login, password_errors_uz, username_error

# Uzbek hafta kunlari qisqartmasi -> Django week_day raqami (1=Yakshanba ... 7=Shanba)
UZ_WEEKDAY_TO_DJANGO = {"Ya": 1, "Du": 2, "Se": 3, "Ch": 4, "Pa": 5, "Ju": 6, "Sh": 7}
from .serializers import (
    UserSerializer,
    CategorySerializer,
    ExpenseCategorySerializer,
    WalletSerializer,
    MemberSerializer,
    IncomeSerializer,
    ExpenseSerializer,
    TransferSerializer,
    DebtSerializer,
    RecurringPaymentSerializer,
    SavingsGoalSerializer,
)


def validate_email_uz(email, exclude_pk=None):
    """Elektron pochta ixtiyoriy, lekin kiritilsa to'g'ri formatda va boshqa hisobda band bo'lmasligi kerak
    (elektron pochta bilan ham kirish mumkinligi uchun). Xato matnini yoki None qaytaradi"""
    if not email:
        return None
    try:
        validate_email(email)
    except DjangoValidationError:
        return "Elektron pochta manzili noto'g'ri"
    if User.email_taken(email, exclude_pk=exclude_pk):
        return "Bu elektron pochta boshqa hisobda ishlatilgan"
    return None


ASCII_INT_RE = re.compile(r"-?[0-9]+")


def strict_int(value):
    """So'rovdagi butun sonni qat'iy o'qiydi: int, kasr qismi yo'q float (99.0) yoki ASCII raqamli satr qabul qilinadi.
    int() ga ishonib bo'lmaydi: int(99.9) jimgina 99, int(True) esa 1 bo'lib qoladi, int("١٢") ham o'tadi.
    Yaroqsiz qiymat uchun None qaytaradi"""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str):
        value = value.strip()
        try:
            # Juda uzun raqamli satr int() da ValueError beradi (Python'ning raqam uzunligi chegarasi)
            return int(value) if ASCII_INT_RE.fullmatch(value) else None
        except ValueError:
            return None
    return None


def api_exception_handler(exc, context):
    """DRF standart xato ishlovchisi + decimal.InvalidOperation. Juda uzun raqam (28 xonadan ortiq, masalan "1e999999" yoki
    40 ta "1") Decimal.quantize() ni yiqitadi — bu ArithmeticError, DRF uni bilmaydi va 500 qaytarardi. Hech qaysi
    haqiqiy miqdor bunchalik katta emas (MAX_AMOUNT), shuning uchun 400 va "miqdor juda katta" xabari"""
    if isinstance(exc, InvalidOperation):
        return Response({"error": MAX_AMOUNT_MESSAGE}, status=status.HTTP_400_BAD_REQUEST)
    return drf_exception_handler(exc, context)


def error_text(e):
    """Validatsiya xatolarini o'qiladigan oddiy matnga aylantiradi (xom dict/ErrorDetail o'rniga)"""
    if isinstance(e, DjangoValidationError):
        return " ".join(e.messages)
    if not isinstance(e, DRFValidationError):
        return str(e)
    parts = []

    def walk(value):
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                walk(item)
        else:
            parts.append(str(value))

    walk(e.detail)
    return " ".join(parts)


# ==========================================
# AUTHENTICATION API ENDPOINTS
# ==========================================

LOGIN_LOCKED_MESSAGE = (
    "Juda ko'p noto'g'ri urinish. 15 daqiqadan keyin qayta urinib ko'ring "
    "yoki \"Parolni unutdingizmi?\" orqali parolni tiklang."
)

# Kirish / ro'yxatdan o'tish / parol tiklash: umumiy cheklovlar + IP bo'yicha qattiqroq "auth" cheklovi
AUTH_THROTTLES = [AnonRateThrottle, UserRateThrottle, AuthRateThrottle]


def enforce_csrf(view):
    """DRF CSRF tokenini faqat tizimga kirgan foydalanuvchida tekshiradi. Kirish, ro'yxatdan o'tish va parol
    tiklash so'rovlarini begona sayt foydalanuvchi brauzeri nomidan yubora olmasligi uchun (login CSRF)
    ularda ham tekshiramiz. Sahifa tokenni X-CSRFToken sarlavhasida avtomatik yuboradi"""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        SessionAuthentication().enforce_csrf(request)
        return view(request, *args, **kwargs)
    return wrapper




def current_password_problem(user, password, field, wrong_message="Joriy parol noto'g'ri"):
    """Sozlamalarda joriy parolni tekshiradi (urinishlar soni cheklangan — backends.verify_current_password).
    Muammo bo'lsa tayyor javob (Response), aks holda None qaytaradi"""
    result = verify_current_password(user, password)
    if result == "locked":
        return Response({field: CURRENT_PASSWORD_LOCKED_MESSAGE}, status=status.HTTP_429_TOO_MANY_REQUESTS)
    if result == "wrong":
        return Response({field: wrong_message}, status=status.HTTP_400_BAD_REQUEST)
    return None


def password_from(request, field):
    """Parol maydonini o'qiydi. Bosh va oxiridagi bo'sh joylar hamma joyda (ro'yxatdan o'tish, kirish,
    parol o'zgartirish va tiklash) bir xil olib tashlanadi — aks holda " parol " bilan o'rnatilgan parol
    bilan kirib bo'lmay qolardi"""
    return str(request.data.get(field) or "").strip()


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes(AUTH_THROTTLES)
@ensure_csrf_cookie
@enforce_csrf
def login_api(request):
    """Tizimga kirish — foydalanuvchi nomi yoki elektron pochta va parol bilan"""
    username = str(request.data.get("username") or request.data.get("email") or "").strip()
    password = password_from(request, "password")

    if not username or not password:
        return Response(
            {"error": "Foydalanuvchi nomi (yoki elektron pochta) va parol kiritilishi shart"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if is_login_locked(username, request):
        log_event("login_locked", request, logging.WARNING, username=username)
        return Response({"error": LOGIN_LOCKED_MESSAGE}, status=status.HTTP_429_TOO_MANY_REQUESTS)

    # Urinishlar hisobi va bloklash backendda (UsernameOrEmailBackend) — admin panelga kirish ham himoyalangan
    user = authenticate(request, username=username, password=password)
    if user is not None:
        # Backend bloklangan akkauntni ham (faqat to'g'ri parol bilan) qaytaradi — shu sabab bu shox endi ishlaydi
        if not user.is_active:
            return Response(
                {"error": "Foydalanuvchi hisobi bloklangan"},
                status=status.HTTP_403_FORBIDDEN
            )
        if user.two_factor_enabled and user.email:
            # Parol to'g'ri, lekin sessiya hali ochilmaydi: emailga kod ketadi, login_2fa_api tasdiqlagach kiriladi
            token = _issue_login_code(user, "login")
            if token is None:
                return Response({"error": LOGIN_CODE_LIMIT_MESSAGE}, status=status.HTTP_429_TOO_MANY_REQUESTS)
            log_event("login_code_sent", request, user_id=user.pk, username=user.username)
            return Response({
                "two_factor": True,
                "token": token,
                "email": mask_email(user.email),
                "message": "Elektron pochtangizga 6 xonali kirish kodi yuborildi",
            })
        # set_expiry() chaqirilmaydi: sessiya muddati settings'dagi SESSION_COOKIE_AGE (doimiy cookie) bo'yicha
        login(request, user)
        return Response({
            "message": "Muvaffaqiyatli tizimga kirildi",
            "user": user_payload(user),
        })

    left = login_attempts_left(username, request)
    if left <= 0:
        return Response({"error": LOGIN_LOCKED_MESSAGE}, status=status.HTTP_429_TOO_MANY_REQUESTS)
    message = "Foydalanuvchi nomi (yoki elektron pochta) yoki parol noto'g'ri"
    if left <= 2:
        message += f". Yana {left} ta urinish qoldi."
    return Response({"error": message}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(["POST"])
@permission_classes([AllowAny])
def logout_api(request):
    """Tizimdan chiqish (Logout)"""
    logout(request)
    return Response({"message": "Tizimdan muvaffaqiyatli chiqildi"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_all_api(request):
    """Barcha qurilmalardan chiqish: session_epoch oshadi — shu foydalanuvchining barcha sessiyalari (joriysi ham)
    yaroqsiz bo'ladi"""
    user = request.user
    # F(): ikki qurilmadan bir vaqtda bosilsa ham yangilanish yo'qolmaydi. Faqat shu maydon yoziladi, shuning uchun
    # parallel parol/profil o'zgarishi ustidan yozilmaydi
    User.objects.filter(pk=user.pk).update(session_epoch=F("session_epoch") + 1)
    log_event("logout_all", request, user_id=user.pk, username=user.username)
    # Joriy qurilma ham chiqadi (foydalanuvchi "barcha"ni tanladi): sessiya bazadan o'chadi, cookie tozalanadi
    logout(request)
    return Response({"message": "Barcha qurilmalardagi sessiyalar yopildi"})


# ==========================================
# QURILMALAR (Sozlamalar → Qurilmalar)
# ==========================================
def _current_device(request, devices):
    key = request.session.session_key
    current = next((d for d in devices if d.session_key == key), None)
    # Ro'yxat so'ralishidan oldin middleware yozuvni yaratgan bo'ladi; bo'lmasa (masalan, sessiya kaliti
    # shu so'rov ichida almashgan) — hozir yoziladi
    return current or register_device(request, request.user)


def _terminate_problem(current):
    """15 kunlik qoida: joriy qurilmada yetarlicha oldin kirilmagan bo'lsa — 403 javob"""
    left = terminate_wait(current)
    if left is None:
        return None
    days = left.days + (1 if left.seconds or left.microseconds else 0)
    return Response(
        {"error": f"Boshqa qurilmalardan chiqarish uchun bu qurilmada kamida {UserDevice.MIN_DAYS_TO_TERMINATE} kun "
                  f"oldin kirilgan bo'lishi kerak. Yana {days} kun qoldi."},
        status=status.HTTP_403_FORBIDDEN,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def devices_api(request):
    """Hisobga kirilgan qurilmalar: joriysi birinchi, qolganlari oxirgi faollik bo'yicha"""
    devices = active_devices(request.user)
    current = _current_device(request, devices)
    if current is not None and current not in devices:
        devices.insert(0, current)
    devices.sort(key=lambda d: (d.pk != getattr(current, "pk", None), -d.last_seen.timestamp()))
    wait = terminate_wait(current) if current else None
    return Response({
        "devices": [device_payload(d, request.session.session_key) for d in devices],
        "min_days": UserDevice.MIN_DAYS_TO_TERMINATE,
        "can_terminate": current is not None and wait is None,
        "terminate_allowed_at": (current.created_at + timedelta(days=UserDevice.MIN_DAYS_TO_TERMINATE)).isoformat()
        if current else None,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def device_terminate_api(request, pk):
    """Bitta boshqa qurilmani chiqarish"""
    devices = active_devices(request.user)
    current = _current_device(request, devices)
    device = next((d for d in devices if d.pk == pk), None)
    if device is None:
        return Response({"error": "Qurilma topilmadi"}, status=status.HTTP_404_NOT_FOUND)
    if current is not None and device.pk == current.pk:
        return Response({"error": "Bu qurilmadan chiqish uchun \"Chiqish\" tugmasini bosing"},
                        status=status.HTTP_400_BAD_REQUEST)
    problem = _terminate_problem(current)
    if problem:
        return problem
    end_device(device)
    log_event("device_terminated", request, user_id=request.user.pk, username=request.user.username, device=pk)
    return Response({"message": "Qurilma chiqarildi"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def devices_terminate_others_api(request):
    """Joriysidan boshqa barcha qurilmalarni chiqarish"""
    devices = active_devices(request.user)
    current = _current_device(request, devices)
    problem = _terminate_problem(current)
    if problem:
        return problem
    others = [d for d in devices if d.pk != current.pk]
    for device in others:
        end_device(device)
    log_event("devices_terminated", request, user_id=request.user.pk, username=request.user.username,
              count=len(others))
    return Response({"message": "Boshqa barcha qurilmalar chiqarildi", "count": len(others)})


@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def me_api(request):
    """Hozirgi foydalanuvchi holati"""
    if request.user.is_authenticated:
        # Ilova ochilganda (ma'lumotlar yuklanishidan oldin) muddati kelgan takroriy to'lovlar yoziladi —
        # bosh sahifa balansi ularni allaqachon hisobga olgan bo'lsin. Xato kirishni to'xtatmasligi kerak
        try:
            process_due_recurring(request.user)
        except Exception:
            logger.exception("Doimiy to'lovlarni yozishda xato (user=%s)", request.user.pk)
        return Response({
            "authenticated": True,
            "user": user_payload(request.user),
        })
    return Response({"authenticated": False})


def user_payload(user):
    """Frontend uchun foydalanuvchi ma'lumotlari (sozlamalar formasini to'ldirish uchun ism/familiya ham)"""
    return {
        "id": user.id,
        "username": user.username,
        "name": str(user),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "phone": user.phone,
        # Navbarda "Admin panel" havolasini ko'rsatish uchun
        "is_staff": user.is_staff,
        # Panel manzili (.env: PANEL_URL) faqat panelga ruxsati borlarga beriladi — boshqalarga navbarda tugma chiqmaydi
        "panel_url": reverse("panel-accounts") if can_view_panel(user) else "",
        "two_factor_enabled": user.two_factor_enabled,
        # Yordam chatida o'qilmagan admin javoblari (navbar qo'ng'irog'i)
        "support_unread": unread_for_user(user),
        # Admin yuborgan, hali o'qilmagan xabarlar (navbar qo'ng'irog'i)
        "notices_unread": unread_notice_count(user),
        # Ovozli yordamchi: brauzer tanimasa ovoz yozuvi serverda taniladi (mainapp/stt.py, .env: OPENAI_API_KEY
        # yoki tekin GEMINI_API_KEY)
        "voice_server_stt": stt_enabled(),
        # Javoblar server ovozida (mainapp/tts.py): voicelab | azure | openai | null — null bo'lsa brauzer ovozi
        "voice_server_tts": tts_provider(),
    }


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def profile_api(request):
    """Sozlamalar — foydalanuvchi o'z profil ma'lumotlarini o'zgartirishi"""
    user = request.user
    data = request.data
    errors = {}
    # O'zgarishlar avval yig'iladi va faqat barcha tekshiruvlar (parol ham) o'tgandan keyin qo'llanadi
    changes = {}

    if "username" in data:
        username = normalize_login(data.get("username"))
        if username != user.username:
            username_problem = username_error(username, exclude_pk=user.pk)
            if username_problem:
                errors["username"] = username_problem
            else:
                changes["username"] = username

    email_changed = False
    if "email" in data:
        email = str(data.get("email") or "").strip()
        email_error = validate_email_uz(email, exclude_pk=user.pk)
        if not email and user.two_factor_enabled:
            # Kirish kodi emailga keladi — email olib tashlansa akkauntga kirib bo'lmay qolardi
            email_error = "Ikki bosqichli himoya yoqilgan — elektron pochtani o'chirishdan oldin uni o'chiring"
        if email_error:
            errors["email"] = email_error
        else:
            email_changed = email.lower() != (user.email or "").lower()
            changes["email"] = email

    for field in ("first_name", "last_name"):
        if field in data:
            changes[field] = str(data.get(field) or "").strip()[:150]

    if "phone" in data:
        changes["phone"] = str(data.get("phone") or "").strip()[:20] or None

    if errors:
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

    if email_changed:
        # Email — parolni tiklash kanali. Uni o'zgartirish (yoki o'chirish) joriy parol bilan tasdiqlanadi:
        # aks holda ochiq qolgan sessiyani qo'lga kiritgan odam emailni o'zinikiga almashtirib,
        # "Parolni unutdingizmi?" orqali akkauntni butunlay egallab olardi
        password = password_from(request, "password")
        if not password:
            return Response({"password": "Elektron pochtani o'zgartirish uchun joriy parolni kiriting"},
                            status=status.HTTP_400_BAD_REQUEST)
        problem = current_password_problem(user, password, "password")
        if problem:
            return problem

    pending_email = None
    if email_changed and changes["email"] and user.two_factor_enabled:
        # Kirish va parol tiklash kodlari emailga keladi: xato yozilgan yangi manzil akkauntni qulflab qo'ymasligi uchun
        # u darhol yozilmaydi — avval yangi manzilga kod boradi va confirm_email_api tasdiqlaydi.
        # Soatlik limit hech narsa saqlanmasdan oldin tekshiriladi
        pending_email = changes.pop("email")
        token = _issue_login_code(user, "email", email=pending_email)
        if token is None:
            return Response({"error": LOGIN_CODE_LIMIT_MESSAGE}, status=status.HTTP_429_TOO_MANY_REQUESTS)

    for field, value in changes.items():
        setattr(user, field, value)
    # Faqat o'zgargan maydonlar yoziladi: parallel so'rov (masalan parol o'zgartirish) yozgan boshqa maydonlar
    # eski qiymat bilan bosib ketilmaydi. Bo'sh ro'yxat bilan save() hech narsa yozmaydi
    try:
        with transaction.atomic():
            user.save(update_fields=list(changes))
            if "email" in changes and email_changed:
                # Eski manzilga yuborilgan tiklash kodi endi egasiniki bo'lmasligi mumkin
                user.password_reset_codes.filter(used=False).update(used=True)
    except IntegrityError as exc:
        # Ikki kishi bir vaqtda bir xil nomni olmoqchi bo'lganda (tekshiruvdan keyin) 500 xato o'rniga
        if not is_username_conflict(exc):
            raise
        return Response({"username": USERNAME_TAKEN_MESSAGE}, status=status.HTTP_400_BAD_REQUEST)
    if pending_email:
        log_event("email_change_requested", request, user_id=user.pk)
        return Response({
            "message": "Yangi elektron pochtaga tasdiqlash kodi yuborildi",
            "user": user_payload(user),
            "email_pending": {"token": token, "email": mask_email(pending_email)},
        })
    return Response({"message": "Profil ma'lumotlari saqlandi", "user": user_payload(user)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password_api(request):
    """Sozlamalar — joriy parolni tasdiqlab, yangi parol o'rnatish"""
    user = request.user
    old_password = password_from(request, "old_password")
    new_password = password_from(request, "new_password")

    if not old_password or not new_password:
        return Response({"error": "Joriy va yangi parol kiritilishi shart"}, status=status.HTTP_400_BAD_REQUEST)
    problem = current_password_problem(user, old_password, "old_password")
    if problem:
        return problem
    if old_password == new_password:
        return Response({"new_password": "Yangi parol joriy paroldan farq qilishi kerak"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        validate_password(new_password, user=user)
    except DjangoValidationError as e:
        return Response({"new_password": password_errors_uz(e)}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        user.set_password(new_password)
        user.save(update_fields=["password"])
        # Parol almashgach avval yuborilgan faol tiklash kodlari bekor qilinadi: ular eski holat uchun berilgan
        # edi, 15 daqiqa ichida emailga kirgan odam bu parolni yana almashtira olmasligi kerak
        user.password_reset_codes.filter(used=False).update(used=True)
    # Parol o'zgargach joriy sessiya chiqib ketmasligi uchun. Sessiya kaliti almashadi — qurilma yozuvi yangi
    # kalitga ko'chiriladi, aks holda kirish vaqti yo'qolib 15 kunlik hisob qaytadan boshlanardi
    old_key = request.session.session_key
    update_session_auth_hash(request, user)
    UserDevice.objects.filter(session_key=old_key).update(session_key=request.session.session_key)
    log_event("password_changed", request, user_id=user.pk, username=user.username)
    return Response({"message": "Parol muvaffaqiyatli o'zgartirildi"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def delete_account_api(request):
    """Sozlamalar - parolni tasdiqlab, hisobni o'chirish.
    Akkaunt va unga bog'langan BARCHA ma'lumotlar bazadan butunlay o'chadi (qaytarib bo'lmaydi); email va login nomi
    qayta ro'yxatdan o'tish uchun bo'shaydi"""
    password = password_from(request, "password")
    if not password:
        return Response({"password": "Tasdiqlash uchun parolni kiriting"}, status=status.HTTP_400_BAD_REQUEST)
    user = request.user
    problem = current_password_problem(user, password, "password", wrong_message="Parol noto'g'ri")
    if problem:
        return problem

    # O'chirgach pk None bo'ladi — logga yozish uchun oldindan olamiz
    user_id, username = user.pk, user.username
    logout(request)
    user.delete()
    log_event("account_deleted", request, user_id=user_id, username=username)
    return Response({"message": "Hisob o'chirildi"})


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes(AUTH_THROTTLES)
@ensure_csrf_cookie
@enforce_csrf
def register_api(request):
    """Yangi foydalanuvchini ro'yxatdan o'tkazish"""
    # str(): JSON'da son/null kelsa ham 500 xato bermasligi uchun
    username = normalize_login(request.data.get("username"))
    password = password_from(request, "password")
    first_name = str(request.data.get("first_name") or "").strip()[:150]
    last_name = str(request.data.get("last_name") or "").strip()[:150]
    phone = str(request.data.get("phone") or "").strip()[:20]
    # Ixtiyoriy, lekin parolni unutganda tiklash kodi shu emailga yuboriladi
    email = str(request.data.get("email") or "").strip()

    if not username or not password:
        return Response(
            {"error": "Foydalanuvchi nomi va parol kiritilishi shart"},
            status=status.HTTP_400_BAD_REQUEST
        )

    username_problem = username_error(username)
    if username_problem:
        return Response({"error": username_problem}, status=status.HTTP_400_BAD_REQUEST)

    email_problem = validate_email_uz(email)
    if email_problem:
        return Response({"error": email_problem}, status=status.HTTP_400_BAD_REQUEST)

    try:
        validate_password(password, user=User(
            username=username, first_name=first_name, last_name=last_name,
        ))
    except DjangoValidationError as e:
        return Response({"error": password_errors_uz(e)}, status=status.HTTP_400_BAD_REQUEST)

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone=phone
            )
            # Standart birinchi hamyon ochib beramiz
            Wallet.objects.create(
                user=user,
                name="Asosiy hamyon (Naqd)",
                summa=0,
                currency="UZS"
            )
    except IntegrityError as exc:
        # Ikki kishi bir vaqtda bir xil nom bilan ro'yxatdan o'tganda (tekshiruvdan keyin) 500 xato o'rniga
        if not is_username_conflict(exc):
            raise
        return Response({"error": USERNAME_TAKEN_MESSAGE}, status=status.HTTP_400_BAD_REQUEST)

    login(request, user)
    return Response({
        "message": "Ro'yxatdan muvaffaqiyatli o'tildi",
        "user": user_payload(user),
    }, status=status.HTTP_201_CREATED)


# ==========================================
# PAROLNI TIKLASH (email orqali kod)
# ==========================================

logger = logging.getLogger(__name__)

RESET_RESEND_SECONDS = 60
# Bitta akkauntga soatiga ko'pi bilan shuncha xat — begona odam birovning pochtasini xatga ko'mib,
# pochta xizmatining kunlik limitini tugata olmasligi uchun
RESET_MAX_PER_HOUR = 5
# Kunlik chegara: har kodga 5 urinish bilan 6 xonali kodni topish ehtimoli yiliga ~2% dan oshmaydi
RESET_MAX_PER_DAY = 10
# IP bo'yicha chegaralar: begona odam bir akkauntga takroran so'rov yuborib, uning soatlik/kunlik kod limitini
# tugatib qo'ymasligi uchun bitta IP bir akkauntga sutkada ko'pi bilan 3 ta kod olishi mumkin (limit 10 dan past),
# va bir IP'dan soatiga 10 tadan ortiq kod so'rab ko'p akkauntni xatga ko'mib bo'lmaydi.
# Cheklovga tushgan so'rovga ham xuddi shu umumiy javob qaytadi (akkaunt borligi bilinmaydi)
RESET_MAX_PER_ACCOUNT_IP_PER_DAY = 3
RESET_MAX_PER_IP_PER_HOUR = 10
RESET_REQUEST_MESSAGE = (
    "Agar bunday hisob mavjud bo'lsa va unga elektron pochta ulangan bo'lsa, "
    "elektron pochtaga 6 xonali tiklash kodi yuborildi."
)
# Kod tekshirishdagi har qanday muvaffaqiyatsizlik (akkaunt yo'q, faol kod yo'q, muddat o'tgan, urinishlar tugagan,
# kod noto'g'ri) uchun BITTA xabar: "Yana N ta urinish qoldi" faqat mavjud akkauntda chiqib, uning borligini oshkor qilardi
RESET_CODE_INVALID_MESSAGE = "Kod noto'g'ri yoki muddati o'tgan. Kerak bo'lsa yangi kod so'rang."


def _run_in_background(func, *args):
    """Sekin tashqi chaqiruvni (SMTP) so'rovdan tashqarida bajaradi. Sinxron yuborilsa mavjud hisobga javob
    sezilarli sekinroq bo'lib, hisob borligini oshkor qilardi. settings.MAIL_IN_BACKGROUND=False bo'lsa (testlar)
    func shu zahoti, shu oqimda bajariladi — test tranzaksiyasi va mail.outbox ko'rinib turadi.
    Oqim daemon: jarayon to'xtaganda yuborilmay qolgan xat yo'qoladi (foydalanuvchi yangi kod so'raydi)"""
    if not settings.MAIL_IN_BACKGROUND:
        func(*args)
        return None

    def runner():
        try:
            func(*args)
        except Exception:
            logger.exception("Fon vazifasi xato bilan tugadi (%s)", getattr(func, "__name__", func))
        finally:
            # Oqim o'zining baza ulanishini ochgan — yopilmasa, har so'rovda bittadan ulanish to'planib qoladi
            connections.close_all()

    thread = threading.Thread(target=runner, name="background-mail", daemon=True)
    thread.start()
    return thread


def _send_reset_mail(user_id, email, name, code, reset_code_id, ip_limits):
    """Tiklash kodini yuboradi. Xat ketmasa xato foydalanuvchiga qaytarilmaydi (javob allaqachon ketgan va u bir xil
    bo'lishi shart), faqat logga yoziladi"""
    try:
        minutes = PasswordResetCode.CODE_LIFETIME_MINUTES
        # Matn + HTML (multipart) — pochta filtrlari faqat matnli yoki faqat HTML xatlarga ko'proq shubha qiladi.
        # Ism foydalanuvchi kiritgan matn — HTML ichiga format_html orqali ekranlanib qo'yiladi
        send_mail(
            subject="Moliya — parolni tiklash kodi",
            message=(
                f"Assalomu alaykum, {name}!\n\n"
                f"Parolni tiklash kodingiz: {code}\n\n"
                f"Kod {minutes} daqiqa amal qiladi. "
                "Agar parolni tiklashni siz so'ramagan bo'lsangiz, bu xatni e'tiborsiz qoldiring — "
                "parolingiz o'zgarmaydi.\n\n"
                "Hurmat bilan,\nMoliya"
            ),
            html_message=format_html(
                '<div style="font-family:Arial,sans-serif;font-size:15px;color:#1f2937;line-height:1.5">'
                "<p>Assalomu alaykum, {}!</p>"
                "<p>Parolni tiklash kodingiz:</p>"
                '<p style="font-size:28px;font-weight:bold;letter-spacing:4px;margin:8px 0">{}</p>'
                "<p>Kod {} daqiqa amal qiladi. Agar parolni tiklashni siz so'ramagan bo'lsangiz, "
                "bu xatni e'tiborsiz qoldiring — parolingiz o'zgarmaydi.</p>"
                '<p style="color:#6b7280">Hurmat bilan,<br>Moliya</p>'
                "</div>",
                name, code, minutes,
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )
    except Exception:
        logger.exception("Parol tiklash xatini yuborib bo'lmadi (user_id=%s)", user_id)
        # Yuborilmagan kod qayta urinishni 60 soniyaga to'sib qo'ymasligi uchun o'chiriladi
        PasswordResetCode.objects.filter(pk=reset_code_id).delete()
        # Xat ketmagan so'rov IP limitidan ham olib tashlanadi: pochta xizmati ishlamay qolsa foydalanuvchi bekorga bloklanmasin
        for key, _, seconds in ip_limits:
            refund_limit(key, seconds)


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes(AUTH_THROTTLES)
@enforce_csrf
def password_reset_request_api(request):
    """1-qadam: login yoki elektron pochta bo'yicha hisobni topib, ulangan elektron pochtaga kod yuborish.
    Javob (matni, statusi va deyarli vaqti ham) har doim bir xil — begona odam hisob yoki elektron pochta borligini
    bilib ololmasligi uchun. Xat fonda yuboriladi, shuning uchun pochta xatosi ham javobga ta'sir qilmaydi"""
    identifier = str(request.data.get("username") or "").strip()
    if not identifier:
        return Response({"error": "Foydalanuvchi nomi yoki elektron pochta kiritilishi shart"}, status=status.HTTP_400_BAD_REQUEST)

    # Kod va uning xeshi akkaunt bor-yo'qligidan qat'i nazar har doim hisoblanadi: sekin xeshlash faqat mavjud
    # akkauntda bajarilsa, javob vaqti akkaunt borligini oshkor qilardi
    code = f"{secrets.randbelow(1_000_000):06d}"
    code_hash = make_password(code)

    user = find_user_by_login(identifier)
    if user is None or not user.is_active or not user.email:
        log_event("password_reset_requested", request, identifier=identifier, result="no_account")
        return Response({"message": RESET_REQUEST_MESSAGE})

    now = timezone.now()
    last = user.password_reset_codes.first()
    if last and (now - last.created_at).total_seconds() < RESET_RESEND_SECONDS:
        # Ketma-ket ko'p xat yuborilishining oldini olish
        log_event("password_reset_requested", request, identifier=identifier, user_id=user.pk, result="cooldown")
        return Response({"message": RESET_REQUEST_MESSAGE})
    recent_codes = user.password_reset_codes.filter(created_at__gte=now - timedelta(days=1))
    if (recent_codes.filter(created_at__gte=now - timedelta(hours=1)).count() >= RESET_MAX_PER_HOUR
            or recent_codes.count() >= RESET_MAX_PER_DAY):
        log_event("password_reset_requested", request, logging.WARNING,
                  identifier=identifier, user_id=user.pk, result="account_limit")
        return Response({"message": RESET_REQUEST_MESSAGE})
    ip = client_ip(request) or "noip"
    ip_limits = (
        (f"reset_req:{user.pk}:{ip}", RESET_MAX_PER_ACCOUNT_IP_PER_DAY, 24 * 3600),
        (f"reset_req_ip:{ip}", RESET_MAX_PER_IP_PER_HOUR, 3600),
    )
    if any(over_limit(*limit) for limit in ip_limits):
        log_event("password_reset_requested", request, logging.WARNING,
                  identifier=identifier, user_id=user.pk, result="ip_limit")
        return Response({"message": RESET_REQUEST_MESSAGE})

    with transaction.atomic():
        user.password_reset_codes.filter(used=False).update(used=True)
        reset_code = PasswordResetCode.objects.create(
            user=user,
            code_hash=code_hash,
            expires_at=timezone.now() + timedelta(minutes=PasswordResetCode.CODE_LIFETIME_MINUTES),
        )

    # Oqim tranzaksiya yopilgandan keyin boshlanadi va ORM obyektlarini emas, oddiy qiymatlarni oladi
    _run_in_background(
        _send_reset_mail, user.pk, user.email, user.first_name or user.username, code, reset_code.pk, ip_limits,
    )
    log_event("password_reset_requested", request, identifier=identifier, user_id=user.pk, result="sent")
    return Response({"message": RESET_REQUEST_MESSAGE})


# ==========================================
# IKKI BOSQICHLI KIRISH (2FA, email kod)
# ==========================================

# Bitta akkauntga soatiga ko'pi bilan shuncha kod: har kodga 5 urinish bilan 6 xonali kodni taxmin qilib topish
# imkoniyati soatiga 25 / 1 000 000 dan oshmaydi, pochta ham xatga ko'milmaydi
LOGIN_CODE_MAX_PER_HOUR = 5
LOGIN_CODE_LIMIT_MESSAGE = "Juda ko'p kod so'raldi. Bir soatdan keyin qayta urinib ko'ring."
LOGIN_CODE_INVALID_MESSAGE = "Kod noto'g'ri yoki muddati o'tgan. Qaytadan kirib, yangi kod oling."
LOGIN_CODE_PURPOSES = {
    "login": ("Moliya — kirish kodi", "Hisobingizga kirish kodi",
              "Agar hozir kirmoqchi bo'lmagan bo'lsangiz, parolingizni darhol almashtiring — uni kimdir biladi."),
    "enable": ("Moliya — ikki bosqichli himoyani yoqish", "Ikki bosqichli himoyani yoqish kodi",
               "Agar buni siz so'ramagan bo'lsangiz, bu xatni e'tiborsiz qoldiring."),
    "email": ("Moliya — yangi elektron pochtani tasdiqlash", "Yangi elektron pochtani tasdiqlash kodi",
              "Agar buni siz so'ramagan bo'lsangiz, bu xatni e'tiborsiz qoldiring — elektron pochta almashtirilmaydi."),
}


def mask_email(email):
    """ab***@gmail.com — kod qaysi pochtaga ketganini eslatadi, manzilni to'liq oshkor qilmaydi"""
    name, _, domain = (email or "").partition("@")
    return f"{name[:2]}***@{domain}"


def _send_login_code_mail(user_id, email, name, code, code_id, purpose):
    subject, lead, warning = LOGIN_CODE_PURPOSES[purpose]
    minutes = LoginCode.CODE_LIFETIME_MINUTES
    try:
        send_mail(
            subject=subject,
            message=f"Assalomu alaykum, {name}!\n\n{lead}: {code}\n\nKod {minutes} daqiqa amal qiladi. {warning}\n\n"
                    "Hurmat bilan,\nMoliya",
            html_message=format_html(
                '<div style="font-family:Arial,sans-serif;font-size:15px;color:#1f2937;line-height:1.5">'
                "<p>Assalomu alaykum, {}!</p><p>{}:</p>"
                '<p style="font-size:28px;font-weight:bold;letter-spacing:4px;margin:8px 0">{}</p>'
                "<p>Kod {} daqiqa amal qiladi. {}</p>"
                '<p style="color:#6b7280">Hurmat bilan,<br>Moliya</p></div>',
                name, lead, code, minutes, warning,
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )
    except Exception:
        logger.exception("Kirish kodi xatini yuborib bo'lmadi (user_id=%s)", user_id)
        # Ketmagan kod soatlik limitni bekorga band qilmasin
        LoginCode.objects.filter(pk=code_id).delete()


def _issue_login_code(user, purpose, email=None):
    """Yangi kod yaratib elektron pochtaga yuboradi va token qaytaradi; soatlik limit tugagan bo'lsa None.
    Oldingi ishlatilmagan kodlar bekor qilinadi — amalda faqat oxirgi xatdagi kod ishlaydi.
    elektron pochta berilsa (hisob elektron pochtasini almashtirish) kod o'sha yangi manzilga ketadi va kod bilan birga saqlanadi"""
    now = timezone.now()
    if user.login_codes.filter(created_at__gte=now - timedelta(hours=1)).count() >= LOGIN_CODE_MAX_PER_HOUR:
        return None
    code = f"{secrets.randbelow(1_000_000):06d}"
    with transaction.atomic():
        user.login_codes.filter(used=False).update(used=True)
        login_code = LoginCode.objects.create(
            user=user,
            token=secrets.token_urlsafe(32),
            code_hash=make_password(code),
            new_email=email or None,
            expires_at=now + timedelta(minutes=LoginCode.CODE_LIFETIME_MINUTES),
        )
    _run_in_background(
        _send_login_code_mail, user.pk, email or user.email, user.first_name or user.username, code, login_code.pk, purpose,
    )
    return login_code.token


def _use_login_code(request, token, code, user=None, email_change=False):
    """Kodni tekshiradi va ishlatilgan deb belgilaydi. Natija: (login_code, None) yoki (None, xato javobi).
    user berilsa (sozlamalardan yoqish) kod faqat o'sha foydalanuvchiniki bo'lishi kerak.
    Kod maqsadlari ajratilgan: elektron pochta_change=True faqat elektron pochtani almashtirish kodini (new_elektron pochta bor), False esa
    kirish/yoqish kodlarini qabul qiladi — biri ikkinchisining o'rniga ishlamaydi"""
    invalid = Response({"code": LOGIN_CODE_INVALID_MESSAGE}, status=status.HTTP_400_BAD_REQUEST)
    token, code = str(token or "").strip(), str(code or "").strip()
    login_code = LoginCode.objects.select_related("user").filter(token=token).first() if token else None
    now = timezone.now()
    if (login_code is None or login_code.used or now >= login_code.expires_at or not login_code.user.is_active
            or (user is not None and login_code.user_id != user.pk)
            or bool(login_code.new_email) != email_change):
        return None, invalid
    # Urinish kodni tekshirishdan OLDIN band qilinadi: login_code.attempts parallel so'rovlarda eskirgan bo'lishi
    # mumkin, shuning uchun limit bazadagi shartli yangilashda tekshiriladi (aks holda hamma so'rov 0 ni ko'rib,
    # 5 tadan ko'p variant sinab ko'rardi). To'g'ri kod ham bitta urinish sarflaydi — 5-urinish baribir ishlaydi
    reserved = LoginCode.objects.filter(
        pk=login_code.pk, used=False, attempts__lt=login_code.MAX_ATTEMPTS, expires_at__gt=now,
    ).update(attempts=F("attempts") + 1)
    if not reserved:
        return None, invalid
    if not re.fullmatch(r"\d{6}", code) or not login_code.check_code(code):
        attempts = LoginCode.objects.filter(pk=login_code.pk).values_list("attempts", flat=True).first() or 0
        left = login_code.MAX_ATTEMPTS - attempts
        log_event("login_code_failed", request, logging.WARNING, user_id=login_code.user_id, left=left)
        if left <= 0:
            return None, invalid
        return None, Response({"code": f"Kod noto'g'ri. Yana {left} ta urinish qoldi."},
                              status=status.HTTP_400_BAD_REQUEST)
    # Shartli yangilash: bir kod ikki parallel so'rovda ikki marta ishlatilmasin
    if not LoginCode.objects.filter(pk=login_code.pk, used=False).update(used=True):
        return None, invalid
    return login_code, None


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes(AUTH_THROTTLES)
@enforce_csrf
def login_2fa_api(request):
    """Kirishning 2-qadami: paroldan keyin elektron pochtaga kelgan kod"""
    login_code, problem = _use_login_code(request, request.data.get("token"), request.data.get("code"))
    if problem:
        return problem
    user = login_code.user
    login(request, user, backend=settings.AUTHENTICATION_BACKENDS[0])
    log_event("login_2fa_ok", request, user_id=user.pk, username=user.username)
    return Response({"message": "Muvaffaqiyatli tizimga kirildi", "user": user_payload(user)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes(AUTH_THROTTLES)
def two_factor_api(request):
    """Sozlamalar: ikki bosqichli himoyani yoqish yoki o'chirish (joriy parol bilan).
    Yoqish darhol emas: elektron pochtaga kod ketadi va two_factor_confirm_api tasdiqlaydi — elektron pochta xato yozilgan bo'lsa,
    foydalanuvchi o'zini hisobdan qulflab qo'ymasligi uchun"""
    user = request.user
    problem = current_password_problem(user, password_from(request, "password"), "password")
    if problem:
        return problem
    enabled = request.data.get("enabled") in (True, "true", "1", 1)
    if not enabled:
        user.two_factor_enabled = False
        user.save(update_fields=["two_factor_enabled"])
        log_event("two_factor_disabled", request, user_id=user.pk)
        return Response({"message": "Ikki bosqichli himoya o'chirildi", "user": user_payload(user)})
    if not user.email:
        return Response({"error": "Avval Profil bo'limida elektron pochta kiriting — kod o'sha elektron pochtaga keladi"},
                        status=status.HTTP_400_BAD_REQUEST)
    token = _issue_login_code(user, "enable")
    if token is None:
        return Response({"error": LOGIN_CODE_LIMIT_MESSAGE}, status=status.HTTP_429_TOO_MANY_REQUESTS)
    return Response({"token": token, "email": mask_email(user.email), "message": "Elektron pochtangizga tasdiqlash kodi yuborildi"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes(AUTH_THROTTLES)
def two_factor_confirm_api(request):
    """Yoqishni elektron pochtaga kelgan kod bilan tasdiqlash"""
    user = request.user
    _, problem = _use_login_code(request, request.data.get("token"), request.data.get("code"), user=user)
    if problem:
        return problem
    user.two_factor_enabled = True
    user.save(update_fields=["two_factor_enabled"])
    log_event("two_factor_enabled", request, user_id=user.pk)
    return Response({"message": "Ikki bosqichli himoya yoqildi", "user": user_payload(user)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes(AUTH_THROTTLES)
def confirm_email_api(request):
    """2FA yoqiq hisobda elektron pochta almashtirishni yangi manzilga kelgan kod bilan tasdiqlash.
    Yangi elektron pochta so'rovdan emas, kod bilan birga saqlangan qiymatdan olinadi"""
    user = request.user
    login_code, problem = _use_login_code(
        request, request.data.get("token"), request.data.get("code"), user=user, email_change=True,
    )
    if problem:
        return problem
    new_email = login_code.new_email
    # Kod yuborilgandan keyin bu manzilni boshqa akkaunt band qilib olgan bo'lishi mumkin
    email_error = validate_email_uz(new_email, exclude_pk=user.pk)
    if email_error:
        return Response({"email": email_error}, status=status.HTTP_400_BAD_REQUEST)
    user.email = new_email
    try:
        with transaction.atomic():
            user.save(update_fields=["email"])
            user.password_reset_codes.filter(used=False).update(used=True)
    except IntegrityError:
        return Response({"email": "Bu elektron pochta boshqa hisobda ishlatilgan"}, status=status.HTTP_400_BAD_REQUEST)
    log_event("email_changed", request, user_id=user.pk)
    return Response({"message": "Elektron pochta yangilandi", "user": user_payload(user)})


@lru_cache(maxsize=1)
def _dummy_reset_hash():
    return make_password("000000")


def _check_reset_code(request, identifier, code):
    """Kodni tekshiradi. Natija: (user, None) yoki (None, xato javobi). Barcha muvaffaqiyatsizliklarga javob bir xil
    (RESET_CODE_INVALID_MESSAGE), sababi esa faqat xavfsizlik logiga yoziladi.
    Noto'g'ri kod urinishlar sonini oshiradi — kodni topib olish uchun ko'p urinib bo'lmaydi"""
    invalid = Response({"code": RESET_CODE_INVALID_MESSAGE}, status=status.HTTP_400_BAD_REQUEST)

    def fail(reason, user=None):
        # Kod xeshini tekshirish sekin: u faqat faol kodli akkauntda bajarilsa, javob vaqti akkaunt borligini
        # oshkor qilardi. Qolgan holatlarda xuddi shunday og'irlikdagi soxta tekshiruv bajariladi
        if reason != "wrong_code":
            check_password(code, _dummy_reset_hash())
        log_event("password_reset_code_failed", request, logging.WARNING,
                  identifier=identifier, user_id=user.pk if user else None, reason=reason)
        return None, invalid

    user = find_user_by_login(identifier)
    if user is None or not user.is_active:
        return fail("no_account")

    reset = user.password_reset_codes.filter(used=False).first()
    if reset is None or not reset.is_usable:
        return fail("no_active_code", user)

    # Urinish kod tekshirilishidan OLDIN atomik band qilinadi: bir vaqtda yuborilgan ko'p so'rov bilan
    # bitta kod uchun MAX_ATTEMPTS dan ortiq variant sinab bo'lmaydi
    codes = PasswordResetCode.objects.filter(pk=reset.pk)
    reserved = codes.filter(used=False, attempts__lt=PasswordResetCode.MAX_ATTEMPTS).update(attempts=F("attempts") + 1)
    if not reserved:
        return fail("attempts_exhausted", user)

    if reset.check_code(code):
        # To'g'ri kod urinish hisoblanmaydi (tekshiruv va yangi parol bosqichlari uchun ham)
        codes.update(attempts=F("attempts") - 1)
        return user, None

    return fail("wrong_code", user)


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes(AUTH_THROTTLES)
@enforce_csrf
def password_reset_verify_api(request):
    """2-qadam: elektron pochtaga kelgan kodni tekshirish (kod hali ishlatilmaydi — yangi parol bilan 3-qadamda yuboriladi)"""
    identifier = str(request.data.get("username") or "").strip()
    code = str(request.data.get("code") or "").strip()
    if not identifier or not code:
        return Response({"error": "Kod kiritilishi shart"}, status=status.HTTP_400_BAD_REQUEST)

    user, error = _check_reset_code(request, identifier, code)
    if error:
        return error
    return Response({"message": "Kod tasdiqlandi"})


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes(AUTH_THROTTLES)
@enforce_csrf
def password_reset_confirm_api(request):
    """3-qadam: tasdiqlangan kod bilan yangi parol o'rnatish"""
    identifier = str(request.data.get("username") or "").strip()
    code = str(request.data.get("code") or "").strip()
    new_password = password_from(request, "new_password")

    if not identifier or not code or not new_password:
        return Response({"error": "Kod va yangi parol kiritilishi shart"}, status=status.HTTP_400_BAD_REQUEST)

    user, error = _check_reset_code(request, identifier, code)
    if error:
        return error

    try:
        validate_password(new_password, user=user)
    except DjangoValidationError as e:
        return Response({"new_password": password_errors_uz(e)}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        user.set_password(new_password)
        user.save(update_fields=["password"])
        user.password_reset_codes.filter(used=False).update(used=True)
    # Parol tiklangach eski noto'g'ri urinishlar tufayli kirish to'sib qolmasin
    clear_login_fails(user.username, user.email, identifier, request=request)
    log_event("password_reset_confirmed", request, user_id=user.pk, username=user.username)

    return Response({"message": "Parol yangilandi. Endi yangi parol bilan tizimga kiring."})


# ==========================================
# STATISTIKA: HAR XIL VALYUTALARNI SO'MGA O'GIRISH
# ==========================================
# Daromad/harajat summasi hamyon valyutasida saqlanadi. Statistikada ular oddiy qo'shilsa
# 100 USD 100 so'm bo'lib qoladi — shuning uchun valyuta bo'yicha guruhlab, Markaziy bank
# kursida so'mga o'giramiz va shundan keyin jamlaymiz/saralaymiz. Kurs operatsiya yozilgan paytda qatorning
# o'zida saqlanadi (uzs_rate) — o'tgan oylar jami kun sayin o'zgarib ketmasin; kursi saqlanmagan (NULL)
# qatorlar bugungi kurs bilan o'giriladi.

STATS_CURRENCY = "UZS"


def sum_groups_in_uzs(converter, qs, group_fields=(), currency_field="wallet__currency"):
    """qs miqdorlarini group_fields bo'yicha guruhlab so'mga o'giradi.
    {kalit: {"uzs": Decimal, "parts": {valyuta: asl_miqdor}}} qaytaradi (kalit — group_fields qiymatlari kortej).
    Qator o'z saqlangan kursi (uzs_rate) bilan o'giriladi, kursi yo'q (NULL) qator — bugungi kurs bilan.
    Guruhlash uzs_rate bo'yicha ham ketadi: miqdor SQL'da yig'iladi, ko'paytma esa Python
    Decimal'da — SQLite'da Sum(miqdor * kurs) float bo'lib, 15 xonadan keyin xonalarni yo'qotardi.
    Sum() ham SQLite'da float: natija 2 xonaga yaxlitlanadi (float xatosi 0.30000000000000004 ko'rinmasin).
    So'rovlar soni o'zgarmaydi (bitta so'rov), qatorlar soni esa kurs o'zgargan kunlar bilan cheklangan"""
    groups = {}
    rows = qs.values(*group_fields, currency_field, "uzs_rate").annotate(s=Sum("summa")).order_by()
    for row in rows:
        key = tuple(row[f] for f in group_fields)
        cur = normalize_currency(row[currency_field]) or STATS_CURRENCY
        group = groups.setdefault(key, {"uzs": Decimal(0), "parts": {}})
        group["parts"][cur] = group["parts"].get(cur, 0) + quantize_money(row["s"] or 0)
        if row["uzs_rate"] is not None:
            converted = Decimal(row["s"] or 0) * row["uzs_rate"]
        else:
            converted = converter.to_uzs(row["s"], cur)
        if converted is not None:
            group["uzs"] += converted
    return groups


def total_in_uzs(converter, qs):
    group = sum_groups_in_uzs(converter, qs).get(())
    return round_amount(group["uzs"]) if group else round_amount(0)


def currency_parts(parts):
    """{"USD": 100, "UZS": 5000} -> [{"currency": "UZS", "total": 5000}, {"currency": "USD", "total": 100}]"""
    return [
        {"currency": cur, "total": total}
        for cur, total in sorted(parts.items(), key=lambda item: (item[0] != STATS_CURRENCY, item[0]))
    ]


def category_breakdown_in_uzs(converter, qs, empty_name):
    """Turkumlar bo'yicha so'mdagi jami (kattasidan kichigiga) va umumiy miqdor.
    Masalan: Oylik 1 000 000 UZS va Boshqa daromad 100 USD (~1 180 000 UZS) -> Boshqa daromad birinchi"""
    groups = sum_groups_in_uzs(converter, qs, ("category__id", "category__name"))
    total = round_amount(sum((g["uzs"] for g in groups.values()), Decimal(0)))
    items = []
    for (cat_id, cat_name), group in groups.items():
        amount = round_amount(group["uzs"])
        items.append({
            "id": cat_id,
            "name": cat_name or empty_name,
            "total": amount,
            "percent": round(amount / total * 100, 1) if total > 0 else 0,
            # Asl valyutadagi summalar — "100 USD ≈ 1 180 919 UZS" ko'rinishida chiqarish uchun
            "parts": currency_parts(group["parts"]),
        })
    items.sort(key=lambda item: (-item["total"], item["name"]))
    return items, total


def percent_change(current, previous):
    return round((current - previous) / previous * 100, 1) if previous > 0 else None


def deleted_wallet_response(*wallets, verb="bekor qilib"):
    """O'chirilgan hamyon qoldig'iga tegadigan bekor qilish (destroy) yoki tahrirlash (update) rad etiladi: aks holda
    xarajat puli ko'rinmaydigan hamyonga qaytib "yo'qolardi", kirim yoki o'tkazmada esa tushunarsiz
    "mablag' yetarli emas" xatosi chiqardi, tahrir esa pulni ko'rinmaydigan hamyonga o'tkazib yuborardi"""
    if any(wallet is not None and not wallet.status for wallet in wallets):
        return Response({
            "error": f"Bu yozuv o'chirilgan hamyonga tegishli — uni {verb} bo'lmaydi "
                     "(pul ko'rinmaydigan hamyonga o'tib qolardi)."
        }, status=status.HTTP_400_BAD_REQUEST)
    return None


class RestoreMixin:
    """O'chirilgan (status=False) daromad / xarajat / o'tkazmani qaytarish — "O'chirildi · Qaytarish" tugmasi uchun.
    Yozuv qayta faol qilinib save() qilinadi: model eski (bo'sh) va yangi effektlar farqini hamyonga o'zi qo'llaydi,
    shuning uchun qoldiq tekshiruvi ham odatdagidek ishlaydi (xarajat puli boshqa joyga sarflangan bo'lsa — xato)"""
    restore_wallet_fields = ("wallet",)

    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        model = self.get_queryset().model
        record_pk = strict_int(pk)
        instance = model.objects.filter(pk=record_pk, user=request.user, status=False).first() if record_pk else None
        if instance is None:
            return Response({"error": "O'chirilgan yozuv topilmadi"}, status=status.HTTP_404_NOT_FOUND)
        problem = deleted_wallet_response(*(getattr(instance, f) for f in self.restore_wallet_fields), verb="qaytarib")
        if problem:
            return problem
        instance.status = True
        try:
            instance.save()
        except (ValueError, DjangoValidationError, DRFValidationError) as e:
            return Response({"error": error_text(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(instance).data)


# Statistikada sana oralig'ining eng katta uzunligi (kun): cheksiz oraliq serverni og'irlashtirmasin
MAX_RANGE_DAYS = 366
# date.fromisoformat Python 3.11+ da "20261005" va "2026-W41-1" ni ham qabul qiladi — faqat YYYY-MM-DD ruxsat etiladi
ISO_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def parse_date_param(value):
    """"2026-10-05" (YYYY-MM-DD) ni date ga o'giradi. Noto'g'ri qiymat (abc, 2026-13-40, 20261005) yoki
    MIN_YEAR..MAX_YEAR dan tashqari yil None qaytaradi — 500 xato o'rniga e'tiborsiz qoldiriladi"""
    if not value or not ISO_DATE_RE.fullmatch(value):
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if MIN_YEAR <= parsed.year <= MAX_YEAR else None


def parse_date_range(params):
    """?date_from=...&date_to=... -> (boshi, oxiri); berilmagan yoki noto'g'ri chegara None bo'ladi.
    Boshi oxiridan katta bo'lsa o'rinlari almashtiriladi — sanalar teskari tanlansa ham javob chiqadi"""
    start = parse_date_param(params.get("date_from"))
    end = parse_date_param(params.get("date_to"))
    if start and end and start > end:
        start, end = end, start
    return start, end


def parse_int_param(value):
    """"2026" -> 2026; boshqa hamma narsa (abc, ²) None. Faqat ASCII raqamlar: "²".isdigit() True, lekin int("²") ValueError
    beradi (500 xato). 4300+ xonali raqam ham int() da ValueError — u ham None"""
    try:
        return int(value) if value.isascii() and value.isdigit() else None
    except ValueError:
        return None


def filter_by_period(qs, params):
    """Amallarni davr bo'yicha filtrlaydi ("Barcha amallar" sahifasi).
    ?date_from=2026-10-01&date_to=2026-10-31 — ikkala kun ham kiradi; bittasi berilsa oraliq bir tomonga ochiq.
    To'g'ri chegara bo'lsa ?year=&month= e'tiborga olinmaydi. Kun mahalliy vaqt bo'yicha (TruncDay bilan bir xil).
    Noto'g'ri qiymat (masalan ?year=abc) 500 xato o'rniga e'tiborsiz qoldiriladi"""
    start, end = parse_date_range(params)
    if start or end:
        if start:
            qs = qs.filter(date__date__gte=start)
        if end:
            qs = qs.filter(date__date__lte=end)
        return qs
    year = parse_int_param(params.get("year", ""))
    month = parse_int_param(params.get("month", ""))
    if year is not None and MIN_YEAR <= year <= MAX_YEAR:
        qs = qs.filter(date__year=year)
    if month is not None and 1 <= month <= 12:
        qs = qs.filter(date__month=month)
    return qs


# ==========================================
# REST API VIEWSETS (Multi-tenant / User-scoped)
# ==========================================

class UnicodeSearchFilter(SearchFilter):
    """SearchFilter bilan bir xil (so'zlar AND, maydonlar OR), lekin kirillcha katta-kichik harfni farqlaydi:
    SQLite icontains faqat ASCII'ni tushiradi, shuning uchun "али" so'rovi "Али"ni topmasdi.
    Oddiy maydonlar Casefold() orqali qidiriladi; search_key_fields dagi maydon tayyor kalit ustuni bo'yicha
    (username -> username_key: u indeksli va allaqachon NFKC + casefold). Bog'lanish yoki ^ = @ $ prefiksli maydonlar
    oddiy SearchFilter qoidasi bilan qoladi"""
    search_key_fields = {"username": "username_key"}

    def filter_queryset(self, request, queryset, view):
        search_fields = self.get_search_fields(view, request)
        search_terms = self.get_search_terms(request)
        if not search_fields or not search_terms:
            return queryset

        def condition(field, term):
            if field in self.search_key_fields:
                return Q(**{f"{self.search_key_fields[field]}__contains": fold(term)})
            if field[0] in self.lookup_prefixes or "__" in field:
                return Q(**{self.construct_search(str(field), queryset): term})
            return casefold_contains_q([field], term)

        for term in search_terms:
            term_q = Q()
            for field in search_fields:
                term_q |= condition(field, term)
            queryset = queryset.filter(term_q)
        return queryset


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.filter(status=True)
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend, UnicodeSearchFilter, OrderingFilter]
    filterset_fields = ["status", "is_active"]
    search_fields = ["username", "first_name", "last_name", "email", "phone"]
    ordering_fields = ["id", "username", "date_joined"]
    ordering = ["-id"]

    def create(self, request, *args, **kwargs):
        # Oddiy foydalanuvchi boshqa akkaunt yarata olmasin — ro'yxatdan o'tish /auth/register/ orqali
        if not (request.user.is_staff or request.user.is_superuser):
            return Response(
                {"error": "Yangi foydalanuvchini faqat administrator qo'sha oladi"},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        self.save_or_username_taken(serializer)

    def perform_update(self, serializer):
        self.save_or_username_taken(serializer)

    @staticmethod
    def save_or_username_taken(serializer):
        """Tekshiruvdan o'tgan, lekin INSERT/UPDATE paytida boshqa so'rov shu nomni band qilib ulgurgan holat (parallel
        so'rovlar): 500 xato o'rniga 400. atomic() — xato tashqi tranzaksiyani buzmasligi va yaratish + parol
        o'rnatish birga bajarilishi uchun"""
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError as exc:
            if not is_username_conflict(exc):
                raise
            raise DRFValidationError({"username": USERNAME_TAKEN_MESSAGE})

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return User.objects.none()
        if self.request.user.is_superuser:
            return User.objects.filter(status=True)
        if self.request.user.is_staff and self.request.user.has_perm("mainapp.view_user"):
            # Oddiy xodim superuser akkauntini ko'ra ham, o'zgartira ham, o'chira ham olmaydi (404): aks holda u
            # superuser emailini o'zinikiga almashtirib, "Parolni unutdingizmi?" orqali akkauntni egallab olardi
            return User.objects.filter(status=True, is_superuser=False)
        return User.objects.filter(id=self.request.user.id, status=True)

    def update(self, request, *args, **kwargs):
        # Oddiy foydalanuvchi profilini faqat /auth/profile/ orqali o'zgartiradi: u yerda email
        # o'zgarishi joriy parol bilan tasdiqlanadi. Bu yerda esa parolsiz o'zgartirib bo'lardi
        if not request.user.is_staff:
            return Response(
                {"error": "Profilni Sozlamalar orqali o'zgartiring (/api/v1/auth/profile/)"},
                status=status.HTTP_403_FORBIDDEN
            )
        denied = self.staff_denied(request, "change_user", "o'zgartira")
        if denied:
            return denied
        return super().update(request, *args, **kwargs)

    def staff_denied(self, request, perm, verb):
        """Boshqa akkauntga tegish: superuser bo'lmagan xodimga mainapp.<perm> huquqi kerak, va u boshqa xodim
        akkauntiga umuman tega olmaydi — aks holda huquqsiz xodim emailni almashtirib, "Parolni unutdingizmi?"
        orqali boshqa akkauntni egallab olardi. O'z akkaunti bundan mustasno. Ruxsat bo'lsa None"""
        user = request.user
        if user.is_superuser:
            return None
        target = self.get_object()
        if target.pk == user.pk:
            return None
        if not user.has_perm(f"mainapp.{perm}"):
            return Response({"error": "Bu amal uchun sizda ruxsat yo'q"}, status=status.HTTP_403_FORBIDDEN)
        if target.is_staff:
            return Response({"error": f"Xodim hisobini faqat superuser {verb} oladi"},
                            status=status.HTTP_403_FORBIDDEN)
        return None

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_staff:
            # Akkaunt faqat parol bilan o'chiriladi (/auth/delete-account/) — sessiyani qo'lga kiritgan
            # odam bu yerdan parolsiz o'chira olmasligi uchun
            return Response(
                {"error": "Hisobni Sozlamalar orqali parol bilan o'chiring (/api/v1/auth/delete-account/)"},
                status=status.HTTP_403_FORBIDDEN
            )
        denied = self.staff_denied(request, "delete_user", "o'chira")
        if denied:
            return denied
        instance = self.get_object()
        is_self = instance.pk == request.user.pk
        if is_self:
            logout(request)
        self.perform_destroy(instance)  # User.delete(): qator va bog'langan hamma narsa butunlay o'chadi
        return Response({"message": "Hisob o'chirildi"}, status=status.HTTP_200_OK)


class CanEditCategory(BasePermission):
    """O'qish hammaga ochiq. Yaratish - tizimga kirgan foydalanuvchiga (shaxsiy turkum).
    O'zgartirish va o'chirish hammaga ruxsat, lekin umumiy turkumda natija turlicha:
    admin uni hamma uchun o'zgartiradi, oddiy foydalanuvchiga esa shaxsiy nusxa yaratiladi
    (qarang: PersonalCategoryMixin.update / destroy). Begona shaxsiy turkum querysetda yo'q — 404"""

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS or request.method == "DELETE" or obj.user_id is None:
            return True
        return obj.user_id == request.user.id


class PersonalCategoryMixin:
    """Umumiy turkumlar hammaga ko'rinadi; foydalanuvchi qo'shganlari faqat o'ziga.
    Har bir foydalanuvchi keraksiz turkumlarni o'z ro'yxatidan olib tashlay oladi"""
    permission_classes = [CanEditCategory]
    hidden_field = ""  # User'dagi yashirilgan toifalar maydoni
    operations_model = None  # Shu toifadagi operatsiyalar modeli (Income / Expense)

    def get_permissions(self):
        if self.action == "restore":
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return qs.filter(user__isnull=True)
        hidden_ids = list(getattr(user, self.hidden_field).values_list("pk", flat=True))
        qs = qs.filter(Q(user__isnull=True) | Q(user=user)).annotate(
            hidden=Case(When(pk__in=hidden_ids, then=Value(True)), default=Value(False), output_field=BooleanField())
        )
        if self.action == "list":
            # Ro'yxatda yashirilganlar chiqmaydi (sozlash oynasi ?include_hidden=1 bilan hammasini oladi)
            if self.request.query_params.get("include_hidden") != "1":
                qs = qs.exclude(pk__in=hidden_ids)
            # Nomi o'zgartirilgan umumiy toifa "o'chirilganlar" orasida ham chiqmaydi — o'rnida shaxsiy nusxasi bor.
            # Nusxa o'chirilsa, asl toifa yana qaytarish uchun ko'rinadi
            replaced_ids = qs.model.objects.filter(user=user, status=True, replaces__isnull=False).values_list("replaces_id", flat=True)
            qs = qs.exclude(pk__in=list(replaced_ids))
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def update(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.user_id is None and not request.user.is_staff:
            return self._personalize_global(request, obj)
        return super().update(request, *args, **kwargs)

    def _personalize_global(self, request, global_cat):
        """Umumiy turkum hammaniki: oddiy foydalanuvchi uni o'zgartirsa boshqalarga tegmaydi.
        Unga yangi nomli shaxsiy nusxa yaratiladi, uning shu turkumdagi amallari nusxaga o'tadi,
        umumiy turkum esa faqat uning ro'yxatidan yashiriladi — foydalanuvchi uchun bu oddiy nom almashtirish"""
        editable = ("name", "description", "icon")
        data = {field: getattr(global_cat, field) for field in editable}
        data.update({field: request.data[field] for field in editable if field in request.data})
        if all(data[field] == getattr(global_cat, field) for field in editable):
            return Response(self.get_serializer(global_cat).data)

        context = {**self.get_serializer_context(), "replaces_pk": global_cat.pk}
        serializer = self.get_serializer(data=data, context=context)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            copy = serializer.save(user=request.user, replaces=global_cat)
            # .update() — balans o'zgarmaydi (Income/Expense.save chaqirilmaydi), faqat toifa almashadi
            self.operations_model.objects.filter(user=request.user, category=global_cat).update(category=copy)
            getattr(request.user, self.hidden_field).add(global_cat)
        return Response(self.get_serializer(copy).data)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.user_id == request.user.id:
            # O'zi qo'shgan toifa: operatsiyalar tarixi saqlanishi uchun o'chirilmaydi, faol emas deb belgilanadi
            obj.status = False
            obj.save(update_fields=["status"])
        else:
            # Umumiy toifa: faqat shu foydalanuvchining ro'yxatidan olib tashlanadi
            getattr(request.user, self.hidden_field).add(obj)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        """Olib tashlangan umumiy turkumni ro'yxatga qaytarish"""
        obj = self.get_object()
        getattr(request.user, self.hidden_field).remove(obj)
        return Response({"message": "Turkum qaytarildi"})


class CategoryViewSet(PersonalCategoryMixin, viewsets.ModelViewSet):
    """Kirim turkumlari (Oylik, Freelance, Sovg'a...)"""
    hidden_field = "hidden_income_categories"
    operations_model = Income
    queryset = Category.objects.filter(status=True)
    serializer_class = CategorySerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status"]
    search_fields = ["name", "description"]
    ordering_fields = ["id", "name", "created_at"]
    ordering = ["name"]


class ExpenseCategoryViewSet(PersonalCategoryMixin, viewsets.ModelViewSet):
    """Chiqim turlari (Ovqat, Transport, Kiyim...)"""
    hidden_field = "hidden_expense_categories"
    operations_model = Expense
    queryset = ExpenseCategory.objects.filter(status=True)
    serializer_class = ExpenseCategorySerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status"]
    search_fields = ["name", "description"]
    ordering_fields = ["id", "name", "created_at"]
    ordering = ["name"]


class WalletViewSet(viewsets.ModelViewSet):
    queryset = Wallet.objects.filter(status=True)
    serializer_class = WalletSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["currency", "status"]
    search_fields = ["name"]
    ordering_fields = ["id", "name", "summa", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Wallet.objects.none()
        # select_related("user"): serializer har qatorda user.username ni o'qiydi (N+1 bo'lmasin)
        return Wallet.objects.filter(status=True, user=self.request.user).select_related("user")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        # Qoldiq ham tahrirlanadi: qator qulflanadi, shunda shu paytdagi parallel kirim/chiqim yangi summani
        # eskirgan nusxa bilan ustidan yozib yubormaydi
        with transaction.atomic():
            Wallet.objects.select_for_update().filter(pk=serializer.instance.pk).first()
            serializer.save()

    def destroy(self, request, *args, **kwargs):
        wallet_pk = self.get_object().pk  # begona / o'chirilgan hamyon uchun 404
        try:
            # Tekshiruvlar va o'chirish bitta tranzaksiyada (SQLite'da u darrov yozuv qulfini oladi): aks holda tekshiruvdan
            # keyin tushgan kirim pulni o'chirilgan hamyonda qoldirardi, ikki parallel so'rov esa "oxirgi hamyon" qoidasini
            # chetlab ikkala hamyonni ham o'chira olardi
            with transaction.atomic():
                instance = Wallet.objects.select_for_update().filter(pk=wallet_pk, user=request.user, status=True).first()
                if instance is None:
                    return Response({"error": "Hamyon topilmadi"}, status=status.HTTP_404_NOT_FOUND)
                if instance.is_goal:
                    return Response({
                        "error": "Bu maqsad hamyoni. Uni Maqsadlar bo'limida maqsad bilan birga o'chiring."
                    }, status=status.HTTP_400_BAD_REQUEST)
                # Maqsad hamyonidan chiqim/kirim qilib bo'lmaydi: oddiy hamyon qolmasa Chiqim/Kirim oynasi bo'sh qolardi
                if not Wallet.objects.filter(user_id=instance.user_id, status=True, is_goal=False).exclude(pk=instance.pk).exists():
                    return Response({
                        "error": "Bu oxirgi hamyoningiz — o'chirib bo'lmaydi. Avval boshqa hamyon oching."
                    }, status=status.HTTP_400_BAD_REQUEST)
                # Puli bor hamyon o'chirilsa pul umumiy hisobdan yo'qolardi; ochiq qarz o'chirilganda esa
                # qoldig'i o'chirilgan (ko'rinmaydigan) hamyonga qaytardi
                if instance.summa != 0:
                    return Response({
                        "error": f"Hamyonda {format_money(instance.summa)} {instance.currency} bor. O'chirishdan oldin pulni "
                                 "O'tkazma orqali boshqa hamyonga o'tkazing."
                    }, status=status.HTTP_400_BAD_REQUEST)
                if instance.debts.filter(status=True, is_settled=False).exists():
                    return Response({
                        "error": "Bu hamyonga to'lanmagan qarz bog'langan. Avval qarzni yoping yoki o'chiring."
                    }, status=status.HTTP_400_BAD_REQUEST)
                self.perform_destroy(instance)
            return Response({"message": "Hamyon muvaffaqiyatli o'chirildi"}, status=status.HTTP_200_OK)
        except (ValueError, DjangoValidationError, DRFValidationError) as e:
            return Response({"error": error_text(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """Umumiy moliyaviy hisobot (qoldiq, daromad, xarajat, qarzlar)"""
        if not request.user.is_authenticated:
            return Response(
                {"error": "Autentifikatsiyadan o'tilmagan"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        user = request.user
        wallets_qs = Wallet.objects.filter(status=True, user=user)
        incomes_qs = Income.objects.filter(status=True, user=user)
        expenses_qs = Expense.objects.filter(status=True, user=user)
        debts_qs = Debt.objects.filter(status=True, user=user)

        now = timezone.localtime()  # Toshkent vaqti: oy/hafta chegarasi UTC bilan siljimasligi uchun
        month_incomes = incomes_qs.filter(date__year=now.year, date__month=now.month)
        month_expenses = expenses_qs.filter(date__year=now.year, date__month=now.month)

        # Turli valyutalarni qo'shib bo'lmaydi: balans valyuta bo'yicha alohida hisoblanadi (UZS birinchi)
        balances_by_currency = sorted(
            (
                {"currency": row["cur"], "total": quantize_money(row["total"] or 0)}
                for row in wallets_qs.annotate(cur=Upper("currency")).values("cur").annotate(total=Sum("summa")).order_by()
            ),
            key=lambda b: (b["currency"] != "UZS", b["currency"]),
        )
        # Daromad/harajat/qarz summalari Markaziy bank kursi bo'yicha so'mga o'girib jamlanadi
        converter = UzsConverter()
        total_income = total_in_uzs(converter, incomes_qs)
        total_expense = total_in_uzs(converter, expenses_qs)
        monthly_income = total_in_uzs(converter, month_incomes)

        # Qarzlar statistikasi (har bir qarz o'z valyutasida)
        def open_debts_in_uzs(debt_type):
            total = Decimal(0)
            for debt in debts_qs.filter(debt_type=debt_type, is_settled=False):
                converted = converter.to_uzs(debt.remaining_summa, debt.currency)
                if converted is not None:
                    total += converted
            return round_amount(total)

        total_given = open_debts_in_uzs("give")
        total_taken = open_debts_in_uzs("take")

        # Muddati o'tgan / yaqinlashgan qarzlar (ochiq va due_date belgilangan)
        DEBT_DUE_SOON_DAYS = 3
        today = now.date()
        soon_cutoff = today + timedelta(days=DEBT_DUE_SOON_DAYS)
        open_debts_with_due = debts_qs.filter(is_settled=False, due_date__isnull=False)
        debts_overdue_count = open_debts_with_due.filter(due_date__lt=today).count()
        debts_due_soon_count = open_debts_with_due.filter(due_date__gte=today, due_date__lte=soon_cutoff).count()

        # 1-masala: Kategoriya bo'yicha harajatlar taqsimoti (Obed, Taksi va h.k.)
        category_expenses, monthly_expense = category_breakdown_in_uzs(converter, month_expenses, "Boshqa xarajat")

        # 2-masala: Hafta kunlari bo'yicha xarajat taqsimoti (joriy hafta: Dushanba -> Yakshanba)
        # Django week_day: 1=Yakshanba, 2=Dushanba, ..., 7=Shanba
        # Uzbek hafta kunlari: Du(Mon)=2, Se(Tue)=3, Ch(Wed)=4, Pa(Thu)=5, Ju(Fri)=6, Sh(Sat)=7, Ya(Sun)=1
        UZ_DAYS = {2: "Du", 3: "Se", 4: "Ch", 5: "Pa", 6: "Ju", 7: "Sh", 1: "Ya"}
        WEEKDAY_ORDER = [2, 3, 4, 5, 6, 7, 1]  # Du -> Ya

        today = now.date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        week_expenses_qs = expenses_qs.filter(date__date__gte=week_start, date__date__lte=week_end)

        week_groups = sum_groups_in_uzs(converter, week_expenses_qs, ("date__week_day",))
        exp_by_weekday = {weekday: round_amount(group["uzs"]) for (weekday,), group in week_groups.items()}

        max_expense = max(exp_by_weekday.values(), default=0)
        weekly_expenses = [
            {
                "label": UZ_DAYS[wd],
                # So'mga o'girilgan qiymat: kunlarni solishtirish (ustun uzunligi, saralash) shu bo'yicha
                "expense": exp_by_weekday.get(wd, 0),
                # Asl valyutadagi summalar — ekranda shular ko'rsatiladi ("100 USD", "50 000 UZS")
                "parts": currency_parts(week_groups[(wd,)]["parts"]) if (wd,) in week_groups else [],
                "is_max": exp_by_weekday.get(wd, 0) == max_expense and max_expense > 0,
            }
            for wd in WEEKDAY_ORDER
        ]

        return Response({
            "balances_by_currency": balances_by_currency,
            "total_income": total_income,
            "total_expense": total_expense,
            "monthly_income": monthly_income,
            "monthly_expense": monthly_expense,
            "net_savings": total_income - total_expense,
            "debts_to_receive": total_given,   # menga qaytarilishi kerak
            "debts_to_pay": total_taken,       # men qaytarishim kerak
            "debts_overdue_count": debts_overdue_count,
            "debts_due_soon_count": debts_due_soon_count,
            "category_expenses": category_expenses,
            "weekly_expenses": weekly_expenses,
            "stats_currency": STATS_CURRENCY,
            "missing_rates": sorted(converter.missing),
        })


class MemberViewSet(viewsets.ModelViewSet):
    """Oila a'zolari / yaqinlar ViewSet — xarajat kimga qilinganini belgilash uchun"""
    queryset = Member.objects.filter(status=True)
    serializer_class = MemberSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status"]
    search_fields = ["name"]
    ordering_fields = ["id", "name", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Member.objects.none()
        return Member.objects.filter(status=True, user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"message": "A'zo muvaffaqiyatli o'chirildi"}, status=status.HTTP_200_OK)


class RecurringPaymentViewSet(viewsets.ModelViewSet):
    """Doimiy to'lovlar. Ro'yxat so'ralganda muddati kelganlari avval yoziladi — ilova ochiq turib kun almashsa ham
    keyingi yangilanishda to'lov tushadi"""
    serializer_class = RecurringPaymentSerializer
    pagination_class = None

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return RecurringPayment.objects.none()
        return RecurringPayment.objects.filter(user=self.request.user, status=True).select_related(
            "wallet", "expense_category", "income_category", "member")

    def list(self, request, *args, **kwargs):
        process_due_recurring(request.user)
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.status = False
        instance.save(update_fields=["status"])
        return Response({"message": "Doimiy to'lov o'chirildi. Avval yozilgan amallar saqlanib qoladi"})


class SavingsGoalViewSet(viewsets.ModelViewSet):
    """Jamg'arma maqsadlari"""
    serializer_class = SavingsGoalSerializer
    pagination_class = None

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return SavingsGoal.objects.none()
        # O'chirilgan hamyonga bog'langan maqsad ko'rsatilmaydi: puli boshqa hamyonga o'tkazilgan, progress 0 bo'lib qolardi
        return SavingsGoal.objects.filter(user=self.request.user, status=True, wallet__status=True).select_related("wallet")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        wallet = instance.wallet
        if not wallet.is_goal:
            # Eski maqsad oddiy hamyonga bog'langan — faqat maqsad o'chadi, hamyonga tegilmaydi
            instance.status = False
            instance.save(update_fields=["status"])
            return Response({"message": "Maqsad o'chirildi. Hamyon va undagi pul joyida qoladi"})

        # Maqsad hamyoni maqsad bilan birga o'chadi; yig'ilgan pul avval tanlangan hamyonga O'tkazma qilinadi
        target = None
        saved = wallet.summa
        if saved > 0:
            target_pk = strict_int(request.data.get("to_wallet") if isinstance(request.data, dict) else None)
            if target_pk is None:
                target_pk = strict_int(request.query_params.get("to_wallet"))
            target = Wallet.objects.filter(pk=target_pk, user=request.user, status=True, is_goal=False).first() if target_pk else None
            if not target:
                return Response({"error": "Maqsad hamyonidagi pul qaysi hamyonga o'tkazilishini tanlang"},
                                status=status.HTTP_400_BAD_REQUEST)
        to_summa, rate = None, None
        if target is not None and normalize_currency(target.currency) == normalize_currency(wallet.currency):
            to_summa, rate = saved, Decimal(1)
        elif target is not None:
            # Kurs tarmoqdan olinishi mumkin — tranzaksiyadan oldin
            try:
                to_summa, rate = convert(saved, wallet.currency, target.currency)
            except CurrencyRateError:
                return Response({"error": f"{wallet.currency} → {target.currency} kursini aniqlab bo'lmadi. "
                                          f"{wallet.currency} hamyonini tanlang yoki keyinroq urinib ko'ring"},
                                status=status.HTTP_400_BAD_REQUEST)
        try:
            with transaction.atomic():
                wallet.refresh_from_db()
                if target is not None and wallet.summa != saved:
                    # Shu orada hamyonga pul tushgan/chiqqan — eskirgan summa bilan o'tkazilmaydi
                    return Response({"error": "Maqsad hamyonidagi summa o'zgardi. Sahifani yangilab qayta urinib ko'ring"},
                                    status=status.HTTP_409_CONFLICT)
                instance.status = False
                instance.save(update_fields=["status"])
                # Maqsad hamyonidan chiqim o'tkazmasi taqiqlangan (Transfer.clean) — avval oddiy hamyonga aylantiriladi
                wallet.is_goal = False
                wallet.save(update_fields=["is_goal", "updated_at"])
                if target is not None:
                    Transfer.objects.create(
                        from_wallet=wallet, to_wallet=target, summa=wallet.summa, to_summa=to_summa, rate=rate,
                        description=f"Maqsad o'chirildi: {instance.name}", user=request.user)
                    wallet.refresh_from_db()
                wallet.delete()
        except (ValueError, DjangoValidationError) as e:
            return Response({"error": error_text(e)}, status=status.HTTP_400_BAD_REQUEST)
        if target is None:
            return Response({"message": "Maqsad va uning hamyoni o'chirildi"})
        return Response({"message": f"Maqsad va uning hamyoni o'chirildi. Pul «{target.name}» hamyoniga o'tkazildi"})


class IncomeViewSet(RestoreMixin, viewsets.ModelViewSet):
    queryset = Income.objects.filter(status=True)
    serializer_class = IncomeSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["wallet", "category", "status"]
    search_fields = ["description", "category__name", "wallet__name"]
    ordering_fields = ["id", "summa", "date", "created_at"]
    ordering = ["-date", "-id"]

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Income.objects.none()
        # Serializer wallet.name / wallet.currency / category.name / user.username ni o'qiydi — bitta JOIN bilan olinadi
        qs = Income.objects.filter(status=True, user=self.request.user).select_related("wallet", "category", "user")
        return filter_by_period(qs, self.request.query_params)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except (ValueError, DjangoValidationError, DRFValidationError) as e:
            return Response({"error": error_text(e)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        # Yangi hamyon o'chirilgan bo'lsa serializer uni "topilmadi" deb rad etadi; eskisi esa shu yerda tekshiriladi
        problem = deleted_wallet_response(self.get_object().wallet, verb="tahrirlab")
        if problem:
            return problem
        try:
            return super().update(request, *args, **kwargs)
        except (ValueError, DjangoValidationError, DRFValidationError) as e:
            return Response({"error": error_text(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        problem = deleted_wallet_response(instance.wallet)
        if problem:
            return problem
        try:
            self.perform_destroy(instance)
            return Response({"message": "Kirim o'chirildi va qoldiq qaytarildi"}, status=status.HTTP_200_OK)
        except (ValueError, DjangoValidationError, DRFValidationError) as e:
            return Response({"error": error_text(e)}, status=status.HTTP_400_BAD_REQUEST)


class ExpenseViewSet(RestoreMixin, viewsets.ModelViewSet):
    queryset = Expense.objects.filter(status=True)
    serializer_class = ExpenseSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["wallet", "category", "member", "status"]
    search_fields = ["description", "location", "category__name", "wallet__name", "member__name"]
    ordering_fields = ["id", "summa", "date", "created_at"]
    ordering = ["-date", "-id"]

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Expense.objects.none()
        # Serializer wallet, category, member va user nomlarini o'qiydi — bitta JOIN bilan olinadi
        qs = Expense.objects.filter(status=True, user=self.request.user).select_related("wallet", "category", "member", "user")
        qs = filter_by_period(qs, self.request.query_params)

        weekday = self.request.query_params.get('weekday')
        if weekday in UZ_WEEKDAY_TO_DJANGO:
            today = timezone.localdate()
            week_start = today - timedelta(days=today.weekday())
            week_end = week_start + timedelta(days=6)
            qs = qs.filter(
                date__week_day=UZ_WEEKDAY_TO_DJANGO[weekday],
                date__date__gte=week_start,
                date__date__lte=week_end,
            )
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except (ValueError, DjangoValidationError, DRFValidationError) as e:
            return Response({"error": error_text(e)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        problem = deleted_wallet_response(self.get_object().wallet, verb="tahrirlab")
        if problem:
            return problem
        try:
            return super().update(request, *args, **kwargs)
        except (ValueError, DjangoValidationError, DRFValidationError) as e:
            return Response({"error": error_text(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        problem = deleted_wallet_response(instance.wallet)
        if problem:
            return problem
        try:
            self.perform_destroy(instance)
            return Response({"message": "Chiqim o'chirildi va qoldiq qaytarildi"}, status=status.HTTP_200_OK)
        except (ValueError, DjangoValidationError, DRFValidationError) as e:
            return Response({"error": error_text(e)}, status=status.HTTP_400_BAD_REQUEST)


class TransferViewSet(RestoreMixin, viewsets.ModelViewSet):
    """Hamyondan hamyonga o'tkazma ViewSet"""
    queryset = Transfer.objects.filter(status=True)
    serializer_class = TransferSerializer
    restore_wallet_fields = ("from_wallet", "to_wallet")
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["from_wallet", "to_wallet", "status"]
    search_fields = ["description", "from_wallet__name", "to_wallet__name"]
    ordering_fields = ["id", "summa", "date", "created_at"]
    ordering = ["-date", "-id"]

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Transfer.objects.none()
        # Serializer ikkala hamyonning nomi va valyutasini hamda user.username ni o'qiydi
        qs = Transfer.objects.filter(status=True, user=self.request.user).select_related("from_wallet", "to_wallet", "user")
        return filter_by_period(qs, self.request.query_params)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except (ValueError, DjangoValidationError, DRFValidationError) as e:
            return Response({"error": error_text(e)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        problem = deleted_wallet_response(instance.from_wallet, instance.to_wallet, verb="tahrirlab")
        if problem:
            return problem
        try:
            return super().update(request, *args, **kwargs)
        except (ValueError, DjangoValidationError, DRFValidationError) as e:
            return Response({"error": error_text(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        problem = deleted_wallet_response(instance.from_wallet, instance.to_wallet)
        if problem:
            return problem
        try:
            self.perform_destroy(instance)
            return Response({"message": "O'tkazma bekor qilindi va qoldiq qaytarildi"}, status=status.HTTP_200_OK)
        except (ValueError, DjangoValidationError, DRFValidationError) as e:
            return Response({"error": error_text(e)}, status=status.HTTP_400_BAD_REQUEST)


class DebtViewSet(viewsets.ModelViewSet):
    """Qarzlar daftari ViewSet"""
    queryset = Debt.objects.filter(status=True)
    serializer_class = DebtSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["debt_type", "is_settled", "status", "wallet"]
    search_fields = ["person_name", "description"]
    ordering_fields = ["id", "summa", "due_date", "created_at"]
    ordering = ["is_settled", "-created_at"]

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Debt.objects.none()
        # Serializer wallet.name va user.username ni o'qiydi
        return Debt.objects.filter(status=True, user=self.request.user).select_related("wallet", "user")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except (ValueError, DjangoValidationError, DRFValidationError) as e:
            return Response({"error": error_text(e)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        problem = deleted_wallet_response(self.get_object().wallet, verb="tahrirlab")
        if problem:
            return problem
        try:
            return super().update(request, *args, **kwargs)
        except (ValueError, DjangoValidationError, DRFValidationError) as e:
            return Response({"error": error_text(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Qarz o'chirilganda qoldig'i hamyonga qaytariladi (Debt.delete)
        problem = deleted_wallet_response(instance.wallet) if instance.remaining_summa > 0 else None
        if problem:
            return problem
        try:
            self.perform_destroy(instance)
            return Response({"message": "Qarz o'chirildi"}, status=status.HTTP_200_OK)
        except (ValueError, DjangoValidationError, DRFValidationError) as e:
            return Response({"error": error_text(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="repay")
    def repay(self, request, pk=None):
        """Qarzni qisman yoki to'liq to'lash/qaytarish"""
        return repay_debt(self.get_object(), request.data.get("amount", 0), request.data.get("wallet"))


def repay_debt(debt, raw_amount, wallet_id):
    """Qarz to'lovi: DebtViewSet.repay va ovozli yordamchi (voice.py) uchun umumiy. Response qaytaradi"""
    try:
        amount = parse_amount(raw_amount)
    except ValueError as e:
        return Response({"error": f"To'lov miqdori: {e}"}, status=status.HTTP_400_BAD_REQUEST)

    if amount <= 0:
        return Response(
            {"error": "To'lov miqdori 0 dan katta bo'lishi kerak"},
            status=status.HTTP_400_BAD_REQUEST
        )
    if amount > MAX_AMOUNT:
        return Response({"error": MAX_AMOUNT_MESSAGE}, status=status.HTTP_400_BAD_REQUEST)

    # Hamyonsiz to'lov hech qaysi balansga tushmasdi (pul "yo'qolardi"), shuning uchun hamyon majburiy
    if wallet_id is None or wallet_id == "":
        return Response({"error": "Hamyonni tanlang"}, status=status.HTTP_400_BAD_REQUEST)
    # "abc", [1], true yoki 1.5 kabi qiymat 500 xato yoki boshqa hamyon o'rniga "topilmadi" javobini oladi
    wallet_pk = strict_int(wallet_id)
    wallet = Wallet.objects.filter(pk=wallet_pk, user=debt.user, status=True).first() if wallet_pk else None
    if not wallet:
        return Response({"error": "Tanlangan hamyon topilmadi"}, status=status.HTTP_404_NOT_FOUND)
    if wallet.is_goal:
        return Response({"error": "Maqsad hamyoni orqali qarz to'lab bo'lmaydi — boshqa hamyonni tanlang"},
                        status=status.HTTP_400_BAD_REQUEST)
    wallet_amount = amount
    if normalize_currency(wallet.currency) != normalize_currency(debt.currency):
        # Qarz bir valyutada, hamyon boshqasida: hamyonga kurs bo'yicha hisoblangan summa yoziladi
        try:
            wallet_amount, _rate = convert(amount, debt.currency, wallet.currency)
        except CurrencyRateError:
            return Response(
                {"error": f"{debt.currency} → {wallet.currency} kursini aniqlab bo'lmadi. "
                          f"Keyinroq urinib ko'ring yoki {debt.currency} hamyonini tanlang."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        if wallet_amount <= 0:
            return Response(
                {"error": f"Miqdor juda kichik: kurs bo'yicha 0 {wallet.currency} bo'ladi"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if wallet_amount > MAX_AMOUNT:
            return Response({"error": MAX_AMOUNT_MESSAGE}, status=status.HTTP_400_BAD_REQUEST)

    try:
        with transaction.atomic():
            # Parallel so'rovlar bir xil qarzni ikki marta to'lamasligi uchun qator qulflanadi
            # va qolgan summa qulfdan keyin qayta tekshiriladi
            debt = Debt.objects.select_for_update().get(pk=debt.pk)
            if amount > debt.remaining_summa:
                return Response(
                    {"error": f"To'lov miqdori qolgan qarzdan ({format_money(debt.remaining_summa)} {debt.currency}) ko'p bo'lishi mumkin emas"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if debt.debt_type == "give":
                # Menga qarz qaytarildi -> hamyonimga pul qo'shiladi
                wallet.add_money(wallet_amount)
            else:
                # Men qarzimni uzdim -> hamyonimdan pul yechiladi
                wallet.withdraw_money(wallet_amount)

            debt.paid_summa += amount
            if debt.paid_summa >= debt.summa:
                debt.is_settled = True
            debt.save()
    except (ValueError, DjangoValidationError, DRFValidationError) as e:
        return Response({"error": error_text(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        "message": "Qarz muvaffaqiyatli to'landi / qaytarildi",
        "debt": DebtSerializer(debt).data,
        "wallet_amount": wallet_amount,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def monthly_stats_api(request):
    """
    Batafsil hisobot — bitta oy yoki ixtiyoriy sana oralig'i uchun.
    Query params: ?year=2026&month=10  yoki  ?date_from=2026-09-15&date_to=2026-10-14
    Oraliq rejimi faqat ikkala sana ham to'g'ri bo'lsa yoqiladi (aks holda oy rejimi), uzunligi MAX_RANGE_DAYS dan oshmasin.
    """
    from django.db.models.functions import TruncDate
    import calendar

    user = request.user
    now = timezone.localtime()

    start, end = parse_date_range(request.query_params)
    if start and end:
        # Oraliq rejimi. Oldingi davr — shu uzunlikdagi, oraliqdan darhol oldingi davr
        length = (end - start).days + 1
        if length > MAX_RANGE_DAYS:
            return Response({"error": "Oraliq 1 yildan oshmasligi kerak"}, status=status.HTTP_400_BAD_REQUEST)
        prev_start = start - timedelta(days=length)
        # Javob shakli oy rejimi bilan mos qolishi uchun year/month — oraliq oxiridagi oy
        year, month = end.year, end.month
    else:
        try:
            year  = int(request.query_params.get("year",  now.year))
            month = int(request.query_params.get("month", now.month))
        except (TypeError, ValueError):
            year, month = now.year, now.month

        # Clamp (0001-yil kabi chekka yillar UTC ga o'girilganda sana chegarasidan chiqib 500 xato berardi)
        month = max(1, min(12, month))
        year = max(MIN_YEAR, min(MAX_YEAR, year))

        # Oy rejimi ham oraliq sifatida ishlanadi (1-kun .. oxirgi kun); oldingi davr — oldingi kalendar oy
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
        prev_start = (start - timedelta(days=1)).replace(day=1)
    prev_end = start - timedelta(days=1)

    def in_period(model, first, last):
        # date__date mahalliy vaqt bo'yicha kunni oladi, ikkala chegara ham kiradi
        return model.objects.filter(status=True, user=user, date__date__gte=first, date__date__lte=last)

    incomes_qs  = in_period(Income, start, end)
    expenses_qs = in_period(Expense, start, end)

    # Barcha summalar Markaziy bank kursi bo'yicha so'mga o'girilib jamlanadi va saralanadi
    converter = UzsConverter()

    # ── 1-2. Kategoriya bo'yicha harajatlar va daromadlar ────────────
    category_expenses, total_expense = category_breakdown_in_uzs(converter, expenses_qs, "Boshqa")
    category_incomes, total_income = category_breakdown_in_uzs(converter, incomes_qs, "Boshqa")
    net_savings = total_income - total_expense

    # ── 3. Kunlik trend (daromad + harajat) ─────────────────────────
    def sums_by_day(qs):
        # TruncDate mahalliy vaqt bo'yicha kunni qaytaradi. Oraliq oy chegarasidan o'tishi mumkin,
        # shuning uchun kun raqami emas, to'liq sana bo'yicha lug'atga yig'amiz
        groups = sum_groups_in_uzs(converter, qs.annotate(day=TruncDate("date")), ("day",))
        return {day: round_amount(group["uzs"]) for (day,), group in groups.items()}

    daily_inc = sums_by_day(incomes_qs)
    daily_exp = sums_by_day(expenses_qs)
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    daily_trend = [
        {"date": d.isoformat(), "day": d.day, "income": daily_inc.get(d, 0), "expense": daily_exp.get(d, 0)}
        for d in days
    ]

    # ── 4. Oldingi davr bilan taqqoslash ──────────────────────────────
    prev_expense = total_in_uzs(converter, in_period(Expense, prev_start, prev_end))
    prev_income  = total_in_uzs(converter, in_period(Income, prev_start, prev_end))

    exp_change = percent_change(total_expense, prev_expense)
    inc_change = percent_change(total_income, prev_income)

    return Response({
        "year":             year,
        "month":            month,
        "date_from":        start.isoformat(),
        "date_to":          end.isoformat(),
        "total_income":     total_income,
        "total_expense":    total_expense,
        "net_savings":      net_savings,
        "prev_expense":     prev_expense,
        "prev_income":      prev_income,
        "expense_change":   exp_change,
        "income_change":    inc_change,
        "category_expenses": category_expenses,
        "category_incomes":  category_incomes,
        "daily_trend":       daily_trend,
        # Hamma summalar shu valyutada; kursi topilmagan valyutalar jamiga qo'shilmagan
        "stats_currency":    STATS_CURRENCY,
        "missing_rates":     sorted(converter.missing),
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def rates_api(request):
    """Navbar → Kurs sahifasi: Markaziy bankning bugungi kurslari (1 birlik = rate so'm, diff — kunlik o'zgarish).
    Kurslar bazada keshlanadi (currency.RATES_TTL); Markaziy bank javob bermasa oxirgi saqlangani qaytadi"""
    rows = get_rates_snapshot()
    if not rows:
        return Response(
            {"error": "Valyuta kurslarini olib bo'lmadi. Internet aloqasini tekshirib, keyinroq urinib ko'ring."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    main = next((r for r in rows if r.currency == "USD"), rows[0])
    return Response({
        "base": "UZS",
        "date": main.rate_date,
        "updated_at": max(r.updated_at for r in rows),
        "rates": [
            {
                "currency": r.currency,
                "rate": f"{r.rate.normalize():f}",
                "diff": None if r.diff is None else f"{r.diff.normalize():f}",
                "date": r.rate_date,
            }
            for r in rows
        ],
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def convert_api(request):
    """Valyuta kalkulyatori (Markaziy bank kursi): ?from=USD&to=UZS&amount=100.
    O'tkazma oynasida tushadigan miqdorni oldindan ko'rsatish uchun"""
    from_code = normalize_currency(request.query_params.get("from"))
    to_code = normalize_currency(request.query_params.get("to"))
    try:
        amount = parse_amount(request.query_params.get("amount", 1))
    except ValueError as e:
        return Response({"error": f"amount: {e}"}, status=status.HTTP_400_BAD_REQUEST)
    if not from_code or not to_code or amount <= 0:
        return Response({"error": "from, to va musbat amount kerak"}, status=status.HTTP_400_BAD_REQUEST)
    if amount > MAX_AMOUNT:
        return Response({"error": MAX_AMOUNT_MESSAGE}, status=status.HTTP_400_BAD_REQUEST)
    try:
        result, rate = convert(amount, from_code, to_code)
    except CurrencyRateError as e:
        return Response({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response({"from": from_code, "to": to_code, "amount": amount, "result": result, "rate": str(rate)})


@ensure_csrf_cookie
def dashboard_view(request):
    """Asosiy Web Dashboard interfeysi"""
    return render(request, "index.html")
