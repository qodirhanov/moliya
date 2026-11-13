from decimal import Decimal

from django.db import models, transaction
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.db.models import DecimalField, F, Q
from django.db.models.functions import Round

# Bitta summa yoki hamyon balansi uchun yuqori chegara (1 trillion). Summalar tiyin bilan (2 xonali kasr) saqlanadi,
# SQLite esa DecimalField arifmetikasini float'da bajaradi: float ~15-16 ta muhim raqamni aniq saqlaydi,
# 10^12 + 2 kasr xona = 15 raqam — shu chegaradan pastda tiyinlar aniq qoladi
MAX_AMOUNT = 10 ** 12
MAX_AMOUNT_MESSAGE = "Miqdor juda katta — eng ko'pi 1 000 000 000 000 bo'lishi mumkin"
MONEY_FIELD_KWARGS = {"max_digits": 15, "decimal_places": 2}


def money_expr(expression):
    """F('summa') ± x ifodasini 2 xonaga yaxlitlaydi. SQLite Decimal'ni float qilib hisoblaydi (0.1 + 0.2 =
    0.30000000000000004): har yangilashda yaxlitlanmasa, xato bazada yig'ilib boradi (1000 × 0.10 != 100.00)"""
    return Round(expression, 2, output_field=DecimalField(**MONEY_FIELD_KWARGS))

def format_money(value):
    """Xabarlar uchun: 1234567 -> "1,234,567", 1234.5 -> "1,234.50" (tiyin faqat nolga teng bo'lmasa ko'rsatiladi)"""
    value = Decimal(value).quantize(Decimal("0.01"))
    return f"{value:,.0f}" if value == value.to_integral_value() else f"{value:,.2f}"


# Sanalar uchun yil chegarasi. 0001-yil kabi sana Toshkent vaqtidan UTC ga o'girilganda Python sanasi
# chegarasidan chiqib ketadi va server xatosi (500) beradi — shuning uchun real oraliq bilan cheklanadi
MIN_YEAR = 1900
MAX_YEAR = 2100
DATE_RANGE_MESSAGE = f"Sana {MIN_YEAR}–{MAX_YEAR} yillar oralig'ida bo'lishi kerak"

# Foydalanuvchi nomi band bo'lganda ko'rsatiladigan xabar (tekshiruv, parallel ro'yxatdan o'tish va admin uchun bir xil)
USERNAME_TAKEN_MESSAGE = "Bu foydalanuvchi nomi allaqachon band"


def is_username_conflict(exc):
    """IntegrityError login nomining noyobligidan (username yoki username_key) chiqqanmi? Faqat shunday xatolar
    "nom band" javobiga aylanadi; boshqa butunlik xatolari (masalan, begona kalit) yashirilmasligi kerak.
    SQLite xabarida "mainapp_user.username_key", Postgres'da cheklov nomida "username_key" bo'ladi"""
    message = str(exc)
    return "username_key" in message or "mainapp_user.username" in message


