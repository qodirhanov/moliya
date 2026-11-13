"""Akkaunt butunlay o'chadi (email/login nomi bo'shaydi) va 30 kun kirmagan akkaunt avtomatik o'chadi"""
from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from mainapp.models import (
    Category, Debt, Expense, ExpenseCategory, Income, Member, PasswordResetCode, RecurringPayment, SupportMessage,
    Transfer, User, UserDevice, Wallet,
)

API = "/api/v1"
PASSWORD = "Parol-12345"


def full_account(username, email=None):
    """Hamma bog'langan jadvallarda yozuvi bor akkaunt"""
    user = User.objects.create_user(username, email or f"{username}@example.com", PASSWORD,
                                    first_name="Ali", phone="+998901234567")
    wallet = Wallet.objects.create(user=user, name="Naqd", summa=1000, currency="UZS")
    wallet2 = Wallet.objects.create(user=user, name="Karta", summa=500, currency="UZS")
    income_cat = Category.objects.create(name="Oylik", user=user)
    expense_cat = ExpenseCategory.objects.create(name="Oziq-ovqat", user=user)
    member = Member.objects.create(user=user, name="Oila")
    Income.objects.create(user=user, wallet=wallet, category=income_cat, summa=100)
    Expense.objects.create(user=user, wallet=wallet, category=expense_cat, member=member, summa=50)
    Transfer.objects.create(user=user, from_wallet=wallet, to_wallet=wallet2, summa=10)
    Debt.objects.create(user=user, wallet=wallet, summa=300, person_name="Vali", debt_type="give")
    RecurringPayment.objects.create(user=user, wallet=wallet, summa=5, name="Internet", kind="expense",
                                    start_date=timezone.localdate(), next_date=timezone.localdate())
    SupportMessage.objects.create(user=user, author=user, text="Salom")
    PasswordResetCode.objects.create(user=user, code_hash="x", expires_at=timezone.now() + timedelta(minutes=15))
    UserDevice.objects.create(user=user, session_key=f"s-{username}", created_at=timezone.now(), last_seen=timezone.now())
    return user


def related_rows(user_id):
    """Shu foydalanuvchiga bog'langan qolgan qatorlar soni (barcha FK bo'yicha) — 0 bo'lishi kerak"""
    total = 0
    for rel in User._meta.related_objects:
        if rel.one_to_many and rel.on_delete.__name__ == "CASCADE":
            total += rel.related_model._default_manager.filter(**{rel.field.name: user_id}).count()
    return total


