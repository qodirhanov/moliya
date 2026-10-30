"""plans.md №7, 20, 21, 22, 23, 24 testlari: parol tiklashda hisob borligi bilinmasligi, IP bo'yicha kirish
cheklovi, proksi sarlavhalari, panelga kirish huquqi, xavfsizlik logi va mayda tuzatishlar."""
import logging
import re
import threading
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import Permission
from django.core import mail
from django.core.cache import cache
from django.db import connection
from django.test import RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from . import views
from .backends import LOGIN_IP_MAX_FAILS, login_attempts_left
from .models import PasswordResetCode, User
from .tests import API, PASSWORD, APITestCase, make_user, post_login
from .throttles import client_ip
from .views import RESET_CODE_INVALID_MESSAGE, RESET_REQUEST_MESSAGE

NEW_PASSWORD = "Yangi-parol-777"


def log_text(captured):
    return "\n".join(captured.output)


def admin_request(ip):
    """Django admin kirish sahifasi authenticate() ni shunday so'rov bilan chaqiradi"""
    return RequestFactory().post("/admin/login/", REMOTE_ADDR=ip)


class ResetFlowMixin:
    def request_code(self, username="ali", ip="203.0.113.9"):
        return APIClient().post(f"{API}/auth/password-reset/", {"username": username}, format="json", REMOTE_ADDR=ip)

    def last_code(self):
        return re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)

    def verify(self, username, code):
        return APIClient().post(f"{API}/auth/password-reset/verify/", {"username": username, "code": code},
                                format="json")

    def confirm(self, username, code, password=NEW_PASSWORD):
        return APIClient().post(
            f"{API}/auth/password-reset/confirm/",
            {"username": username, "code": code, "new_password": password}, format="json",
        )

    @staticmethod
    def wrong(code):
        return "000000" if code != "000000" else "111111"


class FakeThread:
    """threading.Thread o'rnida: oqimni ishga tushirmaydi, faqat target'ni eslab qoladi"""
    created = []

    def __init__(self, target=None, name=None, daemon=None):
        self.target, self.name, self.daemon, self.started = target, name, daemon, False
        FakeThread.created.append(self)

    def start(self):
        self.started = True