class User(AbstractUser):
    """Foydalanuvchi modeli — Django auth tizimi bilan ishlaydi"""
    phone = models.CharField(max_length=20, blank=True, null=True)
    status = models.BooleanField(default=True)
    # Foydalanuvchi o'z ro'yxatidan olib tashlagan umumiy toifalar (boshqalarga ta'sir qilmaydi)
    hidden_income_categories = models.ManyToManyField("Category", blank=True, related_name="hidden_by")
    hidden_expense_categories = models.ManyToManyField("ExpenseCategory", blank=True, related_name="hidden_by")
    # Nomning katta-kichik harfga qaramaydigan ko'rinishi (NFKC + casefold): "Ali"/"ali" va "Али"/"али" bir xil kalit beradi.
    # SQLite'ning lower()/iexact funksiyasi faqat ASCII harflarni tushiradi, shuning uchun kirillcha nomlar uchun
    # qidiruv va noyoblik shu maydon bo'yicha yuritiladi. unique=True parallel ro'yxatdan o'tishda ham ikkita akkaunt
    # chiqmasligini bazaning o'zi kafolatlaydi. save() to'ldiradi; queryset.update(username=...) va bulk_create
    # save()'ni chetlab o'tadi — ularda username_key'ni qo'lda yozing.
    # max_length 150 emas: casefold nomni uzaytirishi mumkin ("ß" -> "ss", ba'zi harflar 3 belgigacha)
    username_key = models.CharField(max_length=450, unique=True, editable=False, blank=True)
    # "Barcha qurilmalardan chiqish" hisoblagichi: har bosilganda 1 ga oshadi va barcha eski sessiyalar yaroqsiz
    # bo'ladi (qarang: _get_session_auth_hash). 0 — hech qachon bosilmagan: sessiya belgisi Django'nikidek qoladi
    session_epoch = models.PositiveIntegerField(default=0, editable=False)
    # Ikki bosqichli kirish: parol to'g'ri bo'lsa ham emailga yuborilgan kod so'raladi (views.py: login_api)
    two_factor_enabled = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"

    # 1. name va surname mosligi (getter & setter)
    @property
    def name(self):
        return self.first_name

    @name.setter
    def name(self, value):
        self.first_name = value

    @property
    def surname(self):
        return self.last_name

    @surname.setter
    def surname(self, value):
        self.last_name = value

    @classmethod
    def email_taken(cls, email, exclude_pk=None):
        """Email boshqa akkauntning emaili YOKI login nomi bo'lsa band hisoblanadi: "@" li identifikator
        avval email bo'yicha qidiriladi, shuning uchun begona odam qurbonning "vera@gmail.com" loginini
        o'z emaili qilib, qurbonni kira olmaydigan qilib qo'ymasligi kerak"""
        qs = cls.objects.filter(Q(email__iexact=email) | Q(username_key=cls.make_username_key(email)))
        if exclude_pk:
            qs = qs.exclude(pk=exclude_pk)
        return qs.exists()

    @classmethod
    def make_username_key(cls, username):
        """Nomning katta-kichik harfga qaramaydigan kaliti (username_key). Python casefold() kirillcha, o'zbekcha va
        boshqa harflarni ham to'g'ri tushiradi — SQL lower()/iexact esa faqat ASCII'ni. Qidiruvda ham shu funksiya ishlatiladi"""
        return cls.normalize_username(str(username or "")).casefold()

    def clean(self):
        # Admin formasi (va full_clean) username_key'ni formada yo'q deb o'tkazib yuboradi — band nom shu yerda ushlanadi
        super().clean()
        if self.username:
            taken = User.objects.filter(username_key=self.make_username_key(self.username))
            if self.pk:
                taken = taken.exclude(pk=self.pk)
            if taken.exists():
                raise ValidationError({"username": USERNAME_TAKEN_MESSAGE})

    def save(self, *args, **kwargs):
        # create_user nomni NFKC bilan normallashtiradi, lekin profil/API/admin orqali o'zgartirishda (setattr + save)
        # u chetlab o'tilardi: "ＡＤＭＩＮ" "admin" bilan yonma-yon "ADMIN" bo'lib saqlanardi
        self.username = self.normalize_username(self.username)
        self.username_key = self.make_username_key(self.username)
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and "username" in update_fields and "username_key" not in update_fields:
            # Nom yozilsa, kalit ham birga yozilishi shart — aks holda ular bir-biridan ajralib qoladi
            kwargs["update_fields"] = [*update_fields, "username_key"]
        super().save(*args, **kwargs)

    def _get_session_auth_hash(self, secret=None):
        # Django bu metodni joriy kalit (get_session_auth_hash) ham, SECRET_KEY_FALLBACKS ham uchun chaqiradi —
        # shuning uchun shu yerda o'zgartiramiz, kalit almashtirish ham avvalgidek ishlayveradi
        if not self.session_epoch:
            # Hech qachon "barcha qurilmalardan chiqish" bosilmagan: belgi o'zgarmaydi, joriy sessiyalar saqlanadi
            return super()._get_session_auth_hash(secret=secret)
        # Parol belgisiga hisoblagich qo'shiladi: u oshgach eski sessiyalardagi belgi mos kelmaydi (get_user sessiyani
        # tozalaydi), parol o'zgarsa ham avvalgidek bekor bo'ladi
        return salted_hmac(
            "mainapp.models.User.session_epoch",
            f"{self.password}:{self.session_epoch}",
            secret=secret,
            algorithm="sha256",
        ).hexdigest()

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username

    def delete(self, *args, **kwargs):
        """Haqiqiy (qaytarib bo'lmas) o'chirish: foydalanuvchi qatori va unga CASCADE bilan bog'langan hamma narsa
        (hamyon, kirim/chiqim, o'tkazma, qarz, a'zo, toifa, maqsad, qurilma, kodlar, murojaat...) bazadan butunlay
        ketadi — email, login nomi va telefon ham. Shuning uchun qayta ro'yxatdan o'tishda ular band bo'lib qolmaydi.
        Avval bu yerda "soft delete" (close_account) bor edi: qator `deleted_N` nomi bilan qolar, shell/update orqali
        yoki eski kodda o'chirilgan akkauntlarda email band bo'lib qolardi. Admin (Django admin, /users/), foydalanuvchi
        o'zi o'chirishi va delete_inactive_accounts buyrug'i — hammasi shu yo'ldan o'tadi"""
        with transaction.atomic():
            return super().delete(*args, **kwargs)


####################################################


class Wallet(models.Model):
    """Hamyon — foydalanuvchining pul saqlash joyi"""
    name = models.CharField(max_length=255, help_text="Masalan: Naqd pul, Karta, Bank")
    summa = models.DecimalField(default=0, **MONEY_FIELD_KWARGS)
    currency = models.CharField(max_length=10, default="UZS")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wallets")
    # Maqsad hamyoni (maqsad qo'shilganda avtomatik ochiladi): undan xarajat qilib bo'lmaydi, pul unga faqat
    # boshqa hamyondan O'tkazma bilan tushadi. Maqsad o'chirilsa oddiy hamyonga aylanadi (False)
    is_goal = models.BooleanField(default=False)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Hamyon"
        verbose_name_plural = "Hamyonlar"

    def __str__(self):
        return f"{self.name} — {format_money(self.summa)} {self.currency}"

    def has_operations(self):
        """Hamyonda amaldagi (o'chirilmagan) daromad, harajat, o'tkazma, qarz, doimiy to'lov yoki maqsad bormi.
        Doimiy to'lov va maqsad summasi ham hamyon valyutasida: valyuta almashsa "3 000 000 so'm" 3 000 000 USD bo'lib qolardi"""
        return any(
            related.filter(status=True).exists()
            for related in (self.incomes, self.expenses, self.transfers_sent, self.transfers_received, self.debts,
                            self.recurring_payments, self.savings_goals)
        )

    def add_money(self, amount):
        """Hamyonga pul qo'shish (3. pk=None holati hisobga olingan, race-safe)"""
        if amount <= 0:
            raise ValueError("Qo'shiladigan miqdor musbat bo'lishi kerak")
        if amount > MAX_AMOUNT:
            raise ValueError(MAX_AMOUNT_MESSAGE)
        if not self.pk:
            if self.summa + amount > MAX_AMOUNT:
                raise ValueError("Hamyon qoldig'i juda katta bo'lib ketadi")
            self.summa += amount
            self.save()
            return
        updated = Wallet.objects.filter(pk=self.pk, summa__lte=MAX_AMOUNT - amount).update(
            summa=money_expr(F('summa') + amount)
        )
        self.refresh_from_db()
        if not updated:
            raise ValueError("Hamyon qoldig'i juda katta bo'lib ketadi")

    def withdraw_money(self, amount):
        """Hamyondan pul yechish (3. pk=None holati hisobga olingan, race-safe)"""
        if amount <= 0:
            raise ValueError("Yechiladigan miqdor musbat bo'lishi kerak")
        if amount > MAX_AMOUNT:
            raise ValueError(MAX_AMOUNT_MESSAGE)
        if not self.pk:
            if amount > self.summa:
                raise ValueError(f"Hamyonda yetarli mablag' yo'q! Mavjud: {format_money(self.summa)} {self.currency}")
            self.summa -= amount
            self.save()
            return

        updated = Wallet.objects.filter(pk=self.pk, summa__gte=amount).update(
            summa=money_expr(F('summa') - amount)
        )
        if not updated:
            self.refresh_from_db()
            raise ValueError(f"Hamyonda yetarli mablag' yo'q! Mavjud: {format_money(self.summa)} {self.currency}")
        self.refresh_from_db()

    def delete(self, *args, **kwargs):
        """Soft delete — hamyon o'chirilganda bog'langan operatsiyalar yo'qolmasligi uchun status=False qilinadi"""
        self.status = False
        self.save(update_fields=["status"])
        return (1, {self._meta.label: 1})


