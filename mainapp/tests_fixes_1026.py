"""2026-10-26 tuzatishlari: 2FA da elektron pochta almashtirishni tasdiqlash, kod urinishlarini parallel so'rovda aylanib o'tib
bo'lmasligi, o'tgan sanali amalga o'sha kun kursi, sessiyani kuniga bir marta yozish va yordamchi tarixi chegarasi.
Tarmoq har doim mock: haqiqiy cbu.uz ga murojaat qilinmaydi."""
import re
import time
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore
from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from . import assistant, currency
from .models import ExchangeRate, Expense, Income, LoginCode, RecurringPayment, User, Wallet
from .recurring import process_due
from .views import _use_login_code

API = "/api/v1"
PASSWORD = "Parol-12345"


class EmailChangeWith2FATests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="ali", password=PASSWORD, email="ali@example.com", first_name="Ali", two_factor_enabled=True,
        )
        self.api = APIClient()
        self.api.force_authenticate(self.user)

    def code(self):
        return re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)

    def request_change(self, email="yangi@example.com", **extra):
        return self.api.patch(
            f"{API}/auth/profile/", {"email": email, "password": PASSWORD, **extra}, format="json",
        )

    def confirm(self, token, code, client=None):
        return (client or self.api).post(
            f"{API}/auth/profile/confirm-email/", {"token": token, "code": code}, format="json",
        )

    def test_change_is_pending_until_new_address_confirms(self):
        res = self.request_change(first_name="Vali")
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertEqual(body["message"], "Yangi elektron pochtaga tasdiqlash kodi yuborildi")
        self.assertEqual(body["user"]["email"], "ali@example.com")
        self.assertEqual(body["email_pending"]["email"], "ya***@example.com")
        # Boshqa maydonlar saqlangan, email esa hali eski
        self.user.refresh_from_db()
        self.assertEqual((self.user.email, self.user.first_name), ("ali@example.com", "Vali"))
        # Kod faqat YANGI manzilga ketgan, yangi email serverda kod bilan saqlangan
        self.assertEqual(mail.outbox[-1].to, ["yangi@example.com"])
        self.assertEqual(LoginCode.objects.get(token=body["email_pending"]["token"]).new_email, "yangi@example.com")

        done = self.confirm(body["email_pending"]["token"], self.code())
        self.assertEqual(done.status_code, 200, done.content)
        self.assertEqual(done.json()["message"], "Elektron pochta yangilandi")
        self.assertEqual(done.json()["user"]["email"], "yangi@example.com")
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "yangi@example.com")

    def test_confirm_uses_stored_email_not_request(self):
        token = self.request_change().json()["email_pending"]["token"]
        res = self.api.post(
            f"{API}/auth/profile/confirm-email/",
            {"token": token, "code": self.code(), "email": "hujum@example.com"}, format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "yangi@example.com")

    def test_wrong_code_keeps_old_email(self):
        token = self.request_change().json()["email_pending"]["token"]
        wrong = "000000" if self.code() != "000000" else "111111"
        res = self.confirm(token, wrong)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Kod noto'g'ri", res.json()["code"])
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "ali@example.com")

    def test_password_still_required_and_nothing_saved_on_failure(self):
        res = self.api.patch(f"{API}/auth/profile/", {"email": "yangi@example.com", "first_name": "Vali"}, format="json")
        self.assertEqual(res.status_code, 400)
        res = self.request_change(password="xato")
        self.assertEqual(res.status_code, 400)
        self.user.refresh_from_db()
        self.assertEqual((self.user.email, self.user.first_name), ("ali@example.com", "Ali"))
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(LoginCode.objects.exists())

    def test_hourly_limit_returns_429_and_saves_nothing(self):
        for i in range(5):
            LoginCode.objects.create(
                user=self.user, token=f"t{i}", code_hash="x", used=True,
                expires_at=timezone.now() + timedelta(minutes=10),
            )
        res = self.request_change(first_name="Vali")
        self.assertEqual(res.status_code, 429)
        self.assertIn("Juda ko'p kod", res.json()["error"])
        self.user.refresh_from_db()
        self.assertEqual((self.user.email, self.user.first_name), ("ali@example.com", "Ali"))

    def test_email_taken_meanwhile_is_rejected_on_confirm(self):
        token = self.request_change().json()["email_pending"]["token"]
        code = self.code()
        User.objects.create_user(username="vali", password=PASSWORD, email="yangi@example.com")
        res = self.confirm(token, code)
        self.assertEqual(res.status_code, 400)
        self.assertIn("email", res.json())
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "ali@example.com")

    def test_email_code_is_not_usable_for_login_or_enable(self):
        token = self.request_change().json()["email_pending"]["token"]
        code = self.code()
        anon = APIClient()
        res = anon.post(f"{API}/auth/login/verify/", {"token": token, "code": code}, format="json")
        self.assertEqual(res.status_code, 400)
        res = self.api.post(f"{API}/auth/two-factor/confirm/", {"token": token, "code": code}, format="json")
        self.assertEqual(res.status_code, 400)
        # Urinish sarflanmagan — kod o'z endpointida hali ishlaydi
        self.assertEqual(self.confirm(token, code).status_code, 200)

    def test_login_and_enable_codes_are_not_usable_for_email_change(self):
        self.api.post(f"{API}/auth/two-factor/", {"enabled": True, "password": PASSWORD}, format="json")
        enable_token = LoginCode.objects.latest("id").token
        res = self.confirm(enable_token, self.code())
        self.assertEqual(res.status_code, 400)
        self.assertIn("code", res.json())

    def test_other_users_code_is_rejected(self):
        token = self.request_change().json()["email_pending"]["token"]
        other = User.objects.create_user(username="vali", password=PASSWORD, email="v@example.com")
        client = APIClient()
        client.force_authenticate(other)
        self.assertEqual(self.confirm(token, self.code(), client).status_code, 400)

    def test_without_2fa_email_changes_immediately(self):
        self.user.two_factor_enabled = False
        self.user.save(update_fields=["two_factor_enabled"])
        res = self.request_change()
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("email_pending", res.json())
        self.assertEqual(res.json()["user"]["email"], "yangi@example.com")
        self.assertEqual(len(mail.outbox), 0)


class LoginCodeAttemptRaceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="ali", password=PASSWORD, email="ali@example.com")
        self.api = APIClient()

    def make_code(self, code="123456", **extra):
        from django.contrib.auth.hashers import make_password
        return LoginCode.objects.create(
            user=self.user, token="tok", code_hash=make_password(code),
            expires_at=timezone.now() + timedelta(minutes=10), **extra,
        )

    def verify(self, code):
        return self.api.post(f"{API}/auth/login/verify/", {"token": "tok", "code": code}, format="json")

    def test_stale_attempts_do_not_allow_extra_guess(self):
        """Bazada 4 ta urinish bor, parallel so'rov esa 0 ni ko'rgan: baribir faqat bitta urinish qoladi"""
        login_code = self.make_code(attempts=LoginCode.MAX_ATTEMPTS - 1)
        calls = []
        real_check = LoginCode.check_code

        def racing_check(obj, code):
            calls.append(code)
            if len(calls) == 1:
                # Birinchi so'rov tekshirish paytida ikkinchi parallel so'rov keladi — urinish allaqachon band
                res, problem = _use_login_code(mock.Mock(), "tok", "123456")
                self.assertIsNone(res)
                self.assertEqual(problem.status_code, 400)
            return real_check(obj, code)

        with mock.patch.object(LoginCode, "check_code", racing_check):
            res = self.verify("000000")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(calls, ["000000"])  # parallel so'rov kodni tekshirishgacha ham yetmadi
        login_code.refresh_from_db()
        self.assertEqual(login_code.attempts, LoginCode.MAX_ATTEMPTS)
        # Endi to'g'ri kod ham o'tmaydi
        self.assertEqual(self.verify("123456").status_code, 400)

    def test_fifth_attempt_with_correct_code_still_works(self):
        self.make_code(attempts=LoginCode.MAX_ATTEMPTS - 1)
        res = self.verify("123456")
        self.assertEqual(res.status_code, 200, res.content)

    def test_wrong_attempts_count_down(self):
        self.make_code()
        first = self.verify("000000")
        self.assertIn("Yana 4 ta", first.json()["code"])
        second = self.verify("000000")
        self.assertIn("Yana 3 ta", second.json()["code"])


def cbu_rates(rate):
    return {"USD": (Decimal(rate), "01.01.2026", None)}


class HistoricalRateTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="ali", password=PASSWORD)
        self.wallet = Wallet.objects.create(user=self.user, name="Dollar", summa=Decimal("1000"), currency="USD")
        self.uzs = Wallet.objects.create(user=self.user, name="Karta", summa=Decimal("1000"), currency="UZS")
        self.fetched = []
        self.past_ok = True

    def fake_fetch(self, day=None):
        self.fetched.append(day)
        if day is None:
            return cbu_rates("12000")
        if not self.past_ok:
            raise OSError("arxiv ishlamayapti")
        return cbu_rates("11000")

    def patched(self):
        return mock.patch("mainapp.currency._fetch_cbu", side_effect=self.fake_fetch)

    def days_ago(self, n):
        return timezone.now() - timedelta(days=n)

    def test_back_dated_income_uses_that_days_rate(self):
        with self.patched():
            past = Income.objects.create(user=self.user, wallet=self.wallet, summa=10, date=self.days_ago(3))
            today = Income.objects.create(user=self.user, wallet=self.wallet, summa=10)
        self.assertEqual(past.uzs_rate, Decimal("11000"))
        self.assertEqual(today.uzs_rate, Decimal("12000"))
        self.assertIn(timezone.localdate() - timedelta(days=3), self.fetched)

    def test_back_dated_expense_uses_that_days_rate(self):
        with self.patched():
            past = Expense.objects.create(user=self.user, wallet=self.wallet, summa=10, date=self.days_ago(1))
        self.assertEqual(past.uzs_rate, Decimal("11000"))

    def test_historical_rate_is_cached(self):
        with self.patched():
            Income.objects.create(user=self.user, wallet=self.wallet, summa=1, date=self.days_ago(2))
            Expense.objects.create(user=self.user, wallet=self.wallet, summa=1, date=self.days_ago(2))
        past_fetches = [d for d in self.fetched if d is not None]
        self.assertEqual(len(past_fetches), 1)

    def test_archive_failure_falls_back_to_current_rate(self):
        self.past_ok = False
        with self.patched(), self.assertLogs("mainapp.currency", "WARNING"):
            income = Income.objects.create(user=self.user, wallet=self.wallet, summa=1, date=self.days_ago(2))
            # Ikkinchi urinish bir necha daqiqa qayta so'ramaydi
            Income.objects.create(user=self.user, wallet=self.wallet, summa=1, date=self.days_ago(5))
        self.assertEqual(income.uzs_rate, Decimal("12000"))
        self.assertEqual(len([d for d in self.fetched if d is not None]), 1)

    def test_total_failure_leaves_null(self):
        with mock.patch("mainapp.currency._fetch_cbu", side_effect=OSError("internet yo'q")), \
                self.assertLogs("mainapp.currency", "WARNING"):
            income = Income.objects.create(user=self.user, wallet=self.wallet, summa=1, date=self.days_ago(2))
        self.assertIsNone(income.uzs_rate)

    def test_uzs_wallet_needs_no_network(self):
        with mock.patch("mainapp.currency._fetch_cbu", side_effect=AssertionError("tarmoq kerak emas")):
            income = Income.objects.create(user=self.user, wallet=self.uzs, summa=1, date=self.days_ago(4))
        self.assertEqual(income.uzs_rate, Decimal(1))

    def test_rate_is_recomputed_when_date_moves_to_another_day(self):
        with self.patched():
            income = Income.objects.create(user=self.user, wallet=self.wallet, summa=1)
            self.assertEqual(income.uzs_rate, Decimal("12000"))
            # Shu kunning ichida vaqtni o'zgartirish kursga tegmaydi
            income.uzs_rate = Decimal("12345")
            income.save(update_fields=["uzs_rate"])
            income.summa = 2
            income.save()
            self.assertEqual(Income.objects.get(pk=income.pk).uzs_rate, Decimal("12345"))
            # Boshqa kunga o'tkazilsa — o'sha kun kursi
            income.date = self.days_ago(5)
            income.save()
            self.assertEqual(Income.objects.get(pk=income.pk).uzs_rate, Decimal("11000"))
            # Bugunga qaytarilsa — joriy kurs
            income.date = timezone.now()
            income.save()
            self.assertEqual(Income.objects.get(pk=income.pk).uzs_rate, Decimal("12000"))

    def test_recurring_catch_up_uses_each_days_rate(self):
        today = timezone.localdate()
        payment = RecurringPayment.objects.create(
            user=self.user, kind="income", name="Maosh", wallet=self.wallet, summa=Decimal("5"), frequency="daily",
            start_date=today - timedelta(days=2), next_date=today - timedelta(days=2),
        )
        with self.patched():
            self.assertEqual(process_due(self.user), 3)
        rates = sorted(Income.objects.filter(user=self.user).values_list("uzs_rate", flat=True))
        self.assertEqual(rates, [Decimal("11000"), Decimal("11000"), Decimal("12000")])
        self.assertTrue(payment.pk)


class SessionRefreshTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="ali", password=PASSWORD)
        self.api = APIClient()
        res = self.api.post(f"{API}/auth/login/", {"username": "ali", "password": PASSWORD}, format="json")
        self.assertEqual(res.status_code, 200)

    def test_session_is_not_saved_on_every_request(self):
        self.assertFalse(settings.SESSION_SAVE_EVERY_REQUEST)
        self.assertEqual(self.api.get(f"{API}/wallets/").status_code, 200)  # birinchi so'rov belgini yozadi
        with mock.patch.object(SessionStore, "save", autospec=True, side_effect=SessionStore.save) as save:
            self.assertEqual(self.api.get(f"{API}/wallets/").status_code, 200)
            self.assertEqual(self.api.get(f"{API}/wallets/").status_code, 200)
            self.assertEqual(save.call_count, 0)

    def test_session_is_refreshed_after_a_day(self):
        self.api.get(f"{API}/wallets/")
        with mock.patch("mainapp.middleware.time.time", return_value=time.time() + 25 * 60 * 60):
            with mock.patch.object(SessionStore, "save", autospec=True, side_effect=SessionStore.save) as save:
                res = self.api.get(f"{API}/wallets/")
                self.assertEqual(res.status_code, 200)
                self.assertEqual(save.call_count, 1)
                # Cookie muddati ham qaytadan uzaytiriladi
                self.assertAlmostEqual(
                    int(res.cookies[settings.SESSION_COOKIE_NAME]["max-age"]), settings.SESSION_COOKIE_AGE, delta=60,
                )
                # Shu kunning ikkinchi so'rovi yana yozmaydi
                self.api.get(f"{API}/wallets/")
                self.assertEqual(save.call_count, 1)


class AssistantHistoryTests(TestCase):
    def test_assistant_turns_are_truncated_not_rejected(self):
        history = [
            {"role": "user", "content": "salom"},
            {"role": "assistant", "content": "x" * 4000},
            {"role": "user", "content": "savol"},
        ]
        cleaned = assistant.clean_history(history)
        self.assertEqual(len(cleaned), 3)
        self.assertEqual(len(cleaned[1]["content"]), assistant.MAX_ASSISTANT_LENGTH)

    def test_long_user_question_still_rejected(self):
        with self.assertRaises(ValueError):
            assistant.clean_history([{"role": "user", "content": "x" * (assistant.MAX_MESSAGE_LENGTH + 1)}])

    def test_total_history_is_capped_by_dropping_oldest(self):
        size = assistant.MAX_ASSISTANT_LENGTH
        history = []
        for i in range(6):
            history.append({"role": "user", "content": f"{i}" + "u" * 900})
            history.append({"role": "assistant", "content": f"{i}" + "a" * (size - 1)})
        history.append({"role": "user", "content": "oxirgi savol"})
        cleaned = assistant.clean_history(history)
        self.assertLessEqual(sum(len(m["content"]) for m in cleaned), assistant.MAX_HISTORY_CHARS)
        self.assertEqual(cleaned[0]["role"], "user")
        self.assertEqual(cleaned[-1], {"role": "user", "content": "oxirgi savol"})
        # Eng eski xabarlar tashlangan, oxirgilari qolgan
        self.assertNotIn("0" + "u" * 900, [m["content"] for m in cleaned])

    def test_dropping_never_leaves_assistant_first(self):
        history = [{"role": "user", "content": "u" * 1000}, {"role": "assistant", "content": "a" * 1500}] * 4
        history.append({"role": "user", "content": "oxirgi"})
        cleaned = assistant.clean_history(history)
        self.assertEqual(cleaned[0]["role"], "user")
        self.assertEqual(cleaned[-1]["role"], "user")

    def test_system_rules_warn_about_client_assistant_turns(self):
        self.assertIn("assistant", assistant.SYSTEM_RULES)
