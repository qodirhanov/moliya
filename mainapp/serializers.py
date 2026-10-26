from datetime import timedelta
from decimal import Decimal

from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.utils import timezone
from .models import (
    format_money,
    DATE_RANGE_MESSAGE, MAX_AMOUNT, MAX_AMOUNT_MESSAGE, MAX_YEAR, MIN_YEAR, USERNAME_TAKEN_MESSAGE,
    User, Category, ExpenseCategory, Wallet, Member, Income, Expense, Transfer, Debt, RecurringPayment, SavingsGoal,
)
from .currency import CurrencyRateError, convert, is_valid_currency_code, normalize_currency
from .money import CENT, MONEY_DECIMALS_MESSAGE, MONEY_INVALID_MESSAGE, quantize_money
from .validators import password_errors_uz, username_error


# Summa maydonlari uchun yuqori chegara (models.MAX_AMOUNT) — DRF'ning inglizcha
# "Ensure this value is less than or equal to ..." xabari o'rniga o'zbekcha xabar bilan
AMOUNT_FIELD = {"max_value": MAX_AMOUNT, "error_messages": {
    "max_value": MAX_AMOUNT_MESSAGE,
    "invalid": MONEY_INVALID_MESSAGE,
    "max_decimal_places": MONEY_DECIMALS_MESSAGE,
    "max_digits": MAX_AMOUNT_MESSAGE,
    "max_whole_digits": MAX_AMOUNT_MESSAGE,
}}


class MoneyField(serializers.DecimalField):
    """Summa maydoni: 12.5, "12.50", 100 qabul qilinadi; 2 tadan ko'p kasr xonasi rad etiladi (jimgina
    yaxlitlanmaydi). DRF'ning standart tekshiruvi "12.340" ni ham rad etardi, bu yerda nolga teng ortiqcha xona mumkin"""

    def validate_precision(self, value):
        if value != value.quantize(CENT):
            self.fail("max_decimal_places", max_decimal_places=2)
        if abs(value) >= 10 ** 13:  # 13 xonali butun qism — max_digits=15 chegarasi; undan kattasi bazaga sig'maydi
            self.fail("max_whole_digits", max_whole_digits=13)
        return value


class MoneyModelSerializer(serializers.ModelSerializer):
    """summa / to_summa maydonlarini MoneyField qiladi (kurslar — rate, uzs_rate — oddiy DecimalField bo'lib qoladi)"""

    def build_standard_field(self, field_name, model_field):
        field_class, field_kwargs = super().build_standard_field(field_name, model_field)
        if field_class is serializers.DecimalField and field_name in ("summa", "to_summa"):
            field_class = MoneyField
        return field_class, field_kwargs

# Transfer.rate (max_digits=20, decimal_places=8) butun qismga atigi 12 xona beradi: undan katta kurs bazaga yozilganda
# decimal.InvalidOperation (500 xato) berardi
MAX_RATE = Decimal(10) ** 12
MAX_RATE_MESSAGE = "Tushadigan summa chiqadigan summadan juda ko'p marta katta — kurs 1 000 000 000 000 dan oshmasligi kerak"
# Pastki chegara: ustun saqlay oladigan eng kichik kurs. Undan kichik kurs 8 xonaga yaxlitlanganda 0 bo'lib saqlanardi
# (keyin faqat summani tahrirlash "Summa juda kichik" xatosini berardi)
MIN_RATE = Decimal("0.00000001")
MIN_RATE_MESSAGE = "Tushadigan summa chiqadigan summadan juda ko'p marta kichik — kurs 0.00000001 dan kam bo'lmasligi kerak"


def check_date_range(value):
    """Operatsiya sanasi / qarz muddati real yillar oralig'ida bo'lishi kerak (0001-yil sanasi 500 xato berardi)"""
    if value is not None and not (MIN_YEAR <= value.year <= MAX_YEAR):
        raise serializers.ValidationError(DATE_RANGE_MESSAGE)
    return value


class BoundedDateTimeField(serializers.DateTimeField):
    """Operatsiya sanasi. 0001-yil kabi sana DRF ichida (vaqt zonasini tekshirishda) OverflowError bilan
    500 xato berardi (serializer validatsiyasiga yetib bormasdan). Shuning uchun chegara maydonning o'zida tekshiriladi"""

    def to_internal_value(self, value):
        try:
            result = super().to_internal_value(value)
        except OverflowError:
            raise serializers.ValidationError(DATE_RANGE_MESSAGE)
        return check_date_range(result)