class AccountDeletionTests(TestCase):
    def register(self, username, email):
        return APIClient().post(f"{API}/auth/register/",
                                {"username": username, "password": PASSWORD, "email": email}, format="json")

    def test_cascade_covers_every_relation(self):
        # full_account() hamma jadvalni to'ldirishi shart: yangi bog'liq model qo'shilsa shu test eslatadi
        user = full_account("ali")
        self.assertGreater(related_rows(user.pk), 10)
        user.delete()
        self.assertEqual(related_rows(user.pk), 0)

    def test_self_delete_removes_everything_and_allows_reregistration(self):
        user = full_account("ali", email="ali@example.com")
        pk = user.pk
        api = APIClient()
        api.force_authenticate(user)
        res = api.post(f"{API}/auth/delete-account/", {"password": PASSWORD}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(User.objects.filter(pk=pk).exists())
        for model in (Wallet, Income, Expense, Transfer, Debt, Member, Category, ExpenseCategory, RecurringPayment,
                      SupportMessage, PasswordResetCode, UserDevice):
            self.assertFalse(model.objects.filter(user_id=pk).exists(), model.__name__)

        # Xuddi shu email va ism bilan qayta ro'yxatdan o'tish
        res = self.register("ali", "ali@example.com")
        self.assertEqual(res.status_code, 201, res.content)

    def test_admin_delete_removes_everything_and_allows_reregistration(self):
        admin = User.objects.create_superuser("boss", "boss@example.com", "BossPass123!")
        user = full_account("ali", email="ali@example.com")
        self.client.force_login(admin)
        resp = self.client.post("/admin/mainapp/user/", {"action": "delete_selected", "_selected_action": [user.pk],
                                                         "post": "yes"})
        # ADMIN_URL boshqa bo'lishi mumkin — shu sababli reverse() ishlatamiz
        if resp.status_code == 404:
            from django.urls import reverse
            resp = self.client.post(reverse("admin:mainapp_user_changelist"),
                                    {"action": "delete_selected", "_selected_action": [user.pk], "post": "yes"})
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(User.objects.filter(pk=user.pk).exists())
        self.assertEqual(self.register("Ali", "ALI@example.com").status_code, 201)

    def test_only_the_deleted_user_loses_data(self):
        keep = full_account("vali")
        gone = full_account("ali")
        gone.delete()
        self.assertTrue(User.objects.filter(pk=keep.pk).exists())
        self.assertEqual(Wallet.objects.filter(user=keep).count(), 2)
        self.assertEqual(Debt.objects.filter(user=keep).count(), 1)

    def test_email_is_not_held_by_any_leftover(self):
        # Ildiz sabab: qator qolsa email band bo'lib turardi. Endi o'chirishdan keyin bazada hech qayerda qolmaydi
        user = full_account("ali", email="ali@example.com")
        user.delete()
        self.assertFalse(User.email_taken("ali@example.com"))
        self.assertFalse(User.objects.filter(email__iexact="ali@example.com").exists())
        self.assertFalse(User.objects.filter(username_key="ali").exists())


class DeleteInactiveAccountsTests(TestCase):
    def run_command(self, *args):
        out = StringIO()
        call_command("delete_inactive_accounts", *args, stdout=out, stderr=out)
        return out.getvalue()

    def make(self, username, joined_days_ago=100, login_days_ago=None, **extra):
        user = full_account(username)
        now = timezone.now()
        values = {
            "date_joined": now - timedelta(days=joined_days_ago),
            "last_login": None if login_days_ago is None else now - timedelta(days=login_days_ago),
            **extra,
        }
        User.objects.filter(pk=user.pk).update(**values)
        UserDevice.objects.filter(user=user).delete()  # qurilma faolligi har testda alohida beriladi
        return user

    def exists(self, user):
        return User.objects.filter(pk=user.pk).exists()

    def test_old_inactive_account_is_deleted_with_all_data(self):
        old = self.make("eski", login_days_ago=31)
        out = self.run_command()
        self.assertFalse(self.exists(old))
        self.assertEqual(related_rows(old.pk), 0)
        self.assertIn("Jami o'chirildi: 1", out)
        # Email va nom qayta ishlatiladi
        self.assertFalse(User.email_taken("eski@example.com"))

    def test_never_logged_in_account_uses_join_date(self):
        old = self.make("hechkirmagan", joined_days_ago=45, login_days_ago=None)
        new = self.make("yangi", joined_days_ago=5, login_days_ago=None)
        self.run_command()
        self.assertFalse(self.exists(old))
        self.assertTrue(self.exists(new))

    def test_recent_login_is_kept(self):
        recent = self.make("faol", login_days_ago=29)
        self.run_command()
        self.assertTrue(self.exists(recent))

    def test_account_created_30_days_ago_with_recent_login_is_kept(self):
        user = self.make("chegara", joined_days_ago=200, login_days_ago=1)
        self.run_command()
        self.assertTrue(self.exists(user))

    def test_recent_device_activity_keeps_account_even_with_old_last_login(self):
        # Sessiya uzoq saqlanadi: ilovani har kuni ochadigan odamning last_login yangilanmaydi
        user = self.make("sessiya", login_days_ago=200)
        UserDevice.objects.create(user=user, session_key="s-live", created_at=timezone.now() - timedelta(days=200),
                                  last_seen=timezone.now() - timedelta(days=2))
        self.run_command()
        self.assertTrue(self.exists(user))

    def test_old_device_activity_does_not_protect(self):
        user = self.make("eskiqurilma", login_days_ago=200)
        UserDevice.objects.create(user=user, session_key="s-old", created_at=timezone.now() - timedelta(days=200),
                                  last_seen=timezone.now() - timedelta(days=60))
        self.run_command()
        self.assertFalse(self.exists(user))

    def test_superuser_staff_and_blocked_are_never_deleted(self):
        boss = self.make("boss", login_days_ago=500, is_superuser=True, is_staff=True)
        staff = self.make("xodim", login_days_ago=500, is_staff=True)
        blocked = self.make("bloklangan", login_days_ago=500, is_active=False)
        never = self.make("hechkirmagan_boss", joined_days_ago=900, login_days_ago=None, is_superuser=True)
        self.run_command()
        for user in (boss, staff, blocked, never):
            self.assertTrue(self.exists(user), user.username)

    def test_dry_run_deletes_nothing_but_lists(self):
        old = self.make("eski", login_days_ago=60)
        out = self.run_command("--dry-run")
        self.assertTrue(self.exists(old))
        self.assertEqual(Wallet.objects.filter(user=old).count(), 2)
        self.assertIn("DRY-RUN", out)
        self.assertIn("eski", out)

    def test_days_option(self):
        user = self.make("oraliq", login_days_ago=10)
        self.run_command()
        self.assertTrue(self.exists(user))
        self.run_command("--days", "7")
        self.assertFalse(self.exists(user))

    def test_invalid_days_is_rejected(self):
        with self.assertRaises(CommandError):
            self.run_command("--days", "0")

    def test_max_delete_guard_aborts_without_deleting(self):
        users = [self.make(f"u{i}", login_days_ago=90) for i in range(3)]
        with self.assertRaises(CommandError):
            self.run_command("--max-delete", "2")
        self.assertTrue(all(self.exists(u) for u in users))
        self.run_command("--max-delete", "3")
        self.assertFalse(any(self.exists(u) for u in users))

    def test_deletion_is_logged_and_idempotent(self):
        self.make("eski", login_days_ago=60)
        with self.assertLogs("security", level="INFO") as logs:
            self.run_command()
        self.assertTrue(any("inactive_account_deleted" in line and "eski" in line for line in logs.output))
        self.assertIn("Jami o'chirildi: 0", self.run_command())

    def test_other_users_data_is_untouched(self):
        old = self.make("eski", login_days_ago=60)
        keep = self.make("faol", login_days_ago=1)
        self.run_command()
        self.assertFalse(self.exists(old))
        self.assertEqual(Wallet.objects.filter(user=keep).count(), 2)
        self.assertEqual(Income.objects.filter(user=keep).count(), 1)


class PurgeClosedAccountsMigrationTests(TestCase):
    """0031: eski soft delete qoldirgan `deleted_N` qatorlar (va ularning ma'lumotlari) tozalanadi, boshqalar tegilmaydi"""

    def test_only_old_closed_accounts_are_purged(self):
        import importlib

        from django.apps import apps as django_apps

        old = full_account("eski")
        User.objects.filter(pk=old.pk).update(username=f"deleted_{old.pk}", email="", status=False, is_active=False,
                                              password="!unusable")
        blocked = full_account("bloklangan")
        User.objects.filter(pk=blocked.pk).update(is_active=False)  # admin bloklagan: o'chmaydi
        boss = User.objects.create_superuser("boss", "boss@example.com", "BossPass123!")

        migration = importlib.import_module("mainapp.migrations.0031_purge_closed_accounts")
        migration.purge_closed_accounts(django_apps, None)

        self.assertFalse(User.objects.filter(pk=old.pk).exists())
        self.assertEqual(related_rows(old.pk), 0)
        self.assertTrue(User.objects.filter(pk=blocked.pk).exists())
        self.assertTrue(User.objects.filter(pk=boss.pk).exists())


class SeedDemoTests(TestCase):
    def test_adds_data_once_and_keeps_balances_consistent(self):
        user = User.objects.create_user("demo", password=PASSWORD)
        call_command("seed_demo", "demo", stdout=StringIO())
        self.assertEqual(Wallet.objects.filter(user=user).count(), 4)
        self.assertGreater(Expense.objects.filter(user=user).count(), 10)
        self.assertEqual(Debt.objects.filter(user=user).count(), 2)
        with self.assertRaises(CommandError):
            call_command("seed_demo", "demo", stdout=StringIO())  # ikkinchi marta qo'shilmaydi
        with self.assertRaises(CommandError):
            call_command("seed_demo", "yoq", stdout=StringIO())