class ResetEnumerationTests(ResetFlowMixin, APITestCase):
    """№7: parol tiklashda javob hisob borligini oshkor qilmasligi kerak"""

    def setUp(self):
        super().setUp()
        self.ali = make_user("ali", email="ali@example.com")
        make_user("vali", email="vali@example.com")
        make_user("emailsiz")

    def test_request_answer_is_identical_for_any_account(self):
        answers = [self.request_code(name) for name in ("ali", "yoq-akkaunt", "emailsiz", "ali@example.com", "ali")]
        self.assertEqual({r.status_code for r in answers}, {200})
        self.assertEqual([r.json() for r in answers], [{"message": RESET_REQUEST_MESSAGE}] * 5)
        self.assertEqual(len(mail.outbox), 1)  # haqiqatan faqat bitta xat ketdi (qolganlari yo'q/cheklov/kutish)

    def test_blocked_account_gets_the_same_answer(self):
        User.objects.filter(username="vali").update(is_active=False)
        self.assertEqual(self.request_code("vali").json(), self.request_code("yoq-akkaunt").json())
        self.assertEqual(len(mail.outbox), 0)

    def test_verify_answer_is_identical_in_every_failure_case(self):
        self.request_code("ali")
        code = self.last_code()
        wrong = self.wrong(code)
        first_wrong = self.verify("ali", wrong)
        answers = [
            first_wrong,
            self.verify("yoq-akkaunt", wrong),  # akkaunt yo'q
            self.verify("vali", wrong),  # akkaunt bor, faol kod yo'q
        ]
        for _ in range(5):  # urinishlar tugaguncha
            answers.append(self.verify("ali", wrong))
        answers.append(self.verify("ali", code))  # urinishlar tugagach to'g'ri kod ham
        self.assertEqual({r.status_code for r in answers}, {400})
        self.assertEqual({r.json()["code"] for r in answers}, {RESET_CODE_INVALID_MESSAGE})
        self.assertNotIn("urinish qoldi", first_wrong.content.decode())

    def test_confirm_answer_does_not_depend_on_account_either(self):
        self.request_code("ali")
        wrong = self.wrong(self.last_code())
        answers = [self.confirm(name, wrong) for name in ("ali", "yoq-akkaunt", "vali")]
        self.assertEqual({r.status_code for r in answers}, {400})
        self.assertEqual(len({r.content for r in answers}), 1)

    def test_code_hash_is_computed_even_when_account_does_not_exist(self):
        # Sekin xeshlash faqat mavjud akkauntda bajarilsa, javob vaqti akkaunt borligini oshkor qilardi
        with mock.patch("mainapp.views.make_password", wraps=views.make_password) as hashing:
            self.request_code("yoq-akkaunt")
            self.assertEqual(hashing.call_count, 1)
            self.request_code("ali")
            self.assertEqual(hashing.call_count, 2)  # mavjud akkauntda ham bitta (kodni ikki marta xeshlamaydi)

    def test_verify_burns_a_hash_check_when_there_is_nothing_to_compare(self):
        self.request_code("ali")
        code = self.wrong(self.last_code())
        with mock.patch("mainapp.views.check_password", wraps=views.check_password) as dummy:
            self.verify("yoq-akkaunt", code)  # akkaunt yo'q
            self.verify("vali", code)  # faol kod yo'q
            self.assertEqual(dummy.call_count, 2)
            self.verify("ali", code)  # haqiqiy kod bilan solishtirildi (models.check_password) — soxta tekshiruv kerak emas
            self.assertEqual(dummy.call_count, 2)

    def test_daily_code_limit_still_works(self):
        for _ in range(12):
            cache.clear()  # IP bo'yicha emas, akkaunt bo'yicha kunlik chegara tekshiriladi
            self.request_code("ali")
            PasswordResetCode.objects.update(created_at=timezone.now() - timedelta(hours=2))
        self.assertEqual(len(mail.outbox), 10)

    def test_mail_failure_does_not_change_the_answer_and_is_logged(self):
        with mock.patch("mainapp.views.send_mail", side_effect=OSError("smtp")), \
                self.assertLogs("mainapp.views", level="ERROR") as logs:
            broken = self.request_code("ali")
        self.assertEqual((broken.status_code, broken.json()), (200, {"message": RESET_REQUEST_MESSAGE}))
        self.assertIn("user_id", log_text(logs))
        self.assertEqual(PasswordResetCode.objects.count(), 0)  # yuborilmagan kod qolmaydi
        # Xat ketmagan so'rov IP limitidan ham olib tashlanadi: keyingi urinish xatsiz o'tadi
        cache.delete_many([f"reset_req:{self.ali.pk}:203.0.113.9", "reset_req_ip:203.0.113.9"])
        self.assertEqual(self.request_code("ali").status_code, 200)
        self.assertEqual(len(mail.outbox), 1)


