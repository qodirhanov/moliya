"""Yuqori darajadagi ikki xato testlari: admin kirishida 2FA aylanib o'tilmasligi va huquqsiz xodim
/users/ orqali boshqa akkauntni egallab ololmasligi."""
from django.conf import settings
from django.contrib.auth.models import Permission
from django.test import TestCase
from rest_framework.test import APIClient

from .tests import API, PASSWORD, make_user

ADMIN_LOGIN = f"/{settings.ADMIN_URL}login/"


def grant(user, *codenames):
    user.user_permissions.add(*Permission.objects.filter(content_type__app_label="mainapp", codename__in=codenames))


def rows(response):
    data = response.json()
    return data["results"] if isinstance(data, dict) and "results" in data else data


class AdminTwoFactorTests(TestCase):
    def post_admin_login(self, username):
        return self.client.post(ADMIN_LOGIN, {"username": username, "password": PASSWORD, "next": f"/{settings.ADMIN_URL}"})

    def test_superuser_with_2fa_cannot_login_to_admin(self):
        make_user("root", is_staff=True, is_superuser=True, two_factor_enabled=True)
        res = self.post_admin_login("root")
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_superuser_without_2fa_can_login_to_admin(self):
        make_user("root", is_staff=True, is_superuser=True)
        res = self.post_admin_login("root")
        self.assertEqual(res.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_session_from_main_site_opens_admin(self):
        root = make_user("root", is_staff=True, is_superuser=True, two_factor_enabled=True)
        self.client.force_login(root)
        self.assertEqual(self.client.get(f"/{settings.ADMIN_URL}").status_code, 200)


class UserViewSetPermissionTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.root = make_user("root", is_staff=True, is_superuser=True, email="root@example.com")
        self.staff = make_user("boss", is_staff=True, email="boss@example.com")
        self.other_staff = make_user("boss2", is_staff=True, email="boss2@example.com")
        self.ali = make_user("ali", email="ali@example.com")

    def url(self, user):
        return f"{API}/users/{user.id}/"

    def test_staff_without_perms_sees_only_self(self):
        self.api.force_authenticate(self.staff)
        ids = [u["id"] for u in rows(self.api.get(f"{API}/users/"))]
        self.assertEqual(ids, [self.staff.id])
        self.assertEqual(self.api.get(self.url(self.ali)).status_code, 404)

    def test_staff_without_perms_cannot_patch_or_delete_others(self):
        self.api.force_authenticate(self.staff)
        res = self.api.patch(self.url(self.ali), {"email": "hacker@example.com"}, format="json")
        self.assertIn(res.status_code, (403, 404))
        self.assertIn(self.api.delete(self.url(self.ali)).status_code, (403, 404))
        self.ali.refresh_from_db()
        self.assertEqual(self.ali.email, "ali@example.com")
        self.assertTrue(self.ali.status)

    def test_staff_without_perms_can_still_patch_self(self):
        self.api.force_authenticate(self.staff)
        res = self.api.patch(self.url(self.staff), {"first_name": "Boss"}, format="json")
        self.assertEqual(res.status_code, 200)

    def test_view_only_staff_cannot_change_or_delete(self):
        grant(self.staff, "view_user")
        self.api.force_authenticate(self.staff)
        self.assertIn(self.ali.id, [u["id"] for u in rows(self.api.get(f"{API}/users/"))])
        self.assertEqual(self.api.patch(self.url(self.ali), {"first_name": "X"}, format="json").status_code, 403)
        self.assertEqual(self.api.delete(self.url(self.ali)).status_code, 403)

    def test_staff_with_perms_manages_ordinary_but_not_staff(self):
        grant(self.staff, "view_user", "change_user", "delete_user")
        self.api.force_authenticate(self.staff)
        self.assertEqual(self.api.patch(self.url(self.ali), {"first_name": "Ali"}, format="json").status_code, 200)
        res = self.api.patch(self.url(self.other_staff), {"email": "x@example.com"}, format="json")
        self.assertEqual(res.status_code, 403)
        self.assertEqual(self.api.delete(self.url(self.other_staff)).status_code, 403)
        self.other_staff.refresh_from_db()
        self.assertEqual(self.other_staff.email, "boss2@example.com")
        self.assertTrue(self.other_staff.status)
        # superuser baribir ko'rinmaydi
        self.assertEqual(self.api.get(self.url(self.root)).status_code, 404)
        self.assertEqual(self.api.delete(self.url(self.ali)).status_code, 200)

    def test_superuser_can_do_everything(self):
        self.api.force_authenticate(self.root)
        for user in (self.other_staff, self.ali):
            res = self.api.patch(self.url(user), {"first_name": "Yangi"}, format="json")
            self.assertEqual(res.status_code, 200, user.username)
        self.assertEqual(self.api.delete(self.url(self.other_staff)).status_code, 200)
        self.assertEqual(self.api.delete(self.url(self.ali)).status_code, 200)