GOAL_WALLET_SPEND_MESSAGE = "Bu maqsad hamyoni — undan pul chiqarib bo'lmaydi. Pul unga faqat boshqa hamyondan O'tkazma bilan qo'shiladi"
GOAL_WALLET_INCOME_MESSAGE = "Maqsad hamyoniga pul faqat boshqa hamyondan O'tkazma bilan qo'shiladi"


def check_not_goal_wallet(wallet, message=GOAL_WALLET_SPEND_MESSAGE):
    """Maqsad hamyoni bilan taqiqlangan amal (xarajat, kirim, qarz, chiqim o'tkazmasi) rad etiladi"""
    if wallet is not None and wallet.is_goal:
        raise ValidationError(message)


def _wallet_for(instance, wallet_id, attr="wallet"):
    """instance.<attr> hamyoni wallet_id ga mos bo'lsa o'sha nusxa, aks holda bazadan (eskirgan nusxada hamyon boshqa bo'lishi mumkin)"""
    current = getattr(instance, attr)
    return current if current.pk == wallet_id else Wallet.objects.get(pk=wallet_id)


def apply_wallet_changes(new_effects, old_effects=()):
    """Yozuv saqlanganda hamyonlarga SOF farqni qo'llaydi. Effekt — (hamyon, ±summa) juftligi: musbat — hamyonga
    kiradi, manfiy — chiqadi. Yangi effektlardan eskilari ayirilib, hamyon id si bo'yicha yig'iladi: summa o'zgarmagan
    yozuvni tahrirlash (masalan faqat izoh) hamyonga umuman tegmaydi, aks holda eski summani to'liq qaytarib yangisini
    qayta yechish pul sarflangan hamyonda "mablag' yetarli emas" xatosini berardi.
    Avval kirimlar (add_money), keyin chiqimlar (withdraw_money) qo'llanadi; hammasi bitta tranzaksiyada —
    biror hamyonda xato bo'lsa butun o'zgarish orqaga qaytadi"""
    net = {}
    for wallet, amount in (*new_effects, *((w, -a) for w, a in old_effects)):
        entry = net.setdefault(wallet.pk, [wallet, 0])
        entry[1] += amount
    changes = [(wallet, amount) for wallet, amount in net.values() if amount]
    with transaction.atomic():
        for wallet, amount in changes:
            if amount > 0:
                wallet.add_money(amount)
        for wallet, amount in changes:
            if amount < 0:
                wallet.withdraw_money(-amount)


####################################################


class Member(models.Model):
    """Oila a'zosi / yaqin odam yoki butun oila — xarajat kimga qilinganini belgilash uchun (masalan: Abdulaziz ukam, Akamning oilasi)"""
    KIND_PERSON = "person"
    KIND_FAMILY = "family"
    KIND_CHOICES = [
        (KIND_PERSON, "Odam"),
        (KIND_FAMILY, "Oila"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="members")
    name = models.CharField(max_length=255, help_text="Masalan: Abdulaziz ukam, Akamning oilasi")
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default=KIND_PERSON, help_text="Bitta odam yoki butun oila")
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "A'zo"
        verbose_name_plural = "A'zolar"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        """Soft delete — a'zo o'chirilganda bog'langan harajatlar tarixi yo'qolmasligi uchun status=False qilinadi"""
        self.status = False
        self.save(update_fields=["status"])
        return (1, {self._meta.label: 1})


####################################################


class Category(models.Model):
    """Daromad turlari — oylik, freelance, sovg'a va h.k."""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True, help_text="Frontend uchun icon nomi")
    user = models.ForeignKey(
        "User", on_delete=models.CASCADE, null=True, blank=True, related_name="income_categories",
        help_text="Bo'sh bo'lsa umumiy kategoriya (hamma ko'radi), aks holda faqat shu foydalanuvchi ko'radi",
    )
    # Foydalanuvchi umumiy toifa nomini o'zgartirganda yaratilgan shaxsiy nusxa qaysi toifa o'rnini bosgani
    replaces = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="personal_copies",
        help_text="Shaxsiy nusxa bo'lsa — o'rnini bosgan umumiy toifa",
    )
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Daromad turi"
        verbose_name_plural = "Daromad turlari"

    def __str__(self):
        return self.name


####################################################