class ResetMailInBackgroundTests(ResetFlowMixin, APITestCase):
    """№7: xat so'rov ichida emas, fon oqimida yuboriladi (testlarda MAIL_IN_BACKGROUND=False, bu yerda yoqiladi)"""

    def setUp(self):
        super().setUp()
        make_user("ali", email="ali@example.com")
        FakeThread.created = []

    def test_tests_run_synchronously_by_default(self):
        self.assertFalse(settings.MAIL_IN_BACKGROUND)
        self.request_code()
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(MAIL_IN_BACKGROUND=True)
    def test_request_returns_before_mail_is_sent(self):
        with mock.patch("mainapp.views.threading.Thread", FakeThread), mock.patch("mainapp.views.connections") as conns:
            res = self.request_code()
            self.assertEqual(res.status_code, 200)
            self.assertEqual(len(mail.outbox), 0)  # javob xatdan oldin qaytdi
            (thread,) = FakeThread.created
            self.assertTrue(thread.started)
            self.assertTrue(thread.daemon)
            self.assertEqual(PasswordResetCode.objects.count(), 1)  # kod tranzaksiya yopilgach, oqimdan oldin saqlangan
            thread.target()  # oqim ishga tushganda
            self.assertEqual(len(mail.outbox), 1)
            self.assertEqual(mail.outbox[0].to, ["ali@example.com"])
            conns.close_all.assert_called_once()  # oqim o'z baza ulanishlarini yopadi

    @override_settings(MAIL_IN_BACKGROUND=True)
    def test_unknown_account_starts_no_thread(self):
        with mock.patch("mainapp.views.threading.Thread", FakeThread):
            self.request_code("yoq-akkaunt")
        self.assertEqual(FakeThread.created, [])

    @override_settings(MAIL_IN_BACKGROUND=True)
    def test_real_background_thread_runs_apart_from_the_request_thread(self):
        seen = []
        with mock.patch("mainapp.views.connections") as conns:
            thread = views._run_in_background(lambda: seen.append(threading.current_thread()))
            thread.join(5)
        self.assertEqual(len(seen), 1)
        self.assertIsNot(seen[0], threading.current_thread())
        self.assertTrue(thread.daemon)
        conns.close_all.assert_called_once()

    @override_settings(MAIL_IN_BACKGROUND=True)
    def test_background_error_is_logged_not_raised(self):
        def boom():
            raise OSError("smtp")

        with mock.patch("mainapp.views.connections") as conns, self.assertLogs("mainapp.views", level="ERROR"):
            views._run_in_background(boom).join(5)
        conns.close_all.assert_called_once()


class AdminLoginIpLimitTests(APITestCase):
    """№20: kirish urinishlari IP bo'yicha ham cheklanadi (admin kirish sahifasida DRF "auth" cheklovi yo'q)"""

    def setUp(self):
        super().setUp()
        self.boss = make_user("boss", is_staff=True, is_superuser=True)

    def spray(self, ip, times):
        """Bitta IP'dan har safar boshqa login bilan noto'g'ri urinish (har bir (hisob+IP) juftligi alohida)"""
        for n in range(times):
            self.assertIsNone(authenticate(admin_request(ip), username=f"yoq{n}", password="xato"))

    def test_one_ip_cannot_spray_many_logins(self):
        self.spray("203.0.113.50", LOGIN_IP_MAX_FAILS - 1)
        self.assertEqual(authenticate(admin_request("203.0.113.50"), username="boss", password=PASSWORD), self.boss)
        self.spray("203.0.113.50", 1)  # 30-xato
        self.assertIsNone(authenticate(admin_request("203.0.113.50"), username="boss", password=PASSWORD))
        # Boshqa IP ta'sirlanmaydi
        self.assertEqual(authenticate(admin_request("198.51.100.7"), username="boss", password=PASSWORD), self.boss)

    def test_successful_logins_do_not_count(self):
        # Umumiy IP-chegara faqat NOTO'G'RI urinishlarni sanaydi: ofis/wifi orqasidagi ko'p foydalanuvchi bir-birini to'smaydi
        for n in range(LOGIN_IP_MAX_FAILS + 5):
            user = make_user(f"kassir{n}")
            self.assertEqual(authenticate(admin_request("203.0.113.51"), username=user.username, password=PASSWORD), user)
        self.assertIsNone(cache.get("login_fail_ip:203.0.113.51"))

    def test_attempts_left_shown_to_the_api_includes_the_ip_limit(self):
        self.spray("203.0.113.52", LOGIN_IP_MAX_FAILS - 1)
        self.assertEqual(login_attempts_left("boss", admin_request("203.0.113.52")), 1)

    def test_api_login_is_blocked_by_the_ip_limit_too(self):
        self.spray("203.0.113.53", LOGIN_IP_MAX_FAILS)
        self.assertEqual(post_login(self.api, PASSWORD, username="boss", ip="203.0.113.53").status_code, 429)
        self.assertEqual(post_login(self.api, PASSWORD, username="boss", ip="198.51.100.7").status_code, 200)

    def test_django_admin_login_form_goes_through_the_same_limit(self):
        url = reverse("admin:login")
        for n in range(LOGIN_IP_MAX_FAILS):
            self.client.post(url, {"username": f"yoq{n}", "password": "xato"}, REMOTE_ADDR="203.0.113.54")
        self.client.post(url, {"username": "boss", "password": PASSWORD}, REMOTE_ADDR="203.0.113.54")
        self.assertNotIn("_auth_user_id", self.client.session)  # to'g'ri parol ham bloklangan IP'dan o'tmaydi
        res = self.client.post(url, {"username": "boss", "password": PASSWORD}, REMOTE_ADDR="198.51.100.7")
        self.assertEqual(res.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)


