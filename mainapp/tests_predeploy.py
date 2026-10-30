"""Serverga chiqishdan oldingi tuzatishlar: valyuta o'zgarishi, doimiy to'lovning ikki marta yozilishi,
ovozdagi "3 marta" va summadan keyingi son"""
import http.client
from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

from django.contrib import admin
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from . import stt, tts, voice_parse as vp
from .admin import LimitedAdminPasswordChangeForm
from .backends import LOGIN_MAX_FAILS
from .models import Expense, ExpenseCategory, PasswordResetCode, RecurringPayment, SavingsGoal, User, Wallet
from .recurring import process_due
from .tests_voice import API as VOICE_API

API = "/api/v1"


class BaseCase(TestCase):
    def setUp(self):
        cache.clear()
        offline = mock.patch("mainapp.currency._fetch_cbu", side_effect=OSError("testlarda internet ishlatilmaydi"))
        offline.start()
        self.addCleanup(offline.stop)
        self.user = User.objects.create_user(username="ali", password="Parol-12345")
        self.api = APIClient()
        self.api.force_authenticate(self.user)
        self.wallet = Wallet.objects.create(user=self.user, name="Karta", summa=Decimal("1000000"))
        self.category = ExpenseCategory.objects.create(name="Kutilmagan xarajatlar")

    def recurring(self, **extra):
        payload = {"kind": "expense", "name": "Ijara", "wallet": self.wallet.id, "summa": "100",
                   "expense_category": self.category.id, "frequency": "monthly",
                   "start_date": timezone.localdate().isoformat(), **extra}
        res = self.api.post(f"{API}/recurring/", payload, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        return RecurringPayment.objects.get(pk=res.json()["id"])


class WalletCurrencyLockTests(BaseCase):
    def change_currency(self):
        return self.api.patch(f"{API}/wallets/{self.wallet.id}/", {"currency": "USD"}, format="json")

    def test_locked_by_recurring_payment(self):
        self.recurring(start_date=(timezone.localdate() + timedelta(days=5)).isoformat())
        self.assertEqual(self.change_currency().status_code, 400)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.currency, "UZS")

    def test_locked_by_savings_goal(self):
        SavingsGoal.objects.create(user=self.user, name="Mashina", target=Decimal("5000"), wallet=self.wallet)
        self.assertEqual(self.change_currency().status_code, 400)

    def test_free_after_recurring_payment_is_deleted(self):
        payment = self.recurring(start_date=(timezone.localdate() + timedelta(days=5)).isoformat())
        RecurringPayment.objects.filter(pk=payment.pk).update(status=False)
        self.assertEqual(self.change_currency().status_code, 200)


