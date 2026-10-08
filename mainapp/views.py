from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db import models, transaction
from django.db.models import Q, Sum
import logging
import secrets
from datetime import timedelta

from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.core.validators import validate_email
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, BasePermission, SAFE_METHODS, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import User, Category, ExpenseCategory, Wallet, Member, Income, Expense, Transfer, Debt, PasswordResetCode
from .backends import find_user_by_login

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
)


def validate_email_uz(email, exclude_pk=None):
    """Email ixtiyoriy, lekin kiritilsa to'g'ri formatda va boshqa akkauntda band bo'lmasligi kerak
    (email bilan ham kirish mumkinligi uchun). Xato matnini yoki None qaytaradi"""
    if not email:
        return None
    try:
        validate_email(email)
    except DjangoValidationError:
        return "Email manzili noto'g'ri"
    if User.email_taken(email, exclude_pk=exclude_pk):
        return "Bu email boshqa akkauntda ishlatilgan"
    return None


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


def password_errors_uz(error):
    """Django parol validatorlari xabarlarini o'zbekchaga o'giradi (uz lokalida tarjimasi yo'q)"""
    messages = []
    for err in error.error_list:
        params = err.params or {}
        if err.code == "password_too_short":
            messages.append(f"Parol juda qisqa — kamida {params.get('min_length', 8)} ta belgi bo'lishi kerak.")
        elif err.code == "password_too_common":
            messages.append("Bu parol juda oddiy, boshqasini tanlang.")
        elif err.code == "password_entirely_numeric":
            messages.append("Parol faqat raqamlardan iborat bo'lmasligi kerak.")
        elif err.code == "password_same_as_username":
            messages.append("Parol foydalanuvchi nomi bilan bir xil bo'lishi mumkin emas.")
        elif err.code == "password_too_simple":
            messages.append("Parol juda oddiy — kamida 3 xil belgi ishlatilishi kerak.")
        else:
            messages.extend(err.messages)
    return " ".join(messages)


# ==========================================
# AUTHENTICATION API ENDPOINTS
# ==========================================

