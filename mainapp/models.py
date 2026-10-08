from django.db import models, transaction
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import F


class User(AbstractUser):
    """Foydalanuvchi modeli — Django auth tizimi bilan ishlaydi"""
    phone = models.CharField(max_length=20, blank=True, null=True)
    status = models.BooleanField(default=True)

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
        qs = cls.objects.filter(email__iexact=email)
        if exclude_pk:
            qs = qs.exclude(pk=exclude_pk)
        return qs.exists()

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username

    def delete(self, *args, **kwargs):
        """Soft delete — akkaunt o'chirilganda moliyaviy tarix yo'qolmasligi uchun
        status=False va is_active=False qilinadi (is_active tufayli qayta kirib bo'lmaydi)"""
        self.status = False
        self.is_active = False
        self.save(update_fields=["status", "is_active"])
        return (1, {self._meta.label: 1})


####################################################


class Wallet(models.Model):
    """Hamyon — foydalanuvchining pul saqlash joyi (PIN-kod / parol bilan himoyalangan)"""
    name = models.CharField(max_length=255, help_text="Masalan: Naqd pul, Karta, Bank")
    summa = models.IntegerField(default=0)
    currency = models.CharField(max_length=10, default="UZS")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wallets")
    # 5. Hamyon xavfsizlik paroli / PIN-kod
    pin_code = models.CharField(max_length=128, blank=True, null=True, help_text="Hamyon PIN-kodi / paroli")
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Hamyon"
        verbose_name_plural = "Hamyonlar"

    def __str__(self):
        return f"{self.name} — {self.summa:,} {self.currency}"

    def set_pin(self, raw_pin):
        """Hamyonga xavfsiz shifrlangan PIN-kod o'rnatish"""
        if raw_pin:
            self.pin_code = make_password(str(raw_pin).strip())
        else:
            self.pin_code = None

    def check_pin(self, raw_pin):
        """Hamyon PIN-kodini tekshirish"""
        if not self.pin_code:
            return True  # Parol o'rnatilmagan bo'lsa erkin o'tadi
        if not raw_pin:
            return False
        return check_password(str(raw_pin).strip(), self.pin_code)

    def add_money(self, amount):
        """Hamyonga pul qo'shish (3. pk=None holati hisobga olingan, race-safe)"""
        if amount <= 0:
            raise ValueError("Qo'shiladigan summa musbat bo'lishi kerak")
        if not self.pk:
            self.summa += amount
            self.save()
            return
        Wallet.objects.filter(pk=self.pk).update(summa=F('summa') + amount)
        self.refresh_from_db()

    def withdraw_money(self, amount):
        """Hamyondan pul yechish (3. pk=None holati hisobga olingan, race-safe)"""
        if amount <= 0:
            raise ValueError("Yechiladigan summa musbat bo'lishi kerak")
        if not self.pk:
            if amount > self.summa:
                raise ValueError(f"Hamyonda yetarli mablag' yo'q! Mavjud: {self.summa:,} {self.currency}")
            self.summa -= amount
            self.save()
            return

        updated = Wallet.objects.filter(pk=self.pk, summa__gte=amount).update(
            summa=F('summa') - amount
        )
        if not updated:
            self.refresh_from_db()
            raise ValueError(f"Hamyonda yetarli mablag' yo'q! Mavjud: {self.summa:,} {self.currency}")
        self.refresh_from_db()

    def delete(self, *args, **kwargs):
        """Soft delete — hamyon o'chirilganda bog'langan operatsiyalar yo'qolmasligi uchun status=False qilinadi"""
        self.status = False
        self.save(update_fields=["status"])
        return (1, {self._meta.label: 1})


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
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Harajat turi"
        verbose_name_plural = "Harajat turlari"

    def __str__(self):
        return self.name


####################################################


class Income(models.Model):
    """Daromad — hamyonga pul kiritish"""
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="incomes")
    summa = models.IntegerField()
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
        return f"Daromad: {self.summa:,} — {self.category}"

    def clean(self):
        # 5. Hamyon egasi bilan amaliyot qiluvchi foydalanuvchi tekshiruvi
        if self.wallet_id and self.user_id and self.wallet.user_id != self.user_id:
            raise ValidationError("Ushbu hamyon boshqa foydalanuvchiga tegishli!")

    def save(self, *args, **kwargs):
        self.clean()
        if self.summa <= 0:
            raise ValueError("Daromad summasi musbat bo'lishi kerak")

        with transaction.atomic():
            if self.pk:
                old = Income.objects.filter(pk=self.pk).first()
                if old and old.status:
                    old.wallet.withdraw_money(old.summa)
            if self.status:
                self.wallet.add_money(self.summa)
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """4. Soft delete — Django standartiga muvofiq (count, dict) qaytaradi"""
        with transaction.atomic():
            if self.status:
                self.status = False
                self.wallet.withdraw_money(self.summa)
                super().save(update_fields=["status"])
        return (1, {self._meta.label: 1})


####################################################