class ExpenseCategory(models.Model):
    """Harajat turlari — ovqat, transport, kiyim va h.k."""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True, help_text="Frontend uchun icon nomi")
    user = models.ForeignKey(
        "User", on_delete=models.CASCADE, null=True, blank=True, related_name="expense_categories",
        help_text="Bo'sh bo'lsa umumiy kategoriya (hamma ko'radi), aks holda faqat shu foydalanuvchi ko'radi",
    )
    # Foydalanuvchi umumiy toifa nomini o'zgartirganda yaratilgan shaxsiy nusxa qaysi toifa o'rnini bosgani
    replaces = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="personal_copies",
        help_text="Shaxsiy nusxa bo'lsa — o'rnini bosgan umumiy toifa",
    )
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Harajat turi"
        verbose_name_plural = "Harajat turlari"

    def __str__(self):
        return self.name


####################################################


def _local_day(value):
    """Operatsiya vaqtining mahalliy (Asia/Tashkent) sanasi; vaqt bo'lmasa None"""
    if value is None:
        return None
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.date()


def prepare_uzs_rate(instance):
    """Daromad/harajat yozilayotgan paytdagi kursni (1 birlik hamyon valyutasi = ? so'm) instance.uzs_rate ga qo'yadi.
    Operatsiya sanasi bugundan oldin bo'lsa (qo'lda kiritilgan eski sana, takroriy to'lovning o'tkazib yuborilgan kuni)
    o'sha kunning Markaziy bank kursi olinadi; olib bo'lmasa bugungi kurs ishlatiladi.
    Faqat yangi yozuvda, tahrir yozuvni BOSHQA valyutali hamyonga ko'chirganda yoki sanasini BOSHQA kunga
    o'tkazganda o'zgaradi; boshqa tahrirlarda (summa, izoh, toifa, shu valyutali boshqa hamyon) saqlangan kurs tegilmaydi. Kursni aniqlab bo'lmasa NULL qoladi:
    kurs tufayli foydalanuvchi operatsiyasi to'xtab qolmasin (statistika bunday qatorni bugungi kurs bilan hisoblaydi).
    save() da tranzaksiyadan OLDIN chaqiriladi: kurs saqlanmagan bo'lsa get_rate_to_uzs cbu.uz ga (10 soniyagacha)
    murojaat qiladi, bu vaqtda baza yozuv qulfini ushlab turmasligi kerak. O'zgargan bo'lsa True qaytaradi"""
    from .currency import CurrencyRateError, get_rate_to_uzs, get_rate_to_uzs_on, normalize_currency  # currency.py models.py ni import qiladi

    old = None
    if instance.pk:
        old = type(instance).objects.filter(pk=instance.pk).values_list("wallet__currency", "date").first()
    day = _local_day(instance.date)
    if old is None:
        if instance.uzs_rate is not None:
            return False  # yangi yozuvga kurs aniq berilgan
    elif (normalize_currency(old[0]) == normalize_currency(instance.wallet.currency)
          and _local_day(old[1]) == day):
        return False
    try:
        if day is not None and day < timezone.localdate():
            instance.uzs_rate = get_rate_to_uzs_on(instance.wallet.currency, day)
        else:
            instance.uzs_rate = get_rate_to_uzs(instance.wallet.currency)
    except CurrencyRateError:
        instance.uzs_rate = None
    return True


class Income(models.Model):
    """Daromad — hamyonga pul kiritish"""
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="incomes")
    summa = models.DecimalField(**MONEY_FIELD_KWARGS)
    uzs_rate = models.DecimalField(
        max_digits=20, decimal_places=8, null=True, blank=True,
        help_text="Operatsiya yozilgan paytdagi kurs: 1 birlik hamyon valyutasi necha so'm (bo'sh bo'lsa statistikada bugungi kurs olinadi)",
    )
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="incomes")
    description = models.TextField(blank=True, null=True)
    date = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="incomes")
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Daromad"
        verbose_name_plural = "Daromadlar"
        ordering = ["-date"]

    def __str__(self):
        return f"Kirim: {format_money(self.summa)} — {self.category}"

    def clean(self):
        # 5. Hamyon egasi bilan amaliyot qiluvchi foydalanuvchi tekshiruvi
        if self.wallet_id and self.user_id and self.wallet.user_id != self.user_id:
            raise ValidationError("Ushbu hamyon boshqa foydalanuvchiga tegishli!")
        if self.status and self.wallet_id:
            check_not_goal_wallet(self.wallet, GOAL_WALLET_INCOME_MESSAGE)

    def balance_effects(self):
        """Hamyonga ta'siri: faol daromad hamyonga kiradi"""
        return [(self.wallet, self.summa)] if self.status else []

    def save(self, *args, **kwargs):
        self.clean()
        if self.summa <= 0:
            raise ValueError("Kirim miqdori musbat bo'lishi kerak")

        # Kursni olish tarmoqqa chiqishi mumkin — tranzaksiyadan oldin
        if prepare_uzs_rate(self) and kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = {*kwargs["update_fields"], "uzs_rate"}

        with transaction.atomic():
            old = Income.objects.filter(pk=self.pk).first() if self.pk else None
            apply_wallet_changes(self.balance_effects(), old.balance_effects() if old else ())
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """4. Soft delete — Django standartiga muvofiq (count, dict) qaytaradi"""
        with transaction.atomic():
            # Qatorni atomik "egallaymiz": view'dagi get_object() eskirgan bo'lishi mumkin — ikki parallel DELETE ikkalasi ham status=True ko'rardi
            if Income.objects.filter(pk=self.pk, status=True).update(status=False, updated_at=timezone.now()) == 1:
                # Summa va hamyon egallashdan KEYIN bazadan o'qiladi: eskirgan nusxada tahrirdan oldingi qiymat bo'lishi mumkin
                summa, wallet_id = Income.objects.values_list("summa", "wallet_id").get(pk=self.pk)
                _wallet_for(self, wallet_id).withdraw_money(summa)
            self.status = False
        return (1, {self._meta.label: 1})


