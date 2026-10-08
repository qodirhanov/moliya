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
    login_api,
    logout_api,
    me_api,
    register_api,
    profile_api,
    change_password_api,
    delete_account_api,
    password_reset_request_api,
    password_reset_confirm_api,
    monthly_stats_api,
)

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

urlpatterns = [
    # Auth endpoints
    path("auth/login/", login_api, name="api-login"),
    path("auth/logout/", logout_api, name="api-logout"),
    path("auth/me/", me_api, name="api-me"),
    path("auth/register/", register_api, name="api-register"),
    path("auth/profile/", profile_api, name="api-profile"),
    path("auth/change-password/", change_password_api, name="api-change-password"),
    path("auth/delete-account/", delete_account_api, name="api-delete-account"),
    path("auth/password-reset/", password_reset_request_api, name="api-password-reset"),
    path("auth/password-reset/confirm/", password_reset_confirm_api, name="api-password-reset-confirm"),
    # Statistics
    path("stats/monthly/", monthly_stats_api, name="api-monthly-stats"),
    # Resource endpoints
    path("", include(router.urls)),
]