class Expense(models.Model):
    """Harajat — nima narsaga (category), qayerda (location), qachon (date) sarflandi"""
    category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True, related_name="expenses")
    summa = models.IntegerField()
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
        cat = self.category.name if self.category else "Harajat"
        return f"{cat}: {self.summa:,}"

    def clean(self):
        # 5. Hamyon egasi bilan amaliyot qiluvchi foydalanuvchi tekshiruvi
        if self.wallet_id and self.user_id and self.wallet.user_id != self.user_id:
            raise ValidationError("Ushbu hamyon boshqa foydalanuvchiga tegishli! Begona hamyondan harajat qilib bo'lmaydi.")
        if self.member_id and self.user_id and self.member.user_id != self.user_id:
            raise ValidationError("Tanlangan a'zo sizga tegishli emas!")

    def save(self, *args, **kwargs):
        self.clean()
        if self.summa <= 0:
            raise ValueError("Harajat summasi musbat bo'lishi kerak")

        with transaction.atomic():
            if self.pk:
                old = Expense.objects.filter(pk=self.pk).first()
                if old and old.status:
                    old.wallet.add_money(old.summa)
            if self.status:
                self.wallet.withdraw_money(self.summa)
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """4. Soft delete — Django standartiga muvofiq (count, dict) qaytaradi"""
        with transaction.atomic():
            if self.status:
                self.status = False
                self.wallet.add_money(self.summa)
                super().save(update_fields=["status"])
        return (1, {self._meta.label: 1})


####################################################


class Transfer(models.Model):
    """2. Hamyonlararo o'tkazma (masalan: Naqd puldan -> Plastik kartaga)"""
    from_wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transfers_sent")
    to_wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transfers_received")
    summa = models.IntegerField()
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
        return f"O'tkazma: {self.from_wallet.name} -> {self.to_wallet.name} ({self.summa:,})"

    def clean(self):
        if self.from_wallet_id == self.to_wallet_id:
            raise ValidationError("Bir xil hamyonlar o'rtasida o'tkazma qilib bo'lmaydi")
        # 5. Foydalanuvchi hamyoni tekshiruvi
        if self.from_wallet_id and self.user_id and self.from_wallet.user_id != self.user_id:
            raise ValidationError("Chiqim hamyoni sizga tegishli emas!")
        if self.to_wallet_id and self.user_id and self.to_wallet.user_id != self.user_id:
            raise ValidationError("Kirim hamyoni sizga tegishli emas!")

    def save(self, *args, **kwargs):
        self.clean()
        if self.summa <= 0:
            raise ValueError("O'tkazma summasi musbat bo'lishi kerak")

        with transaction.atomic():
            if self.pk:
                old = Transfer.objects.filter(pk=self.pk).first()
                if old and old.status:
                    old.from_wallet.add_money(old.summa)
                    old.to_wallet.withdraw_money(old.summa)
            if self.status:
                self.from_wallet.withdraw_money(self.summa)
                self.to_wallet.add_money(self.summa)
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """4. Soft delete — Django standartiga muvofiq (count, dict) qaytaradi"""
        with transaction.atomic():
            if self.status:
                self.status = False
                self.from_wallet.add_money(self.summa)
                self.to_wallet.withdraw_money(self.summa)
                super().save(update_fields=["status"])
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
    summa = models.IntegerField(help_text="Umumiy qarz summasi")
    paid_summa = models.IntegerField(default=0, help_text="Hozirgacha qaytarilgan summa")
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
        action = "Berdim" if self.debt_type == "give" else "Oldim"
        return f"{self.person_name} ({action}: {self.summa:,} UZS)"

    def clean(self):
        if self.wallet and self.user and self.wallet.user_id != self.user_id:
            raise ValidationError("Tanlangan hamyon sizga tegishli emas!")
        if self.paid_summa > self.summa:
            raise ValidationError("Qaytarilgan summa umumiy qarzdan oshib ketishi mumkin emas!")
        if not self.pk and self.wallet and self.debt_type == "give":
            if self.wallet.summa < self.summa:
                raise ValidationError(f"Hamyonda yetarli mablag' yo'q! Mavjud: {self.wallet.summa:,} {self.wallet.currency}")

    def save(self, *args, **kwargs):
        self.clean()
        is_new = self.pk is None
        if self.paid_summa >= self.summa:
            self.is_settled = True

        with transaction.atomic():
            if is_new:
                if self.status and self.wallet:
                    if self.debt_type == "give":
                        self.wallet.withdraw_money(self.summa)
                    elif self.debt_type == "take":
                        self.wallet.add_money(self.summa)
            else:
                old = Debt.objects.filter(pk=self.pk).first()
                # Faqat balansga ta'sir qiluvchi maydonlar o'zgarganda qayta hisoblaymiz
                # (repay() orqali paid_summa o'zgarishi bu yerga tegmasligi kerak)
                if old and old.status and (
                    old.summa != self.summa
                    or old.debt_type != self.debt_type
                    or old.wallet_id != self.wallet_id
                ):
                    if old.wallet:
                        if old.debt_type == "give":
                            old.wallet.add_money(old.summa)
                        elif old.debt_type == "take":
                            old.wallet.withdraw_money(old.summa)
                    if self.status and self.wallet:
                        if self.debt_type == "give":
                            self.wallet.withdraw_money(self.summa)
                        elif self.debt_type == "take":
                            self.wallet.add_money(self.summa)
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """4. Soft delete — qarz bekor qilinganda hamyon balansini atomik tiklaydi"""
        with transaction.atomic():
            if self.status:
                self.status = False
                if self.wallet and self.remaining_summa > 0:
                    if self.debt_type == "give":
                        self.wallet.add_money(self.remaining_summa)
                    elif self.debt_type == "take":
                        self.wallet.withdraw_money(self.remaining_summa)
                super().save(update_fields=["status"])
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
