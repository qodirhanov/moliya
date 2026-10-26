from django.urls import path, include
from rest_framework import routers

from .views import (
    UserViewSet,
    CategoryViewSet,
    ExpenseCategoryViewSet,
    WalletViewSet,
    MemberViewSet,
    IncomeViewSet,
    ExpenseViewSet,
    TransferViewSet,
    DebtViewSet,
    RecurringPaymentViewSet,
    SavingsGoalViewSet,
    login_api,
    login_2fa_api,
    two_factor_api,
    two_factor_confirm_api,
    confirm_email_api,
    logout_api,
    logout_all_api,
    devices_api,
    device_terminate_api,
    devices_terminate_others_api,
    me_api,
    register_api,
    profile_api,
    change_password_api,
    delete_account_api,
    password_reset_request_api,
    password_reset_verify_api,
    password_reset_confirm_api,
    monthly_stats_api,
    convert_api,
    rates_api,
)
from .notices import notices_api, notices_read_api
from .support import assistant_api, support_messages_api, support_unread_api

router = routers.DefaultRouter()
router.register(r"users", UserViewSet)
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"expense-categories", ExpenseCategoryViewSet, basename="expense-category")
router.register(r"wallets", WalletViewSet)
router.register(r"members", MemberViewSet, basename="member")
router.register(r"incomes", IncomeViewSet)
router.register(r"expenses", ExpenseViewSet)
router.register(r"transfers", TransferViewSet)
router.register(r"debts", DebtViewSet)
router.register(r"recurring", RecurringPaymentViewSet, basename="recurring")
router.register(r"goals", SavingsGoalViewSet, basename="goal")

urlpatterns = [
    # Auth endpoints
    path("auth/login/", login_api, name="api-login"),
    path("auth/login/verify/", login_2fa_api, name="api-login-2fa"),
    path("auth/profile/confirm-email/", confirm_email_api, name="api-profile-confirm-email"),
    path("auth/two-factor/", two_factor_api, name="api-two-factor"),
    path("auth/two-factor/confirm/", two_factor_confirm_api, name="api-two-factor-confirm"),
    path("auth/logout/", logout_api, name="api-logout"),
    path("auth/logout-all/", logout_all_api, name="api-logout-all"),
    path("auth/devices/", devices_api, name="api-devices"),
    path("auth/devices/terminate-others/", devices_terminate_others_api, name="api-devices-terminate-others"),
    path("auth/devices/<int:pk>/terminate/", device_terminate_api, name="api-device-terminate"),
    path("auth/me/", me_api, name="api-me"),
    path("auth/register/", register_api, name="api-register"),
    path("auth/profile/", profile_api, name="api-profile"),
    path("auth/change-password/", change_password_api, name="api-change-password"),
    path("auth/delete-account/", delete_account_api, name="api-delete-account"),
    path("auth/password-reset/", password_reset_request_api, name="api-password-reset"),
    path("auth/password-reset/verify/", password_reset_verify_api, name="api-password-reset-verify"),
    path("auth/password-reset/confirm/", password_reset_confirm_api, name="api-password-reset-confirm"),
    # Statistics
    path("stats/monthly/", monthly_stats_api, name="api-monthly-stats"),
    # Valyuta kursi (Markaziy bank)
    path("rates/", rates_api, name="api-rates"),
    path("rates/convert/", convert_api, name="api-rates-convert"),
    # Sozlamalar → Yordam (admin bilan chat) va AI yordamchi
    path("support/messages/", support_messages_api, name="api-support-messages"),
    path("support/unread/", support_unread_api, name="api-support-unread"),
    path("assistant/", assistant_api, name="api-assistant"),
    # Admin yuborgan xabarlar (navbar qo'ng'irog'i)
    path("notices/", notices_api, name="api-notices"),
    path("notices/read/", notices_read_api, name="api-notices-read"),
    # Resource endpoints
    path("", include(router.urls)),
]