def _own_wallets(user):
    return Wallet.objects.filter(user=user, status=True)


# O'chirilgan (status=False) a'zo va toifa ham "topilmadi" — yangi operatsiyaga tanlab bo'lmaydi
def _own_members(user):
    return Member.objects.filter(user=user, status=True)


def _visible_categories(model, hidden_field):
    """Yangi operatsiyaga tanlash mumkin bo'lgan toifalar: umumiy va foydalanuvchining o'zinikilari,
    o'chirilgan va foydalanuvchi o'z ro'yxatidan yashirgan umumiy toifalarsiz"""
    def queryset(user):
        hidden_ids = getattr(user, hidden_field).values_list("pk", flat=True)
        return model.objects.filter(Q(user__isnull=True) | Q(user=user), status=True).exclude(pk__in=hidden_ids)
    return queryset


class OwnedRelationsMixin:
    """Hamyon / toifa / a'zo maydonlarida faqat joriy foydalanuvchiga tegishli yozuvlar qabul qilinadi.
    Begona ID "topilmadi" deb rad etiladi — boshqa birovning hamyoni haqida (balansi, valyutasi)
    xato xabarida ham hech narsa oshkor bo'lmaydi. Model.clean() dagi tekshiruv ikkinchi himoya bo'lib qoladi"""
    owned_relations = {}  # maydon nomi -> (queryset(user), "topilmadi" xabari)
    # Tahrirda bu maydonlarning JORIY qiymati o'chirilgan/yashirilgan bo'lsa ham qabul qilinadi: toifasi yoki a'zosi
    # keyin o'chirilgan eski yozuvni o'sha qiymatlar bilan PUT qilish mumkin bo'lsin (yangi tanlash esa rad etiladi)
    keep_current_relations = ()

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        user = getattr(request, "user", None)
        for name, (make_queryset, not_found) in self.owned_relations.items():
            field = fields.get(name)
            if field is None or field.read_only:
                continue
            model = field.queryset.model
            if user and user.is_authenticated:
                queryset = make_queryset(user)
                current_pk = getattr(self.instance, f"{name}_id", None) if name in self.keep_current_relations else None
                if current_pk:
                    queryset = model.objects.filter(Q(pk=current_pk) | Q(pk__in=queryset.values("pk")))
                field.queryset = queryset
            else:
                field.queryset = model.objects.none()
            field.error_messages["does_not_exist"] = not_found
            field.error_messages["incorrect_type"] = not_found
        return fields


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "status",
            "date_joined",
            "password",
        ]
        # status faqat admin panel / soft delete orqali o'zgaradi
        read_only_fields = ["id", "date_joined", "status"]

    def get_fields(self):
        fields = super().get_fields()
        # Modeldan keladigan UniqueValidator aynan bir xil nomda validate_username dan oldin ishlab, inglizcha
        # "A user with that username already exists." qaytarardi — xabar boshqa yo'llardagi bilan bir xil bo'lsin
        for validator in fields["username"].validators:
            if isinstance(validator, UniqueValidator):
                validator.message = USERNAME_TAKEN_MESSAGE
        return fields

    def validate_username(self, value):
        # Ro'yxatdan o'tish va profil bilan bir xil qoida: katta-kichik harfdan qat'i nazar band nom olinmaydi
        if self.instance is not None and value == self.instance.username:
            return value
        error = username_error(value, exclude_pk=getattr(self.instance, "pk", None))
        if error:
            raise serializers.ValidationError(error)
        return value

    def validate_email(self, value):
        # Email bilan ham kirish mumkin — shuning uchun ikki akkauntda bir xil email bo'lmasin
        if value and User.email_taken(value, exclude_pk=getattr(self.instance, "pk", None)):
            raise serializers.ValidationError("Bu email boshqa akkauntda ishlatilgan")
        return value

    def validate(self, attrs):
        password = attrs.get("password")
        if self.instance is None and password:
            attrs["password"] = password = password.strip()
            try:
                validate_password(password, user=User(username=attrs.get("username", "")))
            except DjangoValidationError as e:
                raise serializers.ValidationError({"password": password_errors_uz(e)})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

    def update(self, instance, validated_data):
        # Parol bu yerda o'zgartirilmaydi: aks holda u shifrlanmasdan saqlanib qoladi
        # va joriy parolni tekshirish chetlab o'tiladi
        if "password" in validated_data:
            raise serializers.ValidationError({
                "password": "Parolni /api/v1/auth/change-password/ orqali o'zgartiring"
            })
        return super().update(instance, validated_data)