####################################################


class Expense(models.Model):
    """Harajat — nima narsaga (category), qayerda (location), qachon (date) sarflandi"""
    category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True, related_name="expenses")
    summa = models.DecimalField(**MONEY_FIELD_KWARGS)
    uzs_rate = models.DecimalField(
        max_digits=20, decimal_places=8, null=True, blank=True,
        help_text="Operatsiya yozilgan paytdagi kurs: 1 birlik hamyon valyutasi necha so'm (bo'sh bo'lsa statistikada bugungi kurs olinadi)",
    )
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="expenses")
    member = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True, related_name="expenses", help_text="Xarajat kimga qilindi (ixtiyoriy)")
    location = models.CharField(max_length=255, blank=True, null=True, help_text="Qayerda sarflandi (joylashuv)")
    description = models.TextField(blank=True, null=True, help_text="Qo'shimcha izoh")
    date = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="expenses")
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Harajat"
        verbose_name_plural = "Harajatlar"
        ordering = ["-date"]

    def __str__(self):
        cat = self.category.name if self.category else "Chiqim"
        return f"{cat}: {format_money(self.summa)}"

    def clean(self):
        # 5. Hamyon egasi bilan amaliyot qiluvchi foydalanuvchi tekshiruvi
        if self.wallet_id and self.user_id and self.wallet.user_id != self.user_id:
            raise ValidationError("Ushbu hamyon boshqa foydalanuvchiga tegishli! Begona hamyondan xarajat qilib bo'lmaydi.")
        if self.member_id and self.user_id and self.member.user_id != self.user_id:
            raise ValidationError("Tanlangan a'zo sizga tegishli emas!")
        if self.status and self.wallet_id:
            check_not_goal_wallet(self.wallet)

    def balance_effects(self):
        """Hamyonga ta'siri: faol harajat hamyondan chiqadi"""
        return [(self.wallet, -self.summa)] if self.status else []

    def save(self, *args, **kwargs):
        self.clean()
        if self.summa <= 0:
            raise ValueError("Chiqim miqdori musbat bo'lishi kerak")

        # Kursni olish tarmoqqa chiqishi mumkin — tranzaksiyadan oldin
        if prepare_uzs_rate(self) and kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = {*kwargs["update_fields"], "uzs_rate"}

        with transaction.atomic():
            old = Expense.objects.filter(pk=self.pk).first() if self.pk else None
            apply_wallet_changes(self.balance_effects(), old.balance_effects() if old else ())
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """4. Soft delete — Django standartiga muvofiq (count, dict) qaytaradi"""
        with transaction.atomic():
            # Qatorni atomik "egallaymiz": view'dagi get_object() eskirgan bo'lishi mumkin — ikki parallel DELETE ikkalasi ham status=True ko'rardi
            if Expense.objects.filter(pk=self.pk, status=True).update(status=False, updated_at=timezone.now()) == 1:
                summa, wallet_id = Expense.objects.values_list("summa", "wallet_id").get(pk=self.pk)
                _wallet_for(self, wallet_id).add_money(summa)
            self.status = False
        return (1, {self._meta.label: 1})


####################################################


class Transfer(models.Model):
    """2. Hamyonlararo o'tkazma (masalan: Naqd puldan -> Plastik kartaga)"""
    from_wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transfers_sent")
    to_wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transfers_received")
    summa = models.DecimalField(**MONEY_FIELD_KWARGS, help_text="Chiqadigan hamyondan yechilgan summa (uning valyutasida)")
    to_summa = models.DecimalField(**MONEY_FIELD_KWARGS, help_text="Tushadigan hamyonga qo'shilgan summa (uning valyutasida)")
    rate = models.DecimalField(max_digits=20, decimal_places=8, default=1, help_text="1 birlik chiqim valyutasi = rate birlik kirim valyutasi")
    description = models.TextField(blank=True, null=True)
    date = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transfers")
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "O'tkazma"
        verbose_name_plural = "O'tkazmalar"
        ordering = ["-date"]

    def __str__(self):
        return f"O'tkazma: {self.from_wallet.name} -> {self.to_wallet.name} ({format_money(self.summa)})"

    def clean(self):
        if self.from_wallet_id == self.to_wallet_id:
            raise ValidationError("Bir xil hamyonlar o'rtasida o'tkazma qilib bo'lmaydi")
        # 5. Foydalanuvchi hamyoni tekshiruvi
        if self.from_wallet_id and self.user_id and self.from_wallet.user_id != self.user_id:
            raise ValidationError("Chiqim hamyoni sizga tegishli emas!")
        if self.to_wallet_id and self.user_id and self.to_wallet.user_id != self.user_id:
            raise ValidationError("Kirim hamyoni sizga tegishli emas!")
        if self.status and self.from_wallet_id:
            check_not_goal_wallet(self.from_wallet)

    def balance_effects(self):
        """Hamyonlarga ta'siri: faol o'tkazma chiqim hamyonidan chiqadi, kirim hamyoniga tushadi"""
        return [(self.from_wallet, -self.summa), (self.to_wallet, self.to_summa)] if self.status else []

    def save(self, *args, **kwargs):
        self.clean()
        if self.to_summa is None and self.from_wallet.currency == self.to_wallet.currency:
            self.to_summa = self.summa
        if self.summa <= 0 or not self.to_summa or self.to_summa <= 0:
            raise ValueError("O'tkazma miqdori musbat bo'lishi kerak")

        with transaction.atomic():
            old = Transfer.objects.filter(pk=self.pk).first() if self.pk else None
            apply_wallet_changes(self.balance_effects(), old.balance_effects() if old else ())
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """4. Soft delete — Django standartiga muvofiq (count, dict) qaytaradi"""
        with transaction.atomic():
            # Qatorni atomik "egallaymiz": view'dagi get_object() eskirgan bo'lishi mumkin — ikki parallel DELETE ikkalasi ham status=True ko'rardi
            if Transfer.objects.filter(pk=self.pk, status=True).update(status=False, updated_at=timezone.now()) == 1:
                summa, to_summa, from_id, to_id = Transfer.objects.values_list(
                    "summa", "to_summa", "from_wallet_id", "to_wallet_id").get(pk=self.pk)
                _wallet_for(self, from_id, "from_wallet").add_money(summa)
                _wallet_for(self, to_id, "to_wallet").withdraw_money(to_summa)
            self.status = False
        return (1, {self._meta.label: 1})