class ProxyHeadersTests(APITestCase):
    """№21: waitress `--trusted-proxy` bilan yuborgan muhit settings va client_ip bilan mos kelishi kerak"""

    def setUp(self):
        super().setUp()
        try:
            import waitress.proxy_headers as proxy_headers
        except ImportError:  # waitress faqat Windows uchun o'rnatiladi (requirements.txt)
            self.skipTest("waitress o'rnatilmagan")
        self.proxy_headers = proxy_headers

    def through_waitress(self, **middleware_kwargs):
        seen = {}

        def app(environ, start_response):
            seen.update(environ)

        wrapped = self.proxy_headers.proxy_headers_middleware(app, **middleware_kwargs)
        # nginx: X-Forwarded-For ga haqiqiy mijoz IP'sini oxiriga qo'shadi; boshidagisi soxta bo'lishi mumkin
        environ = RequestFactory().get(
            "/", REMOTE_ADDR="127.0.0.1", HTTP_X_FORWARDED_FOR="6.6.6.6, 203.0.113.5", HTTP_X_FORWARDED_PROTO="https",
        ).environ
        wrapped(environ, lambda *args: None)
        return seen

    def request_from(self, environ):
        from django.core.handlers.wsgi import WSGIRequest
        return WSGIRequest(environ)

    def test_documented_waitress_flags_keep_the_real_client_ip_and_scheme(self):
        environ = self.through_waitress(
            trusted_proxy="127.0.0.1", trusted_proxy_count=1, clear_untrusted=True,
            trusted_proxy_headers={"x-forwarded-for", "x-forwarded-proto", "x-forwarded-host"},
        )
        request = self.request_from(environ)
        self.assertTrue(request.is_secure())  # SSL yo'naltirish aylanib qolmaydi
        with override_settings(REST_FRAMEWORK={**settings.REST_FRAMEWORK, "NUM_PROXIES": 1}):  # BEHIND_PROXY=True
            self.assertEqual(client_ip(request), "203.0.113.5")  # soxta "6.6.6.6" emas
        # settings.SECURE_PROXY_SSL_HEADER ishlatadigan sarlavha ham saqlanadi
        self.assertEqual(environ["HTTP_X_FORWARDED_PROTO"], "https")

    def test_without_trusted_proxy_waitress_drops_forwarded_headers(self):
        # DEPLOY.md ogohlantirgan holat: sarlavhalar tashlanadi, hamma 127.0.0.1 bo'lib ko'rinadi, sxema http qoladi
        environ = self.through_waitress(trusted_proxy=None, clear_untrusted=True)
        request = self.request_from(environ)
        self.assertFalse(request.is_secure())
        with override_settings(REST_FRAMEWORK={**settings.REST_FRAMEWORK, "NUM_PROXIES": 1}):
            self.assertEqual(client_ip(request), "127.0.0.1")

    def test_deploy_guide_documents_the_flags(self):
        text = (Path(settings.BASE_DIR) / "DEPLOY.md").read_text(encoding="utf-8")
        for needle in ("--trusted-proxy=127.0.0.1", "--trusted-proxy-headers", "--clear-untrusted-proxy-headers",
                       "clearsessions", "schtasks"):
            self.assertIn(needle, text)