class CategoryBaseSerializer(serializers.ModelSerializer):
    """Daromad va harajat toifalari uchun umumiy qismlar"""
    hidden_field = ""  # User'dagi yashirilgan toifalar maydoni (har bir serializer o'zinikini beradi)
    is_custom = serializers.SerializerMethodField()
    hidden = serializers.SerializerMethodField()

    def get_is_custom(self, obj):
        return obj.user_id is not None

    def get_hidden(self, obj):
        return bool(getattr(obj, "hidden", False))

    def validate_name(self, value):
        value = value.strip()
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else None
        qs = self.Meta.model.objects.filter(status=True, name__iexact=value)
        if user:
            hidden_ids = getattr(user, self.hidden_field).values_list("pk", flat=True)
            qs = qs.filter(Q(user__isnull=True) | Q(user=user)).exclude(pk__in=hidden_ids)
        else:
            qs = qs.filter(user__isnull=True)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        # Umumiy toifaning shaxsiy nusxasi yaratilayotganda: asl toifa o'rni almashadi, u bilan to'qnashmaydi
        if self.context.get("replaces_pk"):
            qs = qs.exclude(pk=self.context["replaces_pk"])
        if qs.exists():
            raise serializers.ValidationError("Bu nomli toifa allaqachon mavjud")
        return value


_CATEGORY_NAME_ERRORS = {"name": {"error_messages": {
    "blank": "Toifa nomi bo'sh bo'lishi mumkin emas",
    "max_length": "Toifa nomi 255 belgidan oshmasligi kerak",
}}}


class CategorySerializer(CategoryBaseSerializer):
    """Daromad turlari serializeri"""
    hidden_field = "hidden_income_categories"

    class Meta:
        model = Category
        fields = ["id", "name", "description", "icon", "status", "created_at", "is_custom", "hidden"]
        read_only_fields = ["id", "status", "created_at"]
        extra_kwargs = _CATEGORY_NAME_ERRORS


class ExpenseCategorySerializer(CategoryBaseSerializer):
    """Harajat turlari serializeri"""
    hidden_field = "hidden_expense_categories"

    class Meta:
        model = ExpenseCategory
        fields = ["id", "name", "description", "icon", "status", "created_at", "is_custom", "hidden"]
        read_only_fields = ["id", "status", "created_at"]
        extra_kwargs = _CATEGORY_NAME_ERRORS


class WalletSerializer(MoneyModelSerializer):
    user_name = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Wallet
        fields = [
            "id",
            "name",
            "summa",
            "currency",
            "user",
            "user_name",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "status", "created_at", "updated_at"]
        extra_kwargs = {
            "name": {"error_messages": {
                "blank": "Hamyon nomi bo'sh bo'lishi mumkin emas",
                "max_length": "Hamyon nomi 255 belgidan oshmasligi kerak",
            }},
            "currency": {"error_messages": {
                "blank": "Valyuta bo'sh bo'lishi mumkin emas",
                "max_length": "Valyuta 10 belgidan oshmasligi kerak",
            }},
            "summa": AMOUNT_FIELD,
        }

    def validate_currency(self, value):
        # Kurs bo'yicha avtomatik hisoblash uchun valyuta ISO kodida bo'lishi kerak (UZS, USD, EUR...)
        code = normalize_currency(value)
        if not is_valid_currency_code(code):
            raise serializers.ValidationError("Valyuta 3 harfli kod bo'lishi kerak: UZS, USD, EUR, RUB va h.k.")
        return code

    def validate_summa(self, value):
        if value < 0:
            raise serializers.ValidationError("Hamyon boshlang'ich balansi manfiy bo'lishi mumkin emas")
        return value

    def validate(self, attrs):
        # Balansni faqat Daromad/Harajat/O'tkazma orqali o'zgartirish mumkin —
        # mavjud hamyonning summasini to'g'ridan-to'g'ri tahrirlashga yo'l qo'yilmaydi
        if self.instance is not None and "summa" in attrs and attrs["summa"] != self.instance.summa:
            raise serializers.ValidationError({
                "summa": "Hamyon balansini to'g'ridan-to'g'ri o'zgartirib bo'lmaydi. "
                         "Daromad, Harajat yoki O'tkazma orqali o'zgartiring."
            })
        # Valyutani faqat operatsiyasi yo'q hamyonda (boshlang'ich balans xatosini tuzatish uchun) o'zgartirish mumkin.
        # Aks holda 1 000 000 UZS bir zumda 1 000 000 USD bo'lib, eski operatsiyalar boshqa valyutada hisoblanib qolardi
        if (self.instance is not None and "currency" in attrs
                and attrs["currency"] != normalize_currency(self.instance.currency)
                and self.instance.has_operations()):
            raise serializers.ValidationError({
                "currency": "Bu hamyonda operatsiyalar bor — valyutasini o'zgartirib bo'lmaydi. "
                            "Boshqa valyuta uchun yangi hamyon oching va pulni O'tkazma orqali o'tkazing."
            })
        return attrs


