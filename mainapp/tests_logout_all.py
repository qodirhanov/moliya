from django.contrib.auth.models import AbstractBaseUser
from rest_framework.test import APIClient

from .models import User
from .tests import API, PASSWORD, APITestCase, make_user


class LogoutAllTests(APITestCase):
    """"Barcha qurilmalardan chiqish": session_epoch oshadi va shu foydalanuvchining barcha sessiyalari yopiladi"""

    def setUp(self):
        super().setUp()
        self.user = make_user("ali")
        self.other = make_user("vali")

    def login(self, username="ali", password=PASSWORD, client=None):
        client = client or APIClient()
        res = client.post(f"{API}/auth/login/", {"username": username, "password": password}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        return client

    def signed_in(self, client):
        return client.get(f"{API}/auth/me/").json()["authenticated"]

    def test_logout_all_closes_every_device_including_current(self):
        phone, laptop = self.login(), self.login()
        self.assertTrue(self.signed_in(phone) and self.signed_in(laptop))
        res = phone.post(f"{API}/auth/logout-all/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("message", res.json())
        self.assertFalse(self.signed_in(phone))
        self.assertFalse(self.signed_in(laptop))
        # Himoyalangan manzil ham 401 beradi
        self.assertEqual(laptop.get(f"{API}/wallets/").status_code, 401)
        self.user.refresh_from_db()
        self.assertEqual(self.user.session_epoch, 1)

    def test_other_users_are_unaffected(self):
        mine, theirs = self.login(), self.login("vali")
        mine.post(f"{API}/auth/logout-all/")
        self.assertTrue(self.signed_in(theirs))
        self.other.refresh_from_db()
        self.assertEqual(self.other.session_epoch, 0)

    def test_user_can_log_in_again_after_logout_all(self):
        old = self.login()
        old.post(f"{API}/auth/logout-all/")
        new = self.login()
        self.assertTrue(self.signed_in(new))
        self.assertFalse(self.signed_in(old))
        # Ikkinchi marta bosish ham ishlaydi va hisoblagich yana oshadi
        self.assertEqual(new.post(f"{API}/auth/logout-all/").status_code, 200)
        self.assertFalse(self.signed_in(new))
        self.user.refresh_from_db()
        self.assertEqual(self.user.session_epoch, 2)

    def test_epoch_zero_hash_is_djangos_default(self):
        # Migratsiyadan keyin mavjud sessiyalar yaroqsiz bo'lib qolmasligi kerak
        self.assertEqual(self.user.session_epoch, 0)
        self.assertEqual(self.user.get_session_auth_hash(), AbstractBaseUser._get_session_auth_hash(self.user))
        self.user.session_epoch = 1
        self.assertNotEqual(self.user.get_session_auth_hash(), AbstractBaseUser._get_session_auth_hash(self.user))
        # Zaxira kalitlar ham hisoblagichni hisobga oladi
        with self.settings(SECRET_KEY_FALLBACKS=["eski-kalit"]):
            self.assertNotEqual(list(self.user.get_session_auth_fallback_hash())[0], self.user.get_session_auth_hash())

    def test_session_survives_when_epoch_is_zero(self):
        client = self.login()
        self.assertTrue(self.signed_in(client))
        self.assertTrue(self.signed_in(client))

    def test_password_change_after_logout_all_keeps_current_and_kills_others(self):
        self.user.session_epoch = 1
        self.user.save(update_fields=["session_epoch"])
        current, elsewhere = self.login(), self.login()
        res = current.post(
            f"{API}/auth/change-password/",
            {"old_password": PASSWORD, "new_password": "Yangi-Parol-777"}, format="json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        self.assertTrue(self.signed_in(current))
        self.assertFalse(self.signed_in(elsewhere))

    def test_anonymous_gets_401(self):
        res = APIClient().post(f"{API}/auth/logout-all/")
        self.assertEqual(res.status_code, 401)

    def test_csrf_is_enforced(self):
        client = APIClient(enforce_csrf_checks=True)
        client.get("/")  # sahifa csrftoken cookie'sini beradi
        token = client.cookies["csrftoken"].value
        res = client.post(f"{API}/auth/login/", {"username": "ali", "password": PASSWORD}, format="json",
                          HTTP_X_CSRFTOKEN=token)
        self.assertEqual(res.status_code, 200)
        token = client.cookies["csrftoken"].value
        # Tokensiz so'rov rad etiladi va sessiya o'zgarmaydi
        self.assertEqual(client.post(f"{API}/auth/logout-all/").status_code, 403)
        self.assertTrue(self.signed_in(client))
        self.assertEqual(client.post(f"{API}/auth/logout-all/", HTTP_X_CSRFTOKEN=token).status_code, 200)
        self.assertFalse(self.signed_in(client))

    def test_security_event_is_logged(self):
        client = self.login()
        with self.assertLogs("security", level="INFO") as logs:
            client.post(f"{API}/auth/logout-all/")
        self.assertTrue(any(line.startswith("INFO:security:logout_all ") and "username='ali'" in line
                            for line in logs.output), logs.output)