@api_view(["POST"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def login_api(request):
    """Tizimga kirish — foydalanuvchi nomi yoki email va parol bilan"""
    username = str(request.data.get("username") or request.data.get("email") or "").strip()
    password = str(request.data.get("password") or "").strip()

    if not username or not password:
        return Response(
            {"error": "Foydalanuvchi nomi (yoki email) va parol kiritilishi shart"},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = authenticate(request, username=username, password=password)
    if user is not None:
        if not user.is_active:
            return Response(
                {"error": "Foydalanuvchi hisobi bloklangan"},
                status=status.HTTP_403_FORBIDDEN
            )
        login(request, user)
        request.session.set_expiry(0)
        return Response({
            "message": "Muvaffaqiyatli tizimga kirildi",
            "user": user_payload(user),
        })
    return Response(
        {"error": "Foydalanuvchi nomi (yoki email) yoki parol noto'g'ri"},
        status=status.HTTP_401_UNAUTHORIZED
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def logout_api(request):
    """Tizimdan chiqish (Logout)"""
    logout(request)
    return Response({"message": "Tizimdan muvaffaqiyatli chiqildi"})


@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def me_api(request):
    """Hozirgi foydalanuvchi holati"""
    if request.user.is_authenticated:
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
    }


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def profile_api(request):
    """Sozlamalar — foydalanuvchi o'z profil ma'lumotlarini o'zgartirishi"""
    user = request.user
    data = request.data
    errors = {}

    if "username" in data:
        username = str(data.get("username") or "").strip()
        if not username:
            errors["username"] = "Foydalanuvchi nomi bo'sh bo'lishi mumkin emas"
        elif User.objects.filter(username__iexact=username).exclude(pk=user.pk).exists():
            errors["username"] = "Bu foydalanuvchi nomi allaqachon band"
        else:
            try:
                User.username_validator(username)
            except DjangoValidationError:
                errors["username"] = "Foydalanuvchi nomida faqat harf, raqam va @ . + - _ belgilari bo'lishi mumkin"
            else:
                user.username = username

    if "email" in data:
        email = str(data.get("email") or "").strip()
        email_error = validate_email_uz(email, exclude_pk=user.pk)
        if email_error:
            errors["email"] = email_error
        else:
            user.email = email

    for field in ("first_name", "last_name"):
        if field in data:
            setattr(user, field, str(data.get(field) or "").strip()[:150])

    if "phone" in data:
        user.phone = str(data.get("phone") or "").strip()[:20] or None

    if errors:
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

    user.save()
    return Response({"message": "Profil ma'lumotlari saqlandi", "user": user_payload(user)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password_api(request):
    """Sozlamalar — joriy parolni tasdiqlab, yangi parol o'rnatish"""
    user = request.user
    old_password = request.data.get("old_password", "")
    new_password = request.data.get("new_password", "")

    if not old_password or not new_password:
        return Response({"error": "Joriy va yangi parol kiritilishi shart"}, status=status.HTTP_400_BAD_REQUEST)
    if not user.check_password(old_password):
        return Response({"old_password": "Joriy parol noto'g'ri"}, status=status.HTTP_400_BAD_REQUEST)
    if old_password == new_password:
        return Response({"new_password": "Yangi parol joriy paroldan farq qilishi kerak"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        validate_password(new_password, user=user)
    except DjangoValidationError as e:
        return Response({"new_password": password_errors_uz(e)}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(new_password)
    user.save(update_fields=["password"])
    # Parol o'zgargach joriy sessiya chiqib ketmasligi uchun
    update_session_auth_hash(request, user)
    return Response({"message": "Parol muvaffaqiyatli o'zgartirildi"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def delete_account_api(request):
    """Sozlamalar - parolni tasdiqlab, akkauntni o'chirish.
    close_account(): akkauntga qayta kirib bo'lmaydi, shaxsiy ma'lumotlar tozalanadi va login nomi bo'shaydi,
    moliyaviy tarix bazada saqlanadi"""
    password = str(request.data.get("password") or "")
    if not password:
        return Response({"password": "Tasdiqlash uchun parolni kiriting"}, status=status.HTTP_400_BAD_REQUEST)
    user = request.user
    if not user.check_password(password):
        return Response({"password": "Parol noto'g'ri"}, status=status.HTTP_400_BAD_REQUEST)

    user.close_account()
    logout(request)
    return Response({"message": "Akkaunt o'chirildi"})


@api_view(["POST"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def register_api(request):
    """Yangi foydalanuvchini ro'yxatdan o'tkazish"""
    username = request.data.get("username", "").strip()
    password = request.data.get("password", "").strip()
    first_name = request.data.get("first_name", "").strip()
    last_name = request.data.get("last_name", "").strip()
    phone = request.data.get("phone", "").strip()

    if not username or not password:
        return Response(
            {"error": "Foydalanuvchi nomi va parol kiritilishi shart"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        validate_password(password, user=User(
            username=username, first_name=first_name, last_name=last_name,
        ))
    except DjangoValidationError as e:
        return Response({"error": password_errors_uz(e)}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(username=username).exists():
        return Response(
            {"error": "Bu foydalanuvchi nomi allaqachon band"},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = User.objects.create_user(
        username=username,
        password=password,
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

    login(request, user)
    request.session.set_expiry(0)
    return Response({
        "message": "Ro'yxatdan muvaffaqiyatli o'tildi",
        "user": user_payload(user),
    }, status=status.HTTP_201_CREATED)


# ==========================================
# PAROLNI TIKLASH (email orqali kod)
# ==========================================

logger = logging.getLogger(__name__)

RESET_RESEND_SECONDS = 60
RESET_REQUEST_MESSAGE = (
    "Agar bunday akkaunt mavjud bo'lsa va unga email ulangan bo'lsa, "
    "emailga 6 xonali tiklash kodi yuborildi."
)


@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_request_api(request):
    """1-qadam: login yoki email bo'yicha akkauntni topib, ulangan emailga kod yuborish.
    Javob har doim bir xil — begona odam akkaunt yoki email borligini bilib ololmasligi uchun"""
    identifier = str(request.data.get("username") or "").strip()
    if not identifier:
        return Response({"error": "Foydalanuvchi nomi yoki email kiritilishi shart"}, status=status.HTTP_400_BAD_REQUEST)

    user = find_user_by_login(identifier)
    if user is None or not user.is_active or not user.email:
        return Response({"message": RESET_REQUEST_MESSAGE})

    last = user.password_reset_codes.first()
    if last and (timezone.now() - last.created_at).total_seconds() < RESET_RESEND_SECONDS:
        # Ketma-ket ko'p xat yuborilishining oldini olish
        return Response({"message": RESET_REQUEST_MESSAGE})

    code = f"{secrets.randbelow(1_000_000):06d}"
    with transaction.atomic():
        user.password_reset_codes.filter(used=False).update(used=True)
        reset_code = PasswordResetCode.objects.create(
            user=user,
            code_hash=make_password(code),
            expires_at=timezone.now() + timedelta(minutes=PasswordResetCode.CODE_LIFETIME_MINUTES),
        )

    name = user.first_name or user.username
    try:
        send_mail(
            subject="Moliya — parolni tiklash kodi",
            message=(
                f"Assalomu alaykum, {name}!\n\n"
                f"Parolni tiklash kodingiz: {code}\n\n"
                f"Kod {PasswordResetCode.CODE_LIFETIME_MINUTES} daqiqa amal qiladi. "
                "Agar parolni tiklashni siz so'ramagan bo'lsangiz, bu xatni e'tiborsiz qoldiring — "
                "parolingiz o'zgarmaydi."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )
    except Exception:
        logger.exception("Parol tiklash xatini yuborib bo'lmadi (user_id=%s)", user.pk)
        # Yuborilmagan kod qayta urinishni 60 soniyaga to'sib qo'ymasligi uchun o'chiriladi
        reset_code.delete()
        return Response(
            {"error": "Email yuborishda xatolik yuz berdi. Birozdan keyin qayta urinib ko'ring."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    return Response({"message": RESET_REQUEST_MESSAGE})


@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_confirm_api(request):
    """2-qadam: emailga kelgan kod bilan yangi parol o'rnatish"""
    identifier = str(request.data.get("username") or "").strip()
    code = str(request.data.get("code") or "").strip()
    new_password = str(request.data.get("new_password") or "")

    if not identifier or not code or not new_password:
        return Response({"error": "Kod va yangi parol kiritilishi shart"}, status=status.HTTP_400_BAD_REQUEST)

    invalid = Response({"code": "Kod noto'g'ri yoki muddati o'tgan"}, status=status.HTTP_400_BAD_REQUEST)
    user = find_user_by_login(identifier)
    if user is None or not user.is_active:
        return invalid

    reset = user.password_reset_codes.filter(used=False).first()
    if reset is None or not reset.is_usable:
        return invalid

    if not reset.check_code(code):
        reset.attempts += 1
        reset.save(update_fields=["attempts"])
        left = PasswordResetCode.MAX_ATTEMPTS - reset.attempts
        if left <= 0:
            return Response(
                {"code": "Urinishlar soni tugadi. Yangi kod so'rang."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response({"code": f"Kod noto'g'ri. Yana {left} ta urinish qoldi."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        validate_password(new_password, user=user)
    except DjangoValidationError as e:
        return Response({"new_password": password_errors_uz(e)}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        user.set_password(new_password)
        user.save(update_fields=["password"])
        user.password_reset_codes.filter(used=False).update(used=True)

    return Response({"message": "Parol yangilandi. Endi yangi parol bilan tizimga kiring."})


# ==========================================
# REST API VIEWSETS (Multi-tenant / User-scoped)
# ==========================================

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.filter(status=True)
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
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

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return User.objects.none()
        if self.request.user.is_staff or self.request.user.is_superuser:
            return User.objects.filter(status=True)
        return User.objects.filter(id=self.request.user.id, status=True)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        is_self = instance.pk == request.user.pk
        if is_self:
            instance.close_account()
        else:
            self.perform_destroy(instance)
        if is_self:
            logout(request)
        return Response({"message": "Akkaunt o'chirildi"}, status=status.HTTP_200_OK)


class CanEditCategory(BasePermission):
    """O'qish hammaga ochiq. Yaratish - tizimga kirgan foydalanuvchiga (shaxsiy kategoriya).
    O'zgartirish/o'chirish - faqat kategoriya egasiga; umumiy kategoriyalarni (egasi yo'q) faqat admin"""

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if obj.user_id is None:
            return bool(request.user.is_staff)
        return obj.user_id == request.user.id


class PersonalCategoryMixin:
    """Umumiy kategoriyalar hammaga ko'rinadi; foydalanuvchi qo'shganlari faqat o'ziga"""
    permission_classes = [CanEditCategory]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_authenticated:
            return qs.filter(Q(user__isnull=True) | Q(user=user))
        return qs.filter(user__isnull=True)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CategoryViewSet(PersonalCategoryMixin, viewsets.ModelViewSet):
    """Daromad turlari (Oylik, Freelance, Sovg'a...)"""
    queryset = Category.objects.filter(status=True)
    serializer_class = CategorySerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status"]
    search_fields = ["name", "description"]
    ordering_fields = ["id", "name", "created_at"]
    ordering = ["name"]


class ExpenseCategoryViewSet(PersonalCategoryMixin, viewsets.ModelViewSet):
    """Harajat turlari (Ovqat, Transport, Kiyim...)"""
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
        return Wallet.objects.filter(status=True, user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
            return Response({"message": "Hamyon muvaffaqiyatli o'chirildi"}, status=status.HTTP_200_OK)
        except (ValueError, DjangoValidationError, DRFValidationError) as e:
            return Response({"error": error_text(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """Umumiy moliyaviy statistika (balans, daromad, harajat, qarzlar)"""
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

        now = timezone.now()
        month_incomes = incomes_qs.filter(date__year=now.year, date__month=now.month)
        month_expenses = expenses_qs.filter(date__year=now.year, date__month=now.month)

        total_balance = wallets_qs.aggregate(total=Sum("summa"))["total"] or 0
        total_income = incomes_qs.aggregate(total=Sum("summa"))["total"] or 0
        total_expense = expenses_qs.aggregate(total=Sum("summa"))["total"] or 0
        monthly_income = month_incomes.aggregate(total=Sum("summa"))["total"] or 0
        monthly_expense = month_expenses.aggregate(total=Sum("summa"))["total"] or 0

        # Qarzlar statistikasi
        given_debts = debts_qs.filter(debt_type="give", is_settled=False)
        taken_debts = debts_qs.filter(debt_type="take", is_settled=False)
        total_given = sum(d.remaining_summa for d in given_debts)
        total_taken = sum(d.remaining_summa for d in taken_debts)

        # Muddati o'tgan / yaqinlashgan qarzlar (ochiq va due_date belgilangan)
        DEBT_DUE_SOON_DAYS = 3
        today = now.date()
        soon_cutoff = today + timezone.timedelta(days=DEBT_DUE_SOON_DAYS)
        open_debts_with_due = debts_qs.filter(is_settled=False, due_date__isnull=False)
        debts_overdue_count = open_debts_with_due.filter(due_date__lt=today).count()
        debts_due_soon_count = open_debts_with_due.filter(due_date__gte=today, due_date__lte=soon_cutoff).count()

        # 1-masala: Kategoriya bo'yicha harajatlar taqsimoti (Obed, Taksi va h.k.)
        cat_breakdown = list(
            month_expenses.values("category__id", "category__name")
            .annotate(total=Sum("summa"))
            .order_by("-total")
        )
        category_expenses = [
            {
                "id": item["category__id"],
                "name": item["category__name"] or "Boshqa harajat",
                "total": item["total"],
                "percent": round((item["total"] / monthly_expense * 100), 1) if monthly_expense > 0 else 0
            }
            for item in cat_breakdown
        ]

        # 2-masala: Hafta kunlari bo'yicha xarajat taqsimoti (joriy hafta: Dushanba -> Yakshanba)
        # Django week_day: 1=Yakshanba, 2=Dushanba, ..., 7=Shanba
        # Uzbek hafta kunlari: Du(Mon)=2, Se(Tue)=3, Ch(Wed)=4, Pa(Thu)=5, Ju(Fri)=6, Sh(Sat)=7, Ya(Sun)=1
        UZ_DAYS = {2: "Du", 3: "Se", 4: "Ch", 5: "Pa", 6: "Ju", 7: "Sh", 1: "Ya"}
        WEEKDAY_ORDER = [2, 3, 4, 5, 6, 7, 1]  # Du -> Ya

        today = now.date()
        week_start = today - timezone.timedelta(days=today.weekday())
        week_end = week_start + timezone.timedelta(days=6)
        week_expenses_qs = expenses_qs.filter(date__date__gte=week_start, date__date__lte=week_end)

        exp_by_weekday = {
            item["date__week_day"]: item["s"]
            for item in week_expenses_qs.values("date__week_day").annotate(s=Sum("summa"))
        }

        max_expense = max(exp_by_weekday.values(), default=0)
        weekly_expenses = [
            {
                "label": UZ_DAYS[wd],
                "expense": exp_by_weekday.get(wd, 0),
                "is_max": exp_by_weekday.get(wd, 0) == max_expense and max_expense > 0,
            }
            for wd in WEEKDAY_ORDER
        ]

        return Response({
            "total_wallets_balance": total_balance,
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


class IncomeViewSet(viewsets.ModelViewSet):
    queryset = Income.objects.filter(status=True)
    serializer_class = IncomeSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["wallet", "category", "status"]
    search_fields = ["description", "category__name", "wallet__name"]
    ordering_fields = ["id", "summa", "date", "created_at"]
    ordering = ["-date"]

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Income.objects.none()
        return Income.objects.filter(status=True, user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except (ValueError, DjangoValidationError, DRFValidationError) as e:
            return Response({"error": error_text(e)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except (ValueError, DjangoValidationError, DRFValidationError) as e:
            return Response({"error": error_text(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
            return Response({"message": "Daromad o'chirildi va balans qaytarildi"}, status=status.HTTP_200_OK)
        except (ValueError, DjangoValidationError, DRFValidationError) as e:
            return Response({"error": error_text(e)}, status=status.HTTP_400_BAD_REQUEST)


class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.filter(status=True)
    serializer_class = ExpenseSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["wallet", "category", "member", "status"]
    search_fields = ["description", "location", "category__name", "wallet__name", "member__name"]
    ordering_fields = ["id", "summa", "date", "created_at"]
    ordering = ["-date"]

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Expense.objects.none()
        qs = Expense.objects.filter(status=True, user=self.request.user)
        year  = self.request.query_params.get('year')
        month = self.request.query_params.get('month')
        if year:
            qs = qs.filter(date__year=int(year))
        if month:
            qs = qs.filter(date__month=int(month))

        weekday = self.request.query_params.get('weekday')
        if weekday in UZ_WEEKDAY_TO_DJANGO:
            today = timezone.now().date()
            week_start = today - timezone.timedelta(days=today.weekday())
            week_end = week_start + timezone.timedelta(days=6)
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
        try:
            return super().update(request, *args, **kwargs)
        except (ValueError, DjangoValidationError, DRFValidationError) as e:
            return Response({"error": error_text(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
            return Response({"message": "Harajat o'chirildi va balans qaytarildi"}, status=status.HTTP_200_OK)
        except (ValueError, DjangoValidationError, DRFValidationError) as e:
            return Response({"error": error_text(e)}, status=status.HTTP_400_BAD_REQUEST)


class TransferViewSet(viewsets.ModelViewSet):
    """Hamyonlararo o'tkazma ViewSet"""
    queryset = Transfer.objects.filter(status=True)
    serializer_class = TransferSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["from_wallet", "to_wallet", "status"]
    search_fields = ["description", "from_wallet__name", "to_wallet__name"]
    ordering_fields = ["id", "summa", "date", "created_at"]
    ordering = ["-date"]

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Transfer.objects.none()
        return Transfer.objects.filter(status=True, user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except (ValueError, DjangoValidationError, DRFValidationError) as e:
            return Response({"error": error_text(e)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except (ValueError, DjangoValidationError, DRFValidationError) as e:
            return Response({"error": error_text(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
            return Response({"message": "O'tkazma bekor qilindi va balans qaytarildi"}, status=status.HTTP_200_OK)
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
        return Debt.objects.filter(status=True, user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except (ValueError, DjangoValidationError, DRFValidationError) as e:
            return Response({"error": error_text(e)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except (ValueError, DjangoValidationError, DRFValidationError) as e:
            return Response({"error": error_text(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
            return Response({"message": "Qarz o'chirildi"}, status=status.HTTP_200_OK)
        except (ValueError, DjangoValidationError, DRFValidationError) as e:
            return Response({"error": error_text(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="repay")
    def repay(self, request, pk=None):
        """Qarzni qisman yoki to'liq to'lash/qaytarish"""
        debt = self.get_object()
        try:
            raw_amount = request.data.get("amount", 0)
            amount = int(raw_amount)
        except (TypeError, ValueError):
            return Response(
                {"error": "To'lov summasi butun son bo'lishi kerak"},
                status=status.HTTP_400_BAD_REQUEST
            )

        wallet_id = request.data.get("wallet")

        if amount <= 0:
            return Response(
                {"error": "To'lov summasi 0 dan katta bo'lishi kerak"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if amount > debt.remaining_summa:
            return Response(
                {"error": f"To'lov summasi qolgan qarzdan ({debt.remaining_summa:,} UZS) ko'p bo'lishi mumkin emas"},
                status=status.HTTP_400_BAD_REQUEST
            )

        wallet = None
        if wallet_id:
            wallet = Wallet.objects.filter(pk=wallet_id, user=debt.user, status=True).first()
            if not wallet:
                return Response({"error": "Tanlangan hamyon topilmadi"}, status=status.HTTP_404_NOT_FOUND)

        try:
            with transaction.atomic():
                if wallet:
                    if debt.debt_type == "give":
                        # Menga qarz qaytarildi -> hamyonimga pul qo'shiladi
                        wallet.add_money(amount)
                    else:
                        # Men qarzimni uzdim -> hamyonimdan pul yechiladi
                        wallet.withdraw_money(amount)

                debt.paid_summa += amount
                if debt.paid_summa >= debt.summa:
                    debt.is_settled = True
                debt.save()
        except (ValueError, DjangoValidationError, DRFValidationError) as e:
            return Response({"error": error_text(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": "Qarz muvaffaqiyatli to'landi / qaytarildi",
            "debt": DebtSerializer(debt).data,
        })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def monthly_stats_api(request):
    """
    Oylik batafsil statistika.
    Query params: ?year=2026&month=10
    """
    from django.db.models.functions import TruncDay
    import calendar

    user = request.user
    now = timezone.now()

    try:
        year  = int(request.query_params.get("year",  now.year))
        month = int(request.query_params.get("month", now.month))
    except (TypeError, ValueError):
        year, month = now.year, now.month

    # Clamp
    month = max(1, min(12, month))

    incomes_qs  = Income.objects.filter(status=True, user=user,
                                        date__year=year, date__month=month)
    expenses_qs = Expense.objects.filter(status=True, user=user,
                                         date__year=year, date__month=month)

    total_income  = incomes_qs.aggregate(t=Sum("summa"))["t"] or 0
    total_expense = expenses_qs.aggregate(t=Sum("summa"))["t"] or 0
    net_savings   = total_income - total_expense

    # ── 1. Kategoriya bo'yicha harajatlar ────────────────────────────
    cat_breakdown = list(
        expenses_qs.values("category__id", "category__name")
        .annotate(total=Sum("summa"))
        .order_by("-total")
    )
    category_expenses = [
        {
            "id":      item["category__id"],
            "name":    item["category__name"] or "Boshqa",
            "total":   item["total"],
            "percent": round(item["total"] / total_expense * 100, 1) if total_expense > 0 else 0,
        }
        for item in cat_breakdown
    ]

    # ── 2. Kategoriya bo'yicha daromadlar ────────────────────────────
    inc_breakdown = list(
        incomes_qs.values("category__id", "category__name")
        .annotate(total=Sum("summa"))
        .order_by("-total")
    )
    category_incomes = [
        {
            "id":      item["category__id"],
            "name":    item["category__name"] or "Boshqa",
            "total":   item["total"],
            "percent": round(item["total"] / total_income * 100, 1) if total_income > 0 else 0,
        }
        for item in inc_breakdown
    ]

    # ── 3. Kunlik trend (daromad + harajat) ─────────────────────────
    days_in_month = calendar.monthrange(year, month)[1]

    daily_inc = {
        item["day"]: item["s"]
        for item in incomes_qs.annotate(day=TruncDay("date")).values("day").annotate(s=Sum("summa"))
    }
    daily_exp = {
        item["day"]: item["s"]
        for item in expenses_qs.annotate(day=TruncDay("date")).values("day").annotate(s=Sum("summa"))
    }

    from datetime import date as date_cls
    daily_trend = []
    for d in range(1, days_in_month + 1):
        key = date_cls(year, month, d)
        # TruncDay returns date objects — match either way
        inc_val = 0
        exp_val = 0
        for k, v in daily_inc.items():
            kd = k.date() if hasattr(k, "date") else k
            if kd == key:
                inc_val = v
                break
        for k, v in daily_exp.items():
            kd = k.date() if hasattr(k, "date") else k
            if kd == key:
                exp_val = v
                break
        daily_trend.append({"day": d, "income": inc_val, "expense": exp_val})

    # ── 4. Oldingi oy bilan taqqoslash ────────────────────────────────
    prev_month = month - 1 if month > 1 else 12
    prev_year  = year if month > 1 else year - 1
    prev_exp_qs = Expense.objects.filter(status=True, user=user,
                                         date__year=prev_year, date__month=prev_month)
    prev_inc_qs = Income.objects.filter(status=True, user=user,
                                        date__year=prev_year, date__month=prev_month)
    prev_expense = prev_exp_qs.aggregate(t=Sum("summa"))["t"] or 0
    prev_income  = prev_inc_qs.aggregate(t=Sum("summa"))["t"] or 0

    exp_change = round((total_expense - prev_expense) / prev_expense * 100, 1) if prev_expense > 0 else None
    inc_change = round((total_income  - prev_income)  / prev_income  * 100, 1) if prev_income  > 0 else None

    return Response({
        "year":             year,
        "month":            month,
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
    })


@ensure_csrf_cookie
def dashboard_view(request):
    """Asosiy Web Dashboard interfeysi"""
    return render(request, "index.html")