####################################################


class Debt(models.Model):
    """2. Qarzlar daftari — kimga qarz berdim / kimdan qarz oldim"""
    DEBT_TYPE_CHOICES = (
        ("give", "Qarz berdim (menga qaytarishadi)"),
        ("take", "Qarz oldim (men qaytarishim kerak)"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="debts")
    person_name = models.CharField(max_length=255, help_text="Shaxs ismi / tashkilot")
    debt_type = models.CharField(max_length=10, choices=DEBT_TYPE_CHOICES)
    summa = models.DecimalField(**MONEY_FIELD_KWARGS, help_text="Umumiy qarz summasi")
    paid_summa = models.DecimalField(default=0, **MONEY_FIELD_KWARGS, help_text="Hozirgacha qaytarilgan summa")
    currency = models.CharField(max_length=10, default="UZS", help_text="Qarz valyutasi (hamyon tanlansa — hamyon valyutasi)")
    wallet = models.ForeignKey(Wallet, on_delete=models.SET_NULL, null=True, blank=True, related_name="debts")
    due_date = models.DateField(null=True, blank=True, help_text="Qaytarish muddati")
    description = models.TextField(blank=True, null=True)
    is_settled = models.BooleanField(default=False, help_text="Qarz to'liq yopildimi")
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Qarz"
        verbose_name_plural = "Qarzlar"
        ordering = ["-created_at"]

    @property
    def remaining_summa(self):
        """Qolgan qarz miqdori"""
        return max(0, self.summa - self.paid_summa)

    def __str__(self):
        action = "Qarz berdim" if self.debt_type == "give" else "Qarz oldim"
        return f"{self.person_name} ({action}: {format_money(self.summa)} {self.currency})"

    def clean(self):
        if self.wallet and self.user and self.wallet.user_id != self.user_id:
            raise ValidationError("Tanlangan hamyon sizga tegishli emas!")
        if self.status and self.wallet:
            check_not_goal_wallet(self.wallet, "Maqsad hamyonini qarzga bog'lab bo'lmaydi — boshqa hamyonni tanlang")
        if self.paid_summa > self.summa:
            raise ValidationError("Qaytarilgan miqdor umumiy qarzdan oshib ketishi mumkin emas!")
        if not self.pk and self.wallet and self.debt_type == "give":
            if self.wallet.summa < self.summa:
                raise ValidationError(f"Hamyonda yetarli mablag' yo'q! Mavjud: {format_money(self.wallet.summa)} {self.wallet.currency}")

    def balance_effects(self):
        """Hamyonga ta'siri (yaratilgandagi): berilgan qarz hamyondan chiqadi, olingan qarz hamyonga kiradi.
        To'lovlar (/repay/) hamyonga alohida yoziladi, shuning uchun bu yerga kirmaydi"""
        sign = {"give": -1, "take": 1}.get(self.debt_type, 0)
        return [(self.wallet, sign * self.summa)] if self.status and self.wallet and sign else []

    def save(self, *args, **kwargs):
        self.clean()
        # Hamyonga bog'langan qarz summasi hamyondan yechiladi/qo'shiladi — demak u hamyon valyutasida
        if self.wallet:
            self.currency = self.wallet.currency
        self.currency = (self.currency or "UZS").upper()
        # Har saqlashda qayta hisoblanadi: yopilgan qarzning summasi oshirilsa u yana ochiq bo'ladi
        self.is_settled = self.paid_summa >= self.summa

        with transaction.atomic():
            old = Debt.objects.filter(pk=self.pk).first() if self.pk else None
            if old:
                self.check_edit_allowed(old)
            # Sof farq: repay() orqali faqat paid_summa o'zgarsa (yoki izoh tahrirlansa) hamyonga tegilmaydi
            apply_wallet_changes(self.balance_effects(), old.balance_effects() if old else ())
            super().save(*args, **kwargs)

    def check_edit_allowed(self, old):
        """Balansni buzadigan tahrirlarni rad etadi (serializer'dagi tekshiruvning ikkinchi himoyasi)"""
        if old.paid_summa > 0 and old.debt_type != self.debt_type:
            # To'lovlar eski turga ko'ra yozilgan (give: hamyonga qo'shilgan) — tur almashsa balans 2 × to'langan summaga buziladi
            raise ValidationError("Qisman to'langan qarzning turini o'zgartirib bo'lmaydi")
        if self.wallet and old.wallet_id != self.wallet_id and (old.currency or "UZS").upper() != self.wallet.currency.upper():
            # Summa hamyonlar orasida kurs bo'yicha o'girilmaydi: 100 USD qarz so'm hamyonida 100 UZS bo'lib qolardi
            raise ValidationError(
                f"Qarz {old.currency} da — uni {self.wallet.currency} hamyoniga ko'chirib bo'lmaydi. "
                f"{old.currency} hamyonini tanlang"
            )

    def delete(self, *args, **kwargs):
        """4. Soft delete — qarz bekor qilinganda hamyon balansini atomik tiklaydi"""
        with transaction.atomic():
            # Qatorni atomik "egallaymiz": view'dagi get_object() eskirgan bo'lishi mumkin — ikki parallel DELETE ikkalasi ham status=True ko'rardi
            if Debt.objects.filter(pk=self.pk, status=True).update(status=False, updated_at=timezone.now()) == 1:
                # Qoldiq egallashdan KEYIN bazadan qayta o'qiladi: eskirgan nusxada repay'dan oldingi paid_summa bo'lishi mumkin
                fresh = Debt.objects.filter(pk=self.pk).values("summa", "paid_summa", "wallet_id", "debt_type").first()
                remaining = max(0, fresh["summa"] - fresh["paid_summa"]) if fresh else 0
                if fresh and fresh["wallet_id"] and remaining > 0:
                    wallet = self.wallet if self.wallet_id == fresh["wallet_id"] else Wallet.objects.get(pk=fresh["wallet_id"])
                    if fresh["debt_type"] == "give":
                        wallet.add_money(remaining)
                    elif fresh["debt_type"] == "take":
                        wallet.withdraw_money(remaining)
            self.status = False
        return (1, {self._meta.label: 1})

####################################################


class PasswordResetCode(models.Model):
    """Parolni tiklash kodi — foydalanuvchi emailiga yuboriladi (kodning o'zi emas, xeshi saqlanadi)"""
    CODE_LIFETIME_MINUTES = 15
    MAX_ATTEMPTS = 5

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_reset_codes")
    code_hash = models.CharField(max_length=128)
    attempts = models.PositiveSmallIntegerField(default=0)
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        verbose_name = "Parol tiklash kodi"
        verbose_name_plural = "Parol tiklash kodlari"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} — {self.created_at:%Y-%m-%d %H:%M}"

    @property
    def is_usable(self):
        return not self.used and self.attempts < self.MAX_ATTEMPTS and timezone.now() < self.expires_at

    def check_code(self, code):
        return check_password(code, self.code_hash)