class RecurringScheduleChangeTests(BaseCase):
    def count(self):
        return Expense.objects.filter(status=True).count()

    def test_changing_frequency_does_not_write_todays_payment_twice(self):
        payment = self.recurring()
        self.assertEqual(process_due(self.user), 1)

        res = self.api.patch(f"{API}/recurring/{payment.id}/", {"frequency": "weekly"}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        payment.refresh_from_db()
        self.assertEqual(payment.next_date, timezone.localdate() + timedelta(days=7))
        self.assertEqual(process_due(self.user), 0)
        self.assertEqual(self.count(), 1)

    def test_unpaid_due_today_stays_today(self):
        # Pul yetmagani uchun bugungi to'lov yozilmagan: jadval o'zgarsa ham bugun qoladi
        payment = self.recurring(summa="5000000")
        self.assertEqual(process_due(self.user), 0)
        self.api.patch(f"{API}/recurring/{payment.id}/", {"frequency": "weekly"}, format="json")
        payment.refresh_from_db()
        self.assertEqual(payment.next_date, timezone.localdate())


class VoiceParseTests(TestCase):
    today = date(2026, 10, 30)

    def amount(self, text):
        return vp.best_amount(vp.find_amounts(vp.loose(text).split()))["value"]

    def day(self, text):
        return vp.find_date(vp.loose(text), self.today)[0]

    def test_marta_is_not_march(self):
        self.assertIsNone(self.day("taksiga 3 marta 15 ming sarfladim"))
        self.assertEqual(self.amount("taksiga 3 marta 15 ming sarfladim"), 15000)

    def test_real_month_forms_still_work(self):
        self.assertEqual(self.day("3 mart"), date(2026, 3, 3))
        self.assertEqual(self.day("3 martda"), date(2026, 3, 3))
        self.assertEqual(self.day("5 oktabrdagi"), date(2026, 10, 5))
        self.assertEqual(self.day("12 sentyabrda"), date(2026, 9, 12))
        self.assertEqual(self.day("1 mayda"), date(2026, 5, 1))

    def test_number_after_amount_is_not_added(self):
        self.assertEqual(self.amount("taksiga 20 ming 2 kishiga"), 20000)
        self.assertEqual(self.amount("45 ming 2 ta non"), 45000)
        self.assertEqual(self.amount("20 ming 2"), 20000)

    def test_compound_amounts_still_work(self):
        self.assertEqual(self.amount("45 ming 500"), 45500)
        self.assertEqual(self.amount("2 million 500 ming"), 2500000)
        self.assertEqual(self.amount("2 million 5 ming"), 2005000)
        self.assertEqual(self.amount("yigirma ming besh yuz"), 20500)
        self.assertEqual(self.amount("bir million ikki yuz ming"), 1200000)

    def test_days_ago(self):
        self.assertEqual(self.day("3 kun oldin"), date(2026, 10, 27))
        self.assertEqual(self.day("ikki hafta avval"), date(2026, 10, 16))
        self.assertIsNone(self.day("3 kun"))


class JsonObjectOnlyTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_array_body_gives_400_not_500(self):
        api = APIClient(raise_request_exception=False)
        for path in ("/auth/login/", "/auth/register/", "/auth/password-reset/", "/auth/login-2fa/"):
            res = api.post(f"{API}{path}", [1, 2], format="json")
            self.assertIn(res.status_code, (400, 404), path)

    def test_authenticated_endpoints(self):
        api = APIClient(raise_request_exception=False)
        api.force_authenticate(User.objects.create_user(username="ali", password="Parol-12345"))
        self.assertEqual(api.patch(f"{API}/auth/profile/", [1], format="json").status_code, 400)
        self.assertEqual(api.post(f"{API}/wallets/", "text", format="json").status_code, 400)

    def test_object_body_still_works(self):
        res = APIClient().post(f"{API}/auth/login/", {"username": "yoq", "password": "x"}, format="json")
        self.assertNotEqual(res.status_code, 500)


class EmailChangeResetCodeTests(BaseCase):
    def code(self):
        return PasswordResetCode.objects.create(user=self.user, code_hash="x",
                                                expires_at=timezone.now() + timedelta(minutes=15))

    def test_email_change_cancels_reset_codes(self):
        code = self.code()
        res = self.api.patch(f"{API}/auth/profile/", {"email": "yangi@example.com", "password": "Parol-12345"}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        code.refresh_from_db()
        self.assertTrue(code.used)

    def test_name_change_keeps_reset_codes(self):
        code = self.code()
        self.api.patch(f"{API}/auth/profile/", {"first_name": "Ali"}, format="json")
        code.refresh_from_db()
        self.assertFalse(code.used)


class AdminPasswordFormTests(BaseCase):
    def form(self, old):
        return LimitedAdminPasswordChangeForm(self.user, {
            "old_password": old, "new_password1": "Yangi-Parol-987", "new_password2": "Yangi-Parol-987"})

    def test_site_uses_limited_form(self):
        self.assertIs(admin.site.password_change_form, LimitedAdminPasswordChangeForm)

    def test_correct_password_passes(self):
        self.assertTrue(self.form("Parol-12345").is_valid())

    def test_guessing_locks_even_the_right_password(self):
        for _ in range(LOGIN_MAX_FAILS):
            self.assertIn("old_password", self.form("xato").errors)
        form = self.form("Parol-12345")
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors.as_data()["old_password"][0].code, "password_locked")


class LastWalletTests(BaseCase):
    def test_last_regular_wallet_cannot_be_deleted(self):
        Wallet.objects.create(user=self.user, name="Telefon", summa=0, is_goal=True)
        self.wallet.summa = 0
        self.wallet.save(update_fields=["summa"])
        res = self.api.delete(f"{API}/wallets/{self.wallet.id}/")
        self.assertEqual(res.status_code, 400)
        self.assertIn("oxirgi", res.json()["error"])
        self.wallet.refresh_from_db()
        self.assertTrue(self.wallet.status)

    def test_can_delete_when_another_regular_wallet_exists(self):
        Wallet.objects.create(user=self.user, name="Naqd", summa=0)
        self.wallet.summa = 0
        self.wallet.save(update_fields=["summa"])
        self.assertEqual(self.api.delete(f"{API}/wallets/{self.wallet.id}/").status_code, 200)


class RecurringRateOutsideTransactionTests(BaseCase):
    def test_rate_is_fetched_before_date_moves(self):
        payment = self.recurring()
        seen = []

        def fake_prepare(operation):
            seen.append(RecurringPayment.objects.get(pk=payment.pk).next_date)
            return False

        with mock.patch("mainapp.recurring.prepare_uzs_rate", fake_prepare):
            self.assertEqual(process_due(self.user), 1)
        self.assertEqual(seen, [payment.next_date])


class ProviderDisconnectTests(BaseCase):
    def broken_response(self, body=None):
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        if body is None:
            response.read.side_effect = http.client.IncompleteRead(b"")
        else:
            response.read.return_value = body
        return response

    def test_stt_incomplete_read(self):
        with mock.patch("urllib.request.urlopen", return_value=self.broken_response()):
            with self.assertRaises(stt.SttError):
                stt._openai(b"audio", "audio/webm")

    def test_stt_non_object_json(self):
        with mock.patch("urllib.request.urlopen", return_value=self.broken_response(b"[1]")):
            with self.assertRaises(stt.SttError):
                stt._openai(b"audio", "audio/webm")

    @override_settings(VOICELAB_API_KEY="k")
    def test_stt_voicelab_non_object_json(self):
        with mock.patch("urllib.request.urlopen", return_value=self.broken_response(b'{"id": "1"}')), \
                mock.patch("mainapp.stt._voicelab_get", side_effect=[{"id": "1"}, [1]]):
            with self.assertRaises(stt.SttError):
                stt._voicelab(b"audio", "audio/webm")

    @override_settings(OPENAI_API_KEY="k")
    def test_tts_incomplete_read_skips_provider(self):
        with mock.patch("urllib.request.urlopen", return_value=self.broken_response()):
            with self.assertRaises(tts._Skip):
                tts._fetch("openai", "salom", "female")

    @override_settings(VOICELAB_API_KEY="k")
    def test_tts_voices_non_object_json(self):
        with mock.patch("urllib.request.urlopen", return_value=self.broken_response(b"[1]")):
            with self.assertRaises(tts.TtsError):
                tts.voicelab_voices()


class VoiceEndToEndTests(BaseCase):
    def say(self, text):
        res = self.api.post(VOICE_API, {"text": text}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        return res.json()

    def test_marta_records_todays_expense_with_right_amount(self):
        out = self.say("taksiga 3 marta 15 ming sarfladim")
        self.assertEqual(out["status"], "done", out)
        expense = Expense.objects.get()
        self.assertEqual(expense.summa, Decimal("15000"))
        self.assertEqual(timezone.localtime(expense.date).date(), timezone.localdate())

    def test_days_ago_amount_and_date(self):
        out = self.say("taksiga 20 ming 3 kun oldin sarfladim")
        self.assertEqual(out["status"], "done", out)
        expense = Expense.objects.get()
        self.assertEqual(expense.summa, Decimal("20000"))
        self.assertEqual(timezone.localtime(expense.date).date(), timezone.localdate() - timedelta(days=3))