class PanelAccessTests(APITestCase):
    """№22: panelga is_staff yetmaydi; ruxsati yo'q har kimga mavjud bo'lmagan manzildagi kabi 404"""

    def setUp(self):
        super().setUp()
        self.panel_url = reverse("panel-accounts")
        self.detail_url = reverse("panel-account", args=[1])
        self.unknown_url = "/bunday-sahifa-yoq-7x2k/"
        self.viewer = make_user("viewer", is_staff=True)
        self.viewer.user_permissions.add(Permission.objects.get(codename="view_user"))
        self.plain_staff = make_user("plain_staff", is_staff=True)
        self.regular = make_user("regular")
        self.regular.user_permissions.add(Permission.objects.get(codename="view_user"))  # is_staff yo'q
        self.root = make_user("root", is_staff=True, is_superuser=True)

    def assert_hidden(self, url):
        res = self.client.get(url)
        unknown = self.client.get(self.unknown_url)
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.content, unknown.content)  # mavjud bo'lmagan manzil bilan bir xil sahifa
        self.assertNotIn("Location", res.headers)

    def test_anonymous_sees_no_difference_from_unknown_url(self):
        self.assert_hidden(self.panel_url)
        self.assert_hidden(self.detail_url)

    def test_staff_without_view_permission_is_hidden(self):
        self.client.force_login(self.plain_staff)
        self.assert_hidden(self.panel_url)
        self.assert_hidden(self.detail_url)

    def test_permission_without_is_staff_is_not_enough(self):
        self.client.force_login(self.regular)
        self.assert_hidden(self.panel_url)

    def test_inactive_staff_session_is_hidden(self):
        self.client.force_login(self.viewer)
        User.objects.filter(pk=self.viewer.pk).update(is_active=False)
        self.assert_hidden(self.panel_url)

    def test_staff_with_view_permission_gets_in(self):
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(self.panel_url).status_code, 200)
        self.assertEqual(self.client.get(reverse("panel-account", args=[self.regular.pk])).status_code, 200)

    def test_superuser_staff_gets_in_without_explicit_permission(self):
        self.client.force_login(self.root)
        self.assertEqual(self.client.get(self.panel_url).status_code, 200)

    def test_non_staff_superuser_flag_alone_is_not_enough(self):
        ghost = make_user("ghost", is_superuser=True)
        self.client.force_login(ghost)
        self.assert_hidden(self.panel_url)

    def test_staff_reaches_panel_after_logging_in_on_the_main_page(self):
        # Kirmagan odamga 404 bo'lgani uchun xodim avval saytda tizimga kiradi, so'ng panel manzilini ochadi
        self.assertEqual(self.client.get(self.panel_url).status_code, 404)
        res = self.client.post(f"{API}/auth/login/", {"username": "viewer", "password": PASSWORD},
                               content_type="application/json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(self.client.get(self.panel_url).status_code, 200)

    def test_staff_reaches_panel_after_logging_in_through_admin(self):
        res = self.client.post(reverse("admin:login"), {"username": "root", "password": PASSWORD})
        self.assertEqual(res.status_code, 302)
        self.assertEqual(self.client.get(self.panel_url).status_code, 200)


class SecurityLogTests(ResetFlowMixin, APITestCase):
    """№23: xavfsizlik hodisalari "security" loggerga yoziladi; parol va tiklash kodi hech qachon"""

    def setUp(self):
        super().setUp()
        self.user = make_user("ali", email="ali@example.com")

    def test_logger_is_configured_with_its_own_handler(self):
        config = settings.LOGGING["loggers"]["security"]
        self.assertEqual((config["level"], config["propagate"]), ("INFO", False))
        self.assertTrue(logging.getLogger("security").handlers)

    def test_failed_login_is_logged_with_user_and_ip_but_not_the_password(self):
        secret = "Maxfiy-Parol-9"
        with self.assertLogs("security", level="WARNING") as logs:
            post_login(self.api, secret, username="ali", ip="203.0.113.77")
            post_login(self.api, secret, username="yoq-akkaunt", ip="203.0.113.77")
        text = log_text(logs)
        self.assertEqual(text.count("login_failed"), 2)
        self.assertIn("username='ali'", text)
        self.assertIn("username='yoq-akkaunt'", text)
        self.assertIn("ip='203.0.113.77'", text)
        self.assertIn(f"user_id='{self.user.pk}'", text)
        self.assertNotIn(secret, text)

    def test_lockout_and_blocked_attempts_are_logged(self):
        with self.assertLogs("security", level="WARNING") as logs:
            for _ in range(5):
                post_login(self.api, "xato", ip="203.0.113.78")
            self.assertEqual(post_login(self.api, PASSWORD, ip="203.0.113.78").status_code, 429)
        text = log_text(logs)
        self.assertEqual(text.count("login_failed"), 5)
        self.assertEqual(text.count("login_lockout"), 1)  # blok aynan 5-urinishda boshlandi
        self.assertEqual(text.count("login_locked"), 1)  # bloklangan paytdagi urinish

    def test_admin_login_failures_are_logged_too(self):
        with self.assertLogs("security", level="WARNING") as logs:
            authenticate(admin_request("203.0.113.79"), username="ali", password="xato")
        self.assertIn("login_failed", log_text(logs))

    def test_log_lines_cannot_be_forged_with_newlines(self):
        with self.assertLogs("security", level="WARNING") as logs:
            post_login(self.api, "xato", username="ali\nWARNING:security:login_ok username='boss'")
        self.assertEqual(len(logs.output), 1)
        self.assertNotIn("\n", logs.output[0])

    def test_password_reset_request_verify_and_confirm_are_logged_without_the_code(self):
        with self.assertLogs("security", level="INFO") as logs:
            self.request_code("ali")
            code = self.last_code()
            wrong = self.wrong(code)
            self.verify("ali", wrong)
            self.assertEqual(self.confirm("ali", code).status_code, 200)
            self.request_code("yoq-akkaunt", ip="203.0.113.10")
        text = log_text(logs)
        for event in ("password_reset_requested", "password_reset_code_failed", "password_reset_confirmed"):
            self.assertIn(event, text)
        self.assertIn("result='sent'", text)
        self.assertIn("result='no_account'", text)
        self.assertIn("reason='wrong_code'", text)
        for secret in (code, wrong, NEW_PASSWORD):
            self.assertNotIn(secret, text)

    def test_password_change_is_logged(self):
        self.login_as(self.user)
        with self.assertLogs("security", level="INFO") as logs:
            res = self.api.post(f"{API}/auth/change-password/",
                                {"old_password": PASSWORD, "new_password": NEW_PASSWORD}, format="json")
        self.assertEqual(res.status_code, 200)
        text = log_text(logs)
        self.assertIn("password_changed", text)
        self.assertIn("username='ali'", text)
        self.assertNotIn(PASSWORD, text)
        self.assertNotIn(NEW_PASSWORD, text)

    def test_account_deletion_is_logged_with_the_original_username(self):
        self.login_as(self.user)
        with self.assertLogs("security", level="INFO") as logs:
            res = self.api.post(f"{API}/auth/delete-account/", {"password": PASSWORD}, format="json")
        self.assertEqual(res.status_code, 200)
        text = log_text(logs)
        self.assertIn("account_deleted", text)
        self.assertIn("username='ali'", text)  # close_account() nomni deleted_N ga almashtirgan bo'lsa ham
        self.assertNotIn(PASSWORD, text)


class InactiveAccountLoginTests(APITestCase):
    """№24 (c): bloklangan hisobga "Hisob bloklangan" xabari (avval bu shox hech qachon ishlamagan)"""

    def setUp(self):
        super().setUp()
        self.user = make_user("ali", email="ali@example.com", is_staff=True)
        User.objects.filter(pk=self.user.pk).update(is_active=False)

    def test_correct_password_tells_the_account_is_blocked(self):
        res = post_login(self.api, PASSWORD)
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.json(), {"error": "Foydalanuvchi hisobi bloklangan"})
        self.assertNotIn("sessionid", res.cookies)  # sessiya ochilmadi

    def test_wrong_password_does_not_reveal_that_the_account_is_blocked(self):
        res = post_login(self.api, "xato")
        self.assertEqual(res.status_code, 401)
        self.assertNotIn("bloklangan", res.json()["error"])

    def test_closed_account_stays_a_plain_login_failure(self):
        # O'zi o'chirgan akkaunt: parol yaroqsiz, nom bo'shagan — oddiy "noto'g'ri" xabari
        other = make_user("vali")
        other.close_account()
        self.assertEqual(post_login(self.api, PASSWORD, username="vali").status_code, 401)
        self.assertEqual(post_login(self.api, PASSWORD, username=other.username).status_code, 401)

    def test_django_admin_still_refuses_the_blocked_account(self):
        res = self.client.post(reverse("admin:login"), {"username": "ali", "password": PASSWORD})
        self.assertEqual(res.status_code, 200)  # forma qayta ko'rsatildi
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_blocked_account_session_does_not_authenticate(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(f"{API}/auth/me/").json(), {"authenticated": False})

    def test_authenticate_returns_the_inactive_user_only_for_the_right_password(self):
        self.assertEqual(authenticate(admin_request("203.0.113.60"), username="ali", password=PASSWORD), self.user)
        self.assertIsNone(authenticate(admin_request("203.0.113.60"), username="ali", password="xato"))