class UserDevice(models.Model):
    """Akkauntga kirilgan qurilma (Sozlamalar → Qurilmalar). Har bir sessiyaga bitta yozuv: kirishda
    (middleware.remember_login_time) yoki birinchi so'rovda (DeviceTrackingMiddleware) yaratiladi.
    Qurilmani chiqarish — uning sessiyasini o'chirish (devices.end_device)"""
    # Boshqa qurilmalarni chiqarish uchun joriy qurilmada shuncha kun oldin kirilgan bo'lishi kerak:
    # o'g'irlangan sessiya egasining o'zini akkauntdan chiqarib yubora olmasligi uchun
    MIN_DAYS_TO_TERMINATE = 15

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="devices")
    session_key = models.CharField(max_length=40, unique=True)
    user_agent = models.CharField(max_length=512, blank=True)
    ip = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(help_text="Shu qurilmada akkauntga kirilgan vaqt")
    last_seen = models.DateTimeField(help_text="Oxirgi so'rov vaqti (bir necha daqiqa aniqlikda)")

    class Meta:
        verbose_name = "Qurilma"
        verbose_name_plural = "Qurilmalar"
        ordering = ["-last_seen"]

    def __str__(self):
        return f"{self.user} — {self.created_at:%Y-%m-%d %H:%M}"


class LoginCode(models.Model):
    """Ikki bosqichli kirish kodi. Parol to'g'ri kiritilgach emailga yuboriladi; kod tasdiqlangandagina sessiya
    ochiladi. Kodning o'zi emas, xeshi saqlanadi (PasswordResetCode kabi). token — brauzerda saqlanadigan
    tasodifiy kalit: kodni faqat parolni kiritgan o'sha urinish tasdiqlay oladi"""
    CODE_LIFETIME_MINUTES = 10
    MAX_ATTEMPTS = 5

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="login_codes")
    token = models.CharField(max_length=64, unique=True)
    code_hash = models.CharField(max_length=128)
    attempts = models.PositiveSmallIntegerField(default=0)
    used = models.BooleanField(default=False)
    # Email almashtirish kodi (2FA yoqiq akkaunt): yangi manzil kod bilan birga serverda saqlanadi va tasdiqlashda
    # so'rovdan emas, aynan shu yerdan olinadi. Boshqa maqsadlardagi (kirish, yoqish) kodlarda bo'sh
    new_email = models.EmailField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        verbose_name = "Kirish kodi (2FA)"
        verbose_name_plural = "Kirish kodlari (2FA)"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} — {self.created_at:%Y-%m-%d %H:%M}"

    @property
    def is_usable(self):
        return not self.used and self.attempts < self.MAX_ATTEMPTS and timezone.now() < self.expires_at

    def check_code(self, code):
        return check_password(code, self.code_hash)


####################################################


def add_months(day, months, anchor_day):
    """day dan months oy keyingi sana; kun anchor_day ga qaytariladi, oyda bunday kun bo'lmasa — oyning oxirgi kuni.
    Masalan har oy 31-sanadagi to'lov: 31-yanvar -> 28/29-fevral -> 31-mart (anchor tufayli 28 da qolib ketmaydi)"""
    import calendar
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    return day.replace(year=year, month=month, day=min(anchor_day, calendar.monthrange(year, month)[1]))


