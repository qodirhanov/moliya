import time
from unittest import mock

from django.conf import settings
from rest_framework.test import APIClient

from .tests import API, PASSWORD, APITestCase, make_user

YEAR = 365 * 24 * 60 * 60


class PersistentSessionTests(APITestCase):
    """Foydalanuvchi brauzer/ilovani yopib qayta ochganda ham tizimda qoladi; parol faqat Chiqishdan keyin so'raladi"""

    def setUp(self):
        super().setUp()
        self.user = make_user("ali")

    def login(self, client=None, username="ali", password=PASSWORD):
        return (client or self.api).post(
            f"{API}/auth/login/", {"username": username, "password": password}, format="json"
        )

    def test_login_cookie_is_persistent_for_about_a_year(self):
        res = self.login()
        self.assertEqual(res.status_code, 200)
        cookie = res.cookies[settings.SESSION_COOKIE_NAME]
        # Max-Age/expires bor — bu brauzer yopilganda o'chadigan "session cookie" emas
        self.assertTrue(cookie["max-age"])
        self.assertTrue(cookie["expires"])
        self.assertAlmostEqual(int(cookie["max-age"]), YEAR, delta=60)

    def test_register_cookie_is_persistent_too(self):
        res = self.api.post(
            f"{API}/auth/register/", {"username": "vali", "password": PASSWORD, "confirm_password": PASSWORD},
            format="json",
        )
        self.assertIn(res.status_code, (200, 201), res.content)
        cookie = res.cookies[settings.SESSION_COOKIE_NAME]
        self.assertAlmostEqual(int(cookie["max-age"]), YEAR, delta=60)

    def test_session_older_than_24_hours_still_works(self):
        self.login()
        with mock.patch("mainapp.middleware.time.time", return_value=time.time() + 25 * 60 * 60):
            self.assertEqual(self.api.get(f"{API}/wallets/").status_code, 200)
            self.assertTrue(self.api.get(f"{API}/auth/me/").json()["authenticated"])

    def test_logout_invalidates_the_old_session_cookie(self):
        self.login()
        old_key = self.api.cookies[settings.SESSION_COOKIE_NAME].value
        self.assertEqual(self.api.post(f"{API}/auth/logout/").status_code, 200)
        # Eski cookie'ni boshqa mijoz (masalan, nusxalangan) qayta yuborsa ham kirish yo'q
        replay = APIClient()
        replay.cookies[settings.SESSION_COOKIE_NAME] = old_key
        self.assertEqual(replay.get(f"{API}/wallets/").status_code, 401)
        self.assertFalse(replay.get(f"{API}/auth/me/").json()["authenticated"])

    def test_password_change_logs_out_other_clients_but_not_the_current_one(self):
        other = APIClient()
        self.assertEqual(self.login(other).status_code, 200)
        self.assertEqual(self.login().status_code, 200)

        res = self.api.post(
            f"{API}/auth/change-password/",
            {"old_password": PASSWORD, "new_password": "Yangi-Parol-98765"},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(self.api.get(f"{API}/wallets/").status_code, 200)  # joriy qurilma qoladi
        self.assertEqual(other.get(f"{API}/wallets/").status_code, 401)  # boshqa qurilma chiqib ketadi

    def test_password_reset_ends_all_sessions(self):
        self.login()
        self.user.set_password("Yangi-Parol-98765")  # tiklash tasdiqlashi ham shuni qiladi
        self.user.save(update_fields=["password"])
        self.assertEqual(self.api.get(f"{API}/wallets/").status_code, 401)

    def test_blocked_user_existing_session_gets_401(self):
        self.login()
        self.assertEqual(self.api.get(f"{API}/wallets/").status_code, 200)
        self.user.is_active = False  # admin bloklaydi
        self.user.save(update_fields=["is_active"])
        self.assertEqual(self.api.get(f"{API}/wallets/").status_code, 401)