class ProfileSaveTests(APITestCase):
    """№24 (d): profil faqat o'zgargan maydonlarni yozadi"""

    def setUp(self):
        super().setUp()
        self.user = make_user("ali", email="ali@example.com", first_name="Ali")
        self.login_as(self.user)

    def update_sql(self, payload):
        with CaptureQueriesContext(connection) as queries:
            res = self.api.patch(f"{API}/auth/profile/", payload, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        updates = [q["sql"] for q in queries if q["sql"].startswith('UPDATE "mainapp_user"')]
        self.assertEqual(len(updates), 1)
        return updates[0]

    def test_only_changed_fields_are_written(self):
        sql = self.update_sql({"first_name": "Vali", "last_name": "Aliyev"})
        self.assertIn('"first_name"', sql)
        self.assertIn('"last_name"', sql)
        for untouched in ('"password"', '"is_staff"', '"is_active"', '"is_superuser"', '"status"', '"email"'):
            self.assertNotIn(untouched, sql)
        self.user.refresh_from_db()
        self.assertEqual((self.user.first_name, self.user.last_name), ("Vali", "Aliyev"))
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_username_change_is_still_normalized_and_saved(self):
        res = self.api.patch(f"{API}/auth/profile/", {"username": "ＡＬＩ２"}, format="json")  # NFKC: "ALI2"
        self.assertEqual(res.status_code, 200, res.content)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "ALI2")

    def test_empty_patch_writes_nothing(self):
        with CaptureQueriesContext(connection) as queries:
            res = self.api.patch(f"{API}/auth/profile/", {}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertFalse([q for q in queries if q["sql"].startswith('UPDATE "mainapp_user"')])


class ResetCodesInvalidatedTests(ResetFlowMixin, APITestCase):
    """№24 (e): parol almashgach faol tiklash kodlari bekor qilinadi"""

    def setUp(self):
        super().setUp()
        self.user = make_user("ali", email="ali@example.com")

    def test_password_change_invalidates_active_codes(self):
        self.request_code()
        code = self.last_code()
        self.assertEqual(self.verify("ali", code).status_code, 200)
        self.login_as(self.user)
        res = self.api.post(f"{API}/auth/change-password/",
                            {"old_password": PASSWORD, "new_password": NEW_PASSWORD}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(PasswordResetCode.objects.filter(user=self.user, used=False).exists())
        # Emailga kirgan odam eski kod bilan parolni qayta almashtira olmaydi
        self.assertEqual(self.verify("ali", code).status_code, 400)
        self.assertEqual(self.confirm("ali", code, "Boshqa-parol-555").status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))

    def test_failed_password_change_keeps_the_code(self):
        self.request_code()
        self.login_as(self.user)
        res = self.api.post(f"{API}/auth/change-password/",
                            {"old_password": "xato", "new_password": NEW_PASSWORD}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertTrue(PasswordResetCode.objects.filter(user=self.user, used=False).exists())

    def test_reset_confirm_uses_up_every_code(self):
        self.request_code()
        code = self.last_code()
        self.assertEqual(self.confirm("ali", code).status_code, 200)
        self.assertFalse(PasswordResetCode.objects.filter(user=self.user, used=False).exists())
        self.assertEqual(self.confirm("ali", code, "Boshqa-parol-555").status_code, 400)


class EnvExampleTests(unittest.TestCase):
    """№24 (b): .env.example nusxalanib serverga DEBUG=True bilan chiqib ketmasin"""

    def test_debug_is_off_by_default(self):
        lines = (Path(settings.BASE_DIR) / ".env.example").read_text(encoding="utf-8").splitlines()
        active = [line.strip() for line in lines if line.strip().startswith("DEBUG=")]
        self.assertEqual(active, ["DEBUG=False"])


class AdminDeleteUserTests(TestCase):
    """Admin o'chirgan hisob ham foydalanuvchi o'zi o'chirgandagidek tozalanadi"""

    def setUp(self):
        self.admin = User.objects.create_superuser("boss", "boss@example.com", "BossPass123!")
        self.user = User.objects.create_user(
            "Ali", "ali@example.com", "AliPass123!", first_name="Ali", phone="+998901234567",
        )

    def assert_closed(self, user):
        user.refresh_from_db()
        self.assertFalse(user.status)
        self.assertFalse(user.is_active)
        self.assertTrue(user.username.startswith("deleted_"))
        self.assertEqual((user.email, user.first_name, user.phone), ("", "", None))
        self.assertFalse(user.has_usable_password())

    def test_model_delete_clears_personal_data(self):
        self.user.delete()
        self.assert_closed(self.user)

    def test_django_admin_bulk_delete_clears_data_and_frees_username(self):
        self.client.force_login(self.admin)
        url = reverse("admin:mainapp_user_changelist")
        resp = self.client.post(url, {"action": "delete_selected", "_selected_action": [self.user.pk], "post": "yes"})
        self.assertEqual(resp.status_code, 302)
        self.assert_closed(self.user)
        # Nom va email bo'shadi — shu ma'lumotlar bilan qayta ro'yxatdan o'tish mumkin
        new = User.objects.create_user("ali", "ali@example.com", "AliPass123!")
        self.assertNotEqual(new.pk, self.user.pk)


class ResetMailFormatTests(TestCase):
    def test_reset_mail_has_text_and_escaped_html(self):
        views._send_reset_mail(1, "ali@example.com", "<b>Ali</b>", "123456", 0, ())
        msg = mail.outbox[-1]
        self.assertIn("123456", msg.body)
        html, mimetype = msg.alternatives[0]
        self.assertEqual(mimetype, "text/html")
        self.assertIn("123456", html)
        self.assertIn("&lt;b&gt;Ali&lt;/b&gt;", html)
        self.assertNotIn("<b>Ali</b>", html)