class RecurringPayment(models.Model):
    """Takroriy to'lov yoki tushum: ijara, kommunal, obuna, oylik maosh. Muddati kelganda daromad/harajat
    avtomatik yoziladi (recurring.process_due), muddatidan oldin esa xabarlarda eslatiladi"""
    KIND_EXPENSE = "expense"
    KIND_INCOME = "income"
    KIND_CHOICES = [(KIND_EXPENSE, "Harajat"), (KIND_INCOME, "Daromad")]
    FREQ_CHOICES = [("daily", "Har kuni"), ("weekly", "Har hafta"), ("monthly", "Har oy"), ("yearly", "Har yil")]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recurring_payments")
    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    name = models.CharField(max_length=255, help_text="Masalan: Ijara, Internet, Maosh")
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="recurring_payments")
    summa = models.DecimalField(**MONEY_FIELD_KWARGS)
    expense_category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="recurring_payments")
    income_category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="recurring_payments")
    member = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True, related_name="recurring_payments")
    frequency = models.CharField(max_length=10, choices=FREQ_CHOICES, default="monthly")
    start_date = models.DateField(help_text="Birinchi to'lov sanasi; oylik/yillik to'lov kuni shundan olinadi")
    next_date = models.DateField(help_text="Navbatdagi to'lov sanasi")
    end_date = models.DateField(null=True, blank=True, help_text="Shu sanadan keyin to'xtaydi (ixtiyoriy)")
    remind_days = models.PositiveSmallIntegerField(default=2, help_text="Necha kun oldin eslatilsin")
    # Oxirgi avtomatik yozish muvaffaqiyatsiz bo'lsa (masalan hamyonda pul yetmadi) — sababi; muvaffaqiyatli bo'lsa bo'sh
    last_error = models.CharField(max_length=255, blank=True)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Takroriy to'lov"
        verbose_name_plural = "Takroriy to'lovlar"
        ordering = ["next_date", "id"]

    def __str__(self):
        return f"{self.name}: {format_money(self.summa)} ({self.get_frequency_display()})"

    def date_after(self, day):
        """day dan keyingi to'lov sanasi"""
        from datetime import timedelta
        if self.frequency == "daily":
            return day + timedelta(days=1)
        if self.frequency == "weekly":
            return day + timedelta(weeks=1)
        return add_months(day, 12 if self.frequency == "yearly" else 1, self.start_date.day)


class SavingsGoal(models.Model):
    """Jamg'arma maqsadi. Bitta hamyonga bog'lanadi: yig'ilgan summa — o'sha hamyon balansi. Yangi maqsadga o'z
    hamyoni ochiladi (Wallet.is_goal): pul unga faqat O'tkazma orqali qo'yiladi, undan xarajat qilib bo'lmaydi.
    Eski maqsadlar oddiy hamyonga bog'langan bo'lishi mumkin — ularga cheklov qo'yilmaydi"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="savings_goals")
    name = models.CharField(max_length=255, help_text="Masalan: Mashina, Ta'til")
    target = models.DecimalField(**MONEY_FIELD_KWARGS, help_text="Maqsad summasi (hamyon valyutasida)")
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="savings_goals")
    deadline = models.DateField(null=True, blank=True)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Jamg'arma maqsadi"
        verbose_name_plural = "Jamg'arma maqsadlari"
        ordering = ["deadline", "id"]

    def __str__(self):
        return f"{self.name}: {format_money(self.target)}"


####################################################


class ExchangeRate(models.Model):
    """Markaziy bank kursi (1 birlik valyuta necha so'm). Har soatda yangilanadi;
    internet bo'lmasa oxirgi saqlangan kurs ishlatiladi (qarang: currency.py)"""
    currency = models.CharField(max_length=10, primary_key=True)
    rate = models.DecimalField(max_digits=20, decimal_places=8, help_text="1 birlik = rate UZS")
    rate_date = models.CharField(max_length=20, blank=True, help_text="Markaziy bank e'lon qilgan sana")
    diff = models.DecimalField(
        max_digits=20, decimal_places=8, null=True, blank=True,
        help_text="Oldingi kunga nisbatan o'zgarish (1 birlik uchun, so'mda)",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Valyuta kursi"
        verbose_name_plural = "Valyuta kurslari"

    def __str__(self):
        return f"1 {self.currency} = {self.rate} UZS"


####################################################


class SupportMessage(models.Model):
    """Yordam chati (Sozlamalar → Yordam): foydalanuvchi bilan admin o'rtasidagi yozishma. Har foydalanuvchining
    bitta suhbati bor — xabarlar user bo'yicha guruhlanadi. from_admin=True bo'lsa javobni admin panelidan xodim yozgan.
    is_read — qabul qiluvchi tomon o'qiganmi: foydalanuvchi xabari uchun admin, admin javobi uchun foydalanuvchi"""
    MAX_LENGTH = 2000

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="support_messages")
    from_admin = models.BooleanField(default=False)
    # Javob yozgan xodim (foydalanuvchi xabarida bo'sh). Xodim o'chirilsa javob saqlanib qoladi
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    text = models.TextField(max_length=MAX_LENGTH)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Yordam xabari"
        verbose_name_plural = "Yordam xabarlari"
        ordering = ["id"]
        indexes = [models.Index(fields=["user", "id"]), models.Index(fields=["from_admin", "is_read"])]

    def __str__(self):
        return f"{self.user} — {'admin' if self.from_admin else 'foydalanuvchi'}: {self.text[:40]}"


class AdminNotice(models.Model):
    """Admin yuborgan xabar (admin panel → Xabar yuborish): navbar qo'ng'irog'idagi "Xabarlar"da alohida ko'rinishda chiqadi.
    recipient bo'sh bo'lsa — hammaga: yuborilgan paytda ro'yxatdan o'tgan barcha foydalanuvchilar ko'radi
    (keyin qo'shilganlarga eski e'lonlar tushmaydi). Kim o'qigani AdminNoticeRead da"""
    MAX_LENGTH = 1000

    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="admin_notices")
    text = models.TextField(max_length=MAX_LENGTH)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Admin xabari"
        verbose_name_plural = "Admin xabarlari"
        ordering = ["-id"]
        indexes = [models.Index(fields=["recipient", "id"])]

    def __str__(self):
        return f"{self.recipient or 'Hammaga'}: {self.text[:40]}"


class AdminNoticeRead(models.Model):
    notice = models.ForeignKey(AdminNotice, on_delete=models.CASCADE, related_name="reads")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="+")
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["notice", "user"], name="admin_notice_read_once")]