class MemberSerializer(serializers.ModelSerializer):
    """Oila a'zolari / yaqinlar serializeri"""
    class Meta:
        model = Member
        fields = ["id", "name", "kind", "status", "created_at"]
        read_only_fields = ["id", "status", "created_at"]


class IncomeSerializer(OwnedRelationsMixin, MoneyModelSerializer):
    """Daromad serializeri"""
    owned_relations = {
        "wallet": (_own_wallets, "Hamyon topilmadi"),
        "category": (_visible_categories(Category, "hidden_income_categories"), "Toifa topilmadi"),
    }
    keep_current_relations = ("category",)
    date = BoundedDateTimeField(required=False)
    wallet_name = serializers.CharField(source="wallet.name", read_only=True)
    wallet_currency = serializers.CharField(source="wallet.currency", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    user_name = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Income
        fields = [
            "id",
            "wallet",
            "wallet_name",
            "wallet_currency",
            "summa",
            "category",
            "category_name",
            "description",
            "date",
            "user",
            "user_name",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "status", "created_at", "updated_at"]
        extra_kwargs = {"summa": AMOUNT_FIELD}

    def validate_summa(self, value):
        if value <= 0:
            raise serializers.ValidationError("Daromad summasi 0 dan katta bo'lishi shart")
        return value

    def validate(self, attrs):
        wallet = attrs.get("wallet") or getattr(self.instance, "wallet", None)
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else (attrs.get("user") or getattr(self.instance, "user", None))
        summa = attrs.get("summa") if "summa" in attrs else getattr(self.instance, "summa", 0)

        if wallet and user and wallet.user_id != user.id:
            raise serializers.ValidationError({"wallet": "Tanlangan hamyon ushbu foydalanuvchiga tegishli emas"})

        category = attrs.get("category") or getattr(self.instance, "category", None)
        if category and user and category.user_id not in (None, user.id):
            raise serializers.ValidationError({"category": "Tanlangan kategoriya sizga tegishli emas"})

        if self.instance and wallet and summa:
            if self.instance.wallet_id == wallet.id and self.instance.summa > summa:
                diff = self.instance.summa - summa
                if wallet.summa < diff:
                    raise serializers.ValidationError({
                        "summa": f"Daromadni kamaytirish uchun hamyonda yetarli mablag' qolmagan (Hamyon balansi: {format_money(wallet.summa)} {wallet.currency})"
                    })
        return attrs


class ExpenseSerializer(OwnedRelationsMixin, MoneyModelSerializer):
    """Harajat serializeri — nima narsaga, qayerda, qachon"""
    owned_relations = {
        "wallet": (_own_wallets, "Hamyon topilmadi"),
        "category": (_visible_categories(ExpenseCategory, "hidden_expense_categories"), "Toifa topilmadi"),
        "member": (_own_members, "A'zo topilmadi"),
    }
    keep_current_relations = ("category", "member")
    date = BoundedDateTimeField(required=False)
    wallet_name = serializers.CharField(source="wallet.name", read_only=True)
    wallet_currency = serializers.CharField(source="wallet.currency", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    member_name = serializers.CharField(source="member.name", read_only=True, default=None)
    member_kind = serializers.CharField(source="member.kind", read_only=True, default=None)
    user_name = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Expense
        fields = [
            "id",
            "category",
            "category_name",
            "summa",
            "wallet",
            "wallet_name",
            "wallet_currency",
            "member",
            "member_name",
            "member_kind",
            "location",
            "description",
            "date",
            "user",
            "user_name",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "status", "created_at", "updated_at"]
        extra_kwargs = {"summa": AMOUNT_FIELD}

    def validate_summa(self, value):
        if value <= 0:
            raise serializers.ValidationError("Harajat summasi 0 dan katta bo'lishi shart")
        return value

    def validate(self, attrs):
        wallet = attrs.get("wallet") or getattr(self.instance, "wallet", None)
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else (attrs.get("user") or getattr(self.instance, "user", None))
        summa = attrs.get("summa") if "summa" in attrs else getattr(self.instance, "summa", 0)

        if wallet and user and wallet.user_id != user.id:
            raise serializers.ValidationError({"wallet": "Tanlangan hamyon ushbu foydalanuvchiga tegishli emas"})

        category = attrs.get("category") or getattr(self.instance, "category", None)
        if category and user and category.user_id not in (None, user.id):
            raise serializers.ValidationError({"category": "Tanlangan kategoriya sizga tegishli emas"})

        member = attrs.get("member") or getattr(self.instance, "member", None)
        if member and user and member.user_id != user.id:
            raise serializers.ValidationError({"member": "Tanlangan a'zo ushbu foydalanuvchiga tegishli emas"})

        if wallet and summa:
            if self.instance is None:
                if wallet.summa < summa:
                    raise serializers.ValidationError({
                        "summa": f"Hamyonda mablag' yetarli emas! Mavjud balans: {format_money(wallet.summa)} {wallet.currency}"
                    })
            else:
                old_summa = self.instance.summa if self.instance.wallet_id == wallet.id else 0
                required_balance = summa - old_summa
                if required_balance > 0 and wallet.summa < required_balance:
                    raise serializers.ValidationError({
                        "summa": f"Hamyonda mablag' yetarli emas! Qo'shimcha zarur: {format_money(required_balance)} {wallet.currency}, mavjud: {format_money(wallet.summa)} {wallet.currency}"
                    })
        return attrs


class TransferSerializer(OwnedRelationsMixin, MoneyModelSerializer):
    """Hamyonlararo o'tkazma serializeri"""
    owned_relations = {
        "from_wallet": (_own_wallets, "Chiqim hamyoni topilmadi"),
        "to_wallet": (_own_wallets, "Kirim hamyoni topilmadi"),
    }
    date = BoundedDateTimeField(required=False)
    from_wallet_name = serializers.CharField(source="from_wallet.name", read_only=True)
    to_wallet_name = serializers.CharField(source="to_wallet.name", read_only=True)
    user_name = serializers.CharField(source="user.username", read_only=True)
    from_currency = serializers.CharField(source="from_wallet.currency", read_only=True)
    to_currency = serializers.CharField(source="to_wallet.currency", read_only=True)

    class Meta:
        model = Transfer
        fields = [
            "id",
            "from_wallet",
            "from_wallet_name",
            "to_wallet",
            "to_wallet_name",
            "summa",
            "to_summa",
            "rate",
            "from_currency",
            "to_currency",
            "description",
            "date",
            "user",
            "user_name",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "rate", "status", "created_at", "updated_at"]
        # to_summa ixtiyoriy: berilmasa Markaziy bank kursi bo'yicha avtomatik hisoblanadi
        extra_kwargs = {"summa": AMOUNT_FIELD, "to_summa": {"required": False, "allow_null": True, **AMOUNT_FIELD}}

    def validate_summa(self, value):
        if value <= 0:
            raise serializers.ValidationError("O'tkazma summasi 0 dan katta bo'lishi kerak")
        return value

    def validate_to_summa(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Tushadigan summa 0 dan katta bo'lishi kerak")
        return value

    def _fill_to_summa(self, attrs, from_wallet, to_wallet, summa):
        """Tushadigan hamyonga qo'shiladigan summani (to_summa) va kursni aniqlaydi"""
        if from_wallet.currency == to_wallet.currency:
            attrs["to_summa"] = summa
            attrs["rate"] = 1
            return
        to_summa = attrs.get("to_summa")
        if to_summa:
            # Foydalanuvchi bank/ayirboshlash shoxobchasidagi haqiqiy summani o'zi kiritgan
            rate = round(Decimal(to_summa) / Decimal(summa), 8)
            if rate >= MAX_RATE:
                raise serializers.ValidationError({"to_summa": MAX_RATE_MESSAGE})
            # round() dan keyingi qiymat solishtiriladi: bazaga aynan shu yoziladi (0 bo'lib qolmasligi kerak)
            if rate < MIN_RATE:
                raise serializers.ValidationError({"to_summa": MIN_RATE_MESSAGE})
            attrs["rate"] = rate
            return
        if (self.instance is not None and self.instance.from_wallet_id == from_wallet.id
                and self.instance.to_wallet_id == to_wallet.id):
            # Eski o'tkazmaning faqat summasi tahrirlanmoqda — o'sha kunning kursi saqlanadi
            to_summa = quantize_money(Decimal(summa) * self.instance.rate)
            if to_summa <= 0:
                raise serializers.ValidationError({"summa": f"Summa juda kichik: kurs bo'yicha 0 {to_wallet.currency} bo'ladi"})
            if to_summa > MAX_AMOUNT:
                raise serializers.ValidationError({"summa": MAX_AMOUNT_MESSAGE})
            attrs["to_summa"] = to_summa
            return
        try:
            to_summa, rate = convert(summa, from_wallet.currency, to_wallet.currency)
        except CurrencyRateError:
            raise serializers.ValidationError({
                "to_summa": f"{from_wallet.currency} → {to_wallet.currency} kursini aniqlab bo'lmadi. "
                            "Tushadigan summani qo'lda kiriting."
            })
        if to_summa <= 0:
            raise serializers.ValidationError({
                "summa": f"Summa juda kichik: kurs bo'yicha 0 {to_wallet.currency} bo'ladi"
            })
        if to_summa > MAX_AMOUNT:
            raise serializers.ValidationError({"summa": MAX_AMOUNT_MESSAGE})
        if rate >= MAX_RATE:
            raise serializers.ValidationError({"summa": MAX_RATE_MESSAGE})
        if rate < MIN_RATE:
            raise serializers.ValidationError({"summa": MIN_RATE_MESSAGE})
        attrs["to_summa"] = to_summa
        attrs["rate"] = rate

    def _amounts_changed(self, attrs, from_wallet, to_wallet, summa):
        """Yangi o'tkazma yoki summa / hamyon / tushadigan summa haqiqatan o'zgargan tahrirmi. PUT da maydonlar
        o'zgarmagan qiymat bilan ham yuboriladi — ularni "o'zgargan" deb hisoblash kursni qayta hisoblatardi"""
        old = self.instance
        if old is None:
            return True
        return (
            summa != old.summa
            or from_wallet.id != old.from_wallet_id
            or to_wallet.id != old.to_wallet_id
            or attrs.get("to_summa") not in (None, old.to_summa)
        )

    def validate(self, attrs):
        from_wallet = attrs.get("from_wallet") or getattr(self.instance, "from_wallet", None)
        to_wallet = attrs.get("to_wallet") or getattr(self.instance, "to_wallet", None)
        summa = attrs.get("summa") if "summa" in attrs else getattr(self.instance, "summa", 0)

        if from_wallet and to_wallet and from_wallet.id == to_wallet.id:
            raise serializers.ValidationError({"to_wallet": "Bir xil hamyonlar o'rtasida o'tkazma qilib bo'lmaydi"})

        if from_wallet and to_wallet and summa:
            if self._amounts_changed(attrs, from_wallet, to_wallet, summa):
                self._fill_to_summa(attrs, from_wallet, to_wallet, summa)
            else:
                # Kurs 8 xonaga yaxlitlangan: summa o'zgarmasa to_summa ni undan qayta hisoblash uni jimgina o'zgartirardi
                attrs.pop("to_summa", None)

        if from_wallet and summa:
            if self.instance is None:
                if from_wallet.summa < summa:
                    raise serializers.ValidationError({
                        "summa": f"O'tkazish uchun hamyonda yetarli mablag' yo'q! Mavjud: {format_money(from_wallet.summa)} {from_wallet.currency}"
                    })
            else:
                old_summa = self.instance.summa if self.instance.from_wallet_id == from_wallet.id else 0
                required_balance = summa - old_summa
                if required_balance > 0 and from_wallet.summa < required_balance:
                    raise serializers.ValidationError({
                        "summa": f"O'tkazish uchun hamyonda yetarli mablag' yo'q! Mavjud: {format_money(from_wallet.summa)} {from_wallet.currency}"
                    })
        return attrs


class DebtSerializer(OwnedRelationsMixin, MoneyModelSerializer):
    """Qarzlar daftari serializeri"""
    owned_relations = {
        "wallet": (_own_wallets, "Hamyon topilmadi"),
    }
    wallet_name = serializers.CharField(source="wallet.name", read_only=True)
    user_name = serializers.CharField(source="user.username", read_only=True)
    remaining_summa = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = Debt
        fields = [
            "id",
            "user",
            "user_name",
            "person_name",
            "debt_type",
            "summa",
            "paid_summa",
            "remaining_summa",
            "currency",
            "wallet",
            "wallet_name",
            "due_date",
            "description",
            "is_settled",
            "status",
            "created_at",
            "updated_at",
        ]
        # paid_summa/is_settled faqat /repay/ orqali, status faqat DELETE orqali o'zgaradi:
        # aks holda hamyon balansi qarz bilan mos kelmay qoladi
        read_only_fields = ["id", "user", "remaining_summa", "paid_summa", "is_settled", "status", "created_at", "updated_at"]
        # Qarz doim hamyonga bog'lanadi: berilsa hamyondan yechiladi, olinsa hamyonga qo'shiladi
        extra_kwargs = {
            "wallet": {
                "required": True,
                "allow_null": False,
                "error_messages": {"required": "Hamyonni tanlang", "null": "Hamyonni tanlang"},
            },
            "summa": AMOUNT_FIELD,
        }

    def validate_due_date(self, value):
        return check_date_range(value)

    def validate(self, attrs):
        summa = attrs.get("summa", getattr(self.instance, "summa", 0))
        paid_summa = attrs.get("paid_summa", getattr(self.instance, "paid_summa", 0))
        if summa <= 0:
            raise serializers.ValidationError({"summa": "Qarz summasi musbat bo'lishi kerak"})
        if paid_summa > summa:
            raise serializers.ValidationError({"paid_summa": "Qaytarilgan summa umumiy qarzdan ko'p bo'lishi mumkin emas"})
        attrs["is_settled"] = paid_summa >= summa

        if "currency" in attrs:
            code = normalize_currency(attrs["currency"])
            if not is_valid_currency_code(code):
                raise serializers.ValidationError({"currency": "Valyuta 3 harfli kod bo'lishi kerak: UZS, USD, EUR..."})
            attrs["currency"] = code

        debt_type = attrs.get("debt_type", getattr(self.instance, "debt_type", None))
        wallet = attrs.get("wallet", getattr(self.instance, "wallet", None))
        if self.instance is not None:
            # To'lovlar eski turga ko'ra hamyonga yozilgan: tur almashsa balans 2 × to'langan summaga buziladi
            if debt_type != self.instance.debt_type and self.instance.paid_summa > 0:
                raise serializers.ValidationError({
                    "debt_type": "Qisman to'langan qarzning turini o'zgartirib bo'lmaydi. Qarzni o'chirib, yangisini kiriting"
                })
            # Summa hamyonlar orasida kurs bo'yicha o'girilmaydi: 100 USD qarz so'm hamyonida 100 UZS bo'lib qolardi
            if (wallet and wallet.id != self.instance.wallet_id
                    and normalize_currency(wallet.currency) != normalize_currency(self.instance.currency)):
                raise serializers.ValidationError({
                    "wallet": f"Qarz {self.instance.currency} da — uni {wallet.currency} hamyoniga ko'chirib bo'lmaydi. "
                              f"{self.instance.currency} valyutasidagi hamyonni tanlang"
                })
        if self.instance is None and wallet and debt_type == "give":
            if wallet.summa < summa:
                raise serializers.ValidationError({
                    "wallet": f"Qarz berish uchun hamyonda yetarli mablag' yo'q! Mavjud: {format_money(wallet.summa)} {wallet.currency}"
                })
        return attrs


class RecurringPaymentSerializer(OwnedRelationsMixin, MoneyModelSerializer):
    """Takroriy to'lov / tushum. next_date server tomonida hisoblanadi: o'tib ketgan sanalar orqaga qarab
    yozilmaydi — birinchi to'lov bugun yoki undan keyingi eng yaqin jadval sanasida bo'ladi"""
    owned_relations = {
        "wallet": (_own_wallets, "Hamyon topilmadi"),
        "expense_category": (_visible_categories(ExpenseCategory, "hidden_expense_categories"), "Toifa topilmadi"),
        "income_category": (_visible_categories(Category, "hidden_income_categories"), "Toifa topilmadi"),
        "member": (_own_members, "A'zo topilmadi"),
    }
    keep_current_relations = ("expense_category", "income_category", "member")
    wallet_name = serializers.CharField(source="wallet.name", read_only=True)
    wallet_currency = serializers.CharField(source="wallet.currency", read_only=True)
    category_name = serializers.SerializerMethodField()
    member_name = serializers.CharField(source="member.name", read_only=True, default=None)

    class Meta:
        model = RecurringPayment
        fields = [
            "id", "kind", "name", "wallet", "wallet_name", "wallet_currency", "summa",
            "expense_category", "income_category", "category_name", "member", "member_name",
            "frequency", "start_date", "next_date", "end_date", "remind_days", "last_error", "status", "created_at",
        ]
        read_only_fields = ["id", "next_date", "last_error", "status", "created_at"]
        extra_kwargs = {
            "summa": AMOUNT_FIELD,
            "name": {"error_messages": {"blank": "Nomini kiriting", "max_length": "Nomi 255 belgidan oshmasligi kerak"}},
            "remind_days": {"max_value": 30, "error_messages": {"max_value": "Eslatma eng ko'pi 30 kun oldin bo'lishi mumkin"}},
        }

    def get_category_name(self, obj):
        category = obj.income_category if obj.kind == RecurringPayment.KIND_INCOME else obj.expense_category
        return category.name if category else None

    def validate_summa(self, value):
        if value <= 0:
            raise serializers.ValidationError("Summa 0 dan katta bo'lishi kerak")
        return value

    def validate_start_date(self, value):
        return check_date_range(value)

    def validate_end_date(self, value):
        return check_date_range(value)

    def validate(self, attrs):
        def current(name):
            return attrs.get(name, getattr(self.instance, name, None))

        kind = current("kind")
        if kind == RecurringPayment.KIND_INCOME:
            if not current("income_category"):
                raise serializers.ValidationError({"income_category": "Daromad manbayini tanlang"})
            attrs["expense_category"] = None
            attrs["member"] = None
        else:
            if not current("expense_category"):
                raise serializers.ValidationError({"expense_category": "Harajat toifasini tanlang"})
            attrs["income_category"] = None
        start, end = current("start_date"), current("end_date")
        if start and end and end < start:
            raise serializers.ValidationError({"end_date": "Tugash sanasi boshlanish sanasidan oldin bo'lishi mumkin emas"})

        # Jadval o'zgarsa (yoki yangi bo'lsa) navbatdagi sana qaytadan hisoblanadi
        schedule_changed = self.instance is None or any(
            name in attrs and attrs[name] != getattr(self.instance, name) for name in ("start_date", "frequency"))
        if schedule_changed:
            probe = RecurringPayment(start_date=start, frequency=current("frequency") or "monthly")
            today = timezone.localdate()
            day = start
            # Uzoq o'tmishdagi "har kuni" jadvalda ham sikl cheklangan: yillar bo'yicha tez sakrab olinadi
            if day < today and probe.frequency in ("daily", "weekly"):
                step = 1 if probe.frequency == "daily" else 7
                day = day + timedelta(days=((today - day).days // step) * step)
            while day < today:
                day = probe.date_after(day)
            attrs["next_date"] = day
        return attrs


class SavingsGoalSerializer(OwnedRelationsMixin, MoneyModelSerializer):
    """Jamg'arma maqsadi: yig'ilgan summa — bog'langan hamyon balansi (saved)"""
    owned_relations = {"wallet": (_own_wallets, "Hamyon topilmadi")}
    wallet_name = serializers.CharField(source="wallet.name", read_only=True)
    wallet_currency = serializers.CharField(source="wallet.currency", read_only=True)
    saved = serializers.DecimalField(source="wallet.summa", max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = SavingsGoal
        fields = ["id", "name", "target", "wallet", "wallet_name", "wallet_currency", "saved", "deadline", "status", "created_at"]
        read_only_fields = ["id", "status", "created_at"]
        extra_kwargs = {
            "target": AMOUNT_FIELD,
            "name": {"error_messages": {"blank": "Maqsad nomini kiriting", "max_length": "Nomi 255 belgidan oshmasligi kerak"}},
        }

    def validate_target(self, value):
        if value <= 0:
            raise serializers.ValidationError("Maqsad summasi 0 dan katta bo'lishi kerak")
        return value

    def validate_deadline(self, value):
        return check_date_range(value)
