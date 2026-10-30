from django.contrib import admin
from django.contrib.admin.forms import AdminAuthenticationForm, AdminPasswordChangeForm
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.core.exceptions import ValidationError
from .backends import CURRENT_PASSWORD_LOCKED_MESSAGE, verify_current_password
from .models import User, Category, ExpenseCategory, Wallet, Member, Income, Expense, Transfer, Debt, SupportMessage


class TwoFactorAdminAuthenticationForm(AdminAuthenticationForm):
    """2FA kodi faqat asosiy sahifadagi kirishda so'raladi (login_api). Admin kirish sahifasi esa faqat parol
    tekshirgani uchun, 2FA yoqilgan akkaunt shu yerdan kodsiz kirib ketardi. Shuning uchun bunday akkauntlarni
    bu yerda rad etamiz: avval asosiy sahifadan kirib (kod bilan), keyin adminni ochadi"""
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if getattr(user, "two_factor_enabled", False):
            raise ValidationError(
                "Sizda ikki bosqichli tasdiqlash yoqilgan. Avval asosiy sahifadan kod bilan kiring, "
                "so'ng admin sahifasini oching.",
                code="two_factor_required",
            )


class LimitedAdminPasswordChangeForm(AdminPasswordChangeForm):
    """Joriy parolni taxmin qilish limiti (15 daqiqada 5 ta) Sozlamalardagi bilan umumiy: ochiq qolgan admin sessiyasi
    orqali parolni shu formadan cheksiz sinab ko'rib bo'lmaydi"""
    def clean_old_password(self):
        result = verify_current_password(self.user, self.cleaned_data["old_password"])
        if result == "locked":
            raise ValidationError(CURRENT_PASSWORD_LOCKED_MESSAGE, code="password_locked")
        if result == "wrong":
            raise ValidationError(self.error_messages["password_incorrect"], code="password_incorrect")
        return self.cleaned_data["old_password"]


admin.site.login_form = TwoFactorAdminAuthenticationForm
admin.site.password_change_form = LimitedAdminPasswordChangeForm


class SoftDeleteAdminMixin:
    """"Delete selected" ommaviy amali queryset.delete() ishlatadi, bu esa modeldagi
    custom delete() (soft delete + hamyon qoldig'ini qaytarish) ni chetlab o'tadi.
    Shu sabab har bir obyektni alohida .delete() qilib chiqamiz."""
    def delete_queryset(self, request, queryset):
        for obj in queryset:
            obj.delete()


@admin.register(User)
class UserAdmin(SoftDeleteAdminMixin, BaseUserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "phone", "status", "is_staff")
    list_filter = ("status", "is_staff", "is_superuser", "is_active")
    search_fields = ("username", "first_name", "last_name", "email", "phone")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Qo'shimcha ma'lumotlar", {"fields": ("phone", "status")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Qo'shimcha ma'lumotlar", {"fields": ("phone", "status")}),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "icon", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("name", "description")


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "icon", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("name", "description")


@admin.register(Wallet)
class WalletAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("name", "user", "summa", "currency", "status", "updated_at")
    list_filter = ("status", "currency", "created_at")
    search_fields = ("name", "user__username")


@admin.register(Member)
class MemberAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("name", "kind", "user", "status", "created_at")
    list_filter = ("kind", "status", "created_at")
    search_fields = ("name", "user__username")


@admin.register(Income)
class IncomeAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("user", "wallet", "category", "summa", "date", "status")
    list_filter = ("status", "category", "date")
    search_fields = ("description", "user__username", "wallet__name")
    date_hierarchy = "date"


@admin.register(Expense)
class ExpenseAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("category", "summa", "wallet", "member", "user", "location", "date", "status")
    list_filter = ("status", "category", "date")
    search_fields = ("description", "location", "category__name", "user__username", "wallet__name", "member__name")
    date_hierarchy = "date"


@admin.register(Transfer)
class TransferAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("user", "from_wallet", "to_wallet", "summa", "date", "status")
    list_filter = ("status", "date")
    search_fields = ("description", "from_wallet__name", "to_wallet__name", "user__username")
    date_hierarchy = "date"


@admin.register(Debt)
class DebtAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("person_name", "debt_type", "user", "summa", "paid_summa", "is_settled", "due_date", "status")
    list_filter = ("debt_type", "is_settled", "status", "due_date")
    search_fields = ("person_name", "description", "user__username")

@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    """Javob yozish admin panelida (panel/support/) — bu yerda faqat ko'rish va qidirish"""
    list_display = ("user", "from_admin", "short_text", "is_read", "created_at")
    list_filter = ("from_admin", "is_read")
    search_fields = ("user__username", "text")
    raw_id_fields = ("user", "author")

    @admin.display(description="Xabar")
    def short_text(self, obj):
        return obj.text[:80]
