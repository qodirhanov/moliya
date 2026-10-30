"""Ovozli yordamchi (voice.py, voice_parse.py): gapni tushunish, savol-javob bilan to'ldirish va amalni yozish.
Claude chaqirilmaydi (ANTHROPIC_API_KEY bo'sh) — faqat bitta testda mock bilan. Tarmoq (cbu.uz) ham mock"""
import json
from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from . import voice_parse as vp
from .models import Category, Debt, Expense, ExpenseCategory, Income, Member, RecurringPayment, SavingsGoal, Transfer, User, Wallet

API = "/api/v1/voice/"


class ParseTests(TestCase):
    def amount(self, text):
        a = vp.best_amount(vp.find_amounts(vp.loose(text).split()))
        return a and (a["value"], a["currency"])

    def test_numbers_in_digits_and_words(self):
        self.assertEqual(self.amount("tushlikka 45 ming"), (45000, None))
        self.assertEqual(self.amount("qirq besh ming so'm"), (45000, "UZS"))
        self.assertEqual(self.amount("1,5 million"), (1500000, None))
        self.assertEqual(self.amount("bir yarim million"), (1500000, None))
        self.assertEqual(self.amount("yarim million"), (500000, None))
        self.assertEqual(self.amount("ikki yuz ellik ming"), (250000, None))
        self.assertEqual(self.amount("45 000 so'm"), (45000, "UZS"))
        self.assertEqual(self.amount("100$"), (100, "USD"))
        self.assertEqual(self.amount("300 dollar"), (300, "USD"))
        # "2 ta non" dagi 2 emas — ming bilan aytilgan summa tanlanadi
        self.assertEqual(self.amount("2 ta non 10 ming"), (10000, None))

    def test_cyrillic_is_transliterated(self):
        self.assertEqual(vp.loose("Тушликка 45 минг сарфладим"), "tushlikka 45 ming sarfladim")

    def test_intents(self):
        cases = {
            "tushlikka 45 ming sarfladim": "expense",
            "taksiga yigirma ming berdim": "expense",
            "non oldim 5 ming": "expense",
            "oylik tushdi 5 million": "income",
            "kartadan naqdga 200 ming o'tkaz": "transfer",
            "akmalga 1 million qarz berdim": "debt_give",
            "akmaldan 300 dollar qarz oldim": "debt_take",
            "akmal qarzini qaytardi": "debt_repay",
            "mashina maqsadiga 500 ming qo'sh": "goal_fund",
            "har oy 10-sanada internetga 100 ming": "recurring",
            "qoldig'im qancha": "query_balance",
            "balansim qancha": "query_balance",  # eski so'z ham tushuniladi
            "bu oy qancha sarfladim": "query_spent",
            "dollar kursi qancha": "query_rate",
            "qarzlarim qancha": "query_debts",
            "meni eshityapsanmi": "chat_hear",
            "hisobotni och": "nav_stats",
            "qorong'i rejim": "theme_dark",
            "oxirgisini o'chir": "undo",
            "to'xta": "cancel",
            "qirq besh ming": "ask_kind",
        }
        for text, intent in cases.items():
            with self.subTest(text=text):
                self.assertEqual(vp.detect_intent(vp.loose(text)), intent)

    def test_wake_phrase_is_stripped(self):
        self.assertEqual(vp.strip_wake(vp.loose("Salom Moliya, qoldig'im qancha")), "qoldigim qancha")
        self.assertEqual(vp.strip_wake(vp.loose("Хай Молия")), "")

    def test_dates(self):
        today = date(2026, 10, 26)
        self.assertEqual(vp.find_date("kecha bozorga", today)[0], date(2026, 10, 25))
        self.assertEqual(vp.find_date("15 dekabrgacha", today, future=True)[0], date(2026, 12, 15))
        self.assertEqual(vp.find_date("1 oyga", today, future=True)[0], today + timedelta(days=30))

    def test_person(self):
        self.assertEqual(vp.find_person(vp.normalize("Akmalga 1 million qarz berdim"), "give"), "Akmal")
        self.assertEqual(vp.find_person(vp.normalize("akmaldan qarz oldim"), "take"), "Akmal")

    def test_number_words_for_speech(self):
        self.assertEqual(vp.say_money(Decimal("1250000"), "UZS"), "bir million, ikki yuz ellik ming so'm")
        self.assertEqual(vp.number_words(45000), "qirq besh ming")

    def test_numbers_are_spelled_for_speech(self):
        cases = {
            "Qoldiq: 122 909 367 UZS":
                "Qoldiq: bir yuz yigirma ikki million, to'qqiz yuz to'qqiz ming, uch yuz oltmish yetti so'm",
            "122909367": "bir yuz yigirma ikki million, to'qqiz yuz to'qqiz ming, uch yuz oltmish yetti",
            "1,234,567": "bir million, ikki yuz o'ttiz to'rt ming, besh yuz oltmish yetti",
            "1.500.000": "bir million, besh yuz ming",
            "−30 442 334 UZS": "minus o'ttiz million, to'rt yuz qirq ikki ming, uch yuz o'ttiz to'rt so'm",
            "+14 471 330": "plyus o'n to'rt million, to'rt yuz yetmish bir ming, uch yuz o'ttiz",
            "Dollar kursi 12 650,45 so'm": "Dollar kursi o'n ikki ming olti yuz ellik so'm, qirq besh tiyin",
            "1 500": "bir ming besh yuz",
            "2026-yil": "ikki ming yigirma oltinchi yil",
            "1,5 million": "bir butun o'ndan besh million",
            "29-okt, 15%": "yigirma to'qqizinchi oktabr, o'n besh foiz",
            "2-iyun": "ikkinchi iyun",
            "soat 14:30": "soat o'n to'rt o'ttiz",
            "100 ming": "yuz ming",
            "Bugun 3 ta amal": "Bugun uch ta amal",
        }
        for text, spoken in cases.items():
            with self.subTest(text=text):
                self.assertEqual(vp.spell_numbers(text), spoken)


@override_settings(ANTHROPIC_API_KEY="", GEMINI_API_KEY="")
class VoiceApiTests(TestCase):
    def setUp(self):
        cache.clear()
        offline = mock.patch("mainapp.currency._fetch_cbu", side_effect=OSError("testlarda internet ishlatilmaydi"))
        offline.start()
        self.addCleanup(offline.stop)
        self.user = User.objects.create_user(username="abdurahmon", first_name="Abdurahmon", password="Parol-12345")
        self.api = APIClient()
        self.api.force_authenticate(self.user)
        self.naqd = Wallet.objects.create(user=self.user, name="Naqd pul", summa=Decimal("1000000"))
        self.karta = Wallet.objects.create(user=self.user, name="Humo karta", summa=Decimal("2000000"))
        self.food = ExpenseCategory.objects.create(name="Oziq-ovqat va bozor")
        self.transport = ExpenseCategory.objects.create(name="Transport va yo'l kira")
        self.other = ExpenseCategory.objects.create(name="Kutilmagan xarajatlar")
        self.salary = Category.objects.create(name="Oylik maosh")
        self.other_inc = Category.objects.create(name="Boshqa daromadlar")

    def say(self, text):
        res = self.api.post(API, {"text": text}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        return res.json()

    def balance(self, wallet):
        wallet.refresh_from_db()
        return wallet.summa

    def test_expense_with_wallet_and_category(self):
        out = self.say("Salom Moliya, tushlikka 45 ming naqddan sarfladim")
        self.assertEqual(out["status"], "done", out)
        self.assertIsNone(out["say"])  # bajarilgan amal ovozda aytilmaydi
        expense = Expense.objects.get()
        self.assertEqual(expense.summa, Decimal("45000"))
        self.assertEqual(expense.category, self.food)
        self.assertEqual(expense.wallet, self.naqd)
        self.assertEqual(self.balance(self.naqd), Decimal("955000"))
        self.assertEqual((out["done"][0]["type"], out["done"][0]["id"]), ("expenses", expense.pk))
        self.assertEqual(expense.description, "Tushlik")  # izoh — gapning o'zi emas, "nima uchun"

    def test_missing_amount_is_asked(self):
        out = self.say("taksiga pul to'ladim kartadan")
        self.assertEqual(out["status"], "ask")
        self.assertEqual(out["text"], "Qancha sarfladingiz?")
        self.assertTrue(out["expect_reply"])
        out = self.say("yigirma ming")
        self.assertEqual(out["status"], "done", out)
        expense = Expense.objects.get()
        self.assertEqual((expense.summa, expense.category, expense.wallet), (Decimal("20000"), self.transport, self.karta))

    def test_missing_wallet_is_asked_and_answered_by_name(self):
        out = self.say("bozorga 100 ming ketdi")
        self.assertEqual(out["status"], "ask")
        self.assertIn("Naqd pul", out["text"])
        self.assertIn("Humo karta", out["text"])
        out = self.say("kartadan")
        self.assertEqual(out["status"], "done", out)
        self.assertEqual(Expense.objects.get().wallet, self.karta)

    def test_wallet_answer_by_ordinal(self):
        self.say("bozorga 100 ming ketdi")
        out = self.say("birinchisi")
        self.assertEqual(out["status"], "done", out)
        self.assertEqual(Expense.objects.get().wallet, self.naqd)

    def test_income(self):
        out = self.say("oylik tushdi 5 million kartaga")
        self.assertEqual(out["status"], "done", out)
        income = Income.objects.get()
        self.assertEqual((income.summa, income.category, income.wallet), (Decimal("5000000"), self.salary, self.karta))

    def test_transfer(self):
        out = self.say("kartadan naqdga 200 ming o'tkaz")
        self.assertEqual(out["status"], "done", out)
        transfer = Transfer.objects.get()
        self.assertEqual((transfer.from_wallet, transfer.to_wallet, transfer.summa), (self.karta, self.naqd, Decimal("200000")))

    def test_debt_give_take_and_repay(self):
        out = self.say("Akmalga 300 ming qarz berdim naqddan")
        self.assertEqual(out["status"], "done", out)
        debt = Debt.objects.get()
        self.assertEqual((debt.person_name, debt.debt_type, debt.summa), ("Akmal", "give", Decimal("300000")))
        self.assertEqual(self.balance(self.naqd), Decimal("700000"))

        out = self.say("Akmal qarzini qaytardi")
        self.assertEqual(out["status"], "done", out)
        debt.refresh_from_db()
        self.assertTrue(debt.is_settled)
        self.assertEqual(self.balance(self.naqd), Decimal("1000000"))

    def test_debt_person_is_asked(self):
        out = self.say("500 ming qarz oldim kartaga")
        self.assertEqual(out["status"], "ask")
        self.assertEqual(out["text"], "Kimdan qarz oldingiz?")
        out = self.say("Botirdan")
        self.assertEqual(out["status"], "done", out)
        self.assertEqual(Debt.objects.get().person_name, "Botir")

    def test_insufficient_balance_is_reported(self):
        out = self.say("naqddan 5 million sarfladim bozorga")
        self.assertEqual(out["status"], "error")
        self.assertIn("yetarli emas", out["text"])
        # Ovozda raqam so'z bilan: "1,000,000 UZS" emas
        self.assertIn("bir million so'm", out["say"])
        self.assertFalse(Expense.objects.exists())

    def test_hearing_check_uses_first_name(self):
        out = self.say("Salom Moliya meni eshityapsanmi")
        self.assertEqual(out["status"], "reply")
        self.assertEqual(out["text"], "Ha, Abdurahmon, eshityapman.")

    def test_balance_query(self):
        out = self.say("qoldigim qancha")
        self.assertEqual(out["status"], "reply")
        self.assertEqual(out["text"], "Jami qoldiq: 3,000,000 so'm")
        self.assertIn("uch million so'm", out["say"])

    def test_spent_query(self):
        Expense.objects.create(user=self.user, wallet=self.naqd, category=self.food, summa=Decimal("40000"), date=timezone.now())
        out = self.say("bugun qancha sarfladim")
        self.assertEqual(out["text"], "Bugun sarflandi: 40,000 so'm")

    def test_navigation_and_client_actions(self):
        self.assertEqual(self.say("hisobotni och")["client"], {"action": "navigate", "target": "stats"})
        self.assertEqual(self.say("qorong'i rejim")["client"], {"action": "theme", "value": "dark"})
        self.assertEqual(self.say("oxirgisini bekor qil")["client"], {"action": "undo"})

    def test_cancel_drops_pending_question(self):
        self.say("bozorga pul ketdi")
        out = self.say("kerak emas")
        self.assertEqual(out["client"], {"action": "close"})
        out = self.say("50 ming")  # endi savolga javob emas — yangi buyruq
        self.assertEqual(out["status"], "ask")
        self.assertFalse(Expense.objects.exists())

    def test_kind_is_guessed_from_category(self):
        out = self.say("45 ming benzin kartadan")
        self.assertEqual(out["status"], "done", out)
        self.assertEqual(Expense.objects.get().category, self.transport)

    def test_kind_is_asked(self):
        out = self.say("qirq besh ming kartaga")
        self.assertEqual(out["text"], "Bu kirimmi yoki chiqim?")
        out = self.say("kirim")
        self.assertEqual(out["status"], "done", out)
        self.assertEqual(Income.objects.get().category, self.other_inc)

    def test_recurring(self):
        out = self.say("har oy 10-sanada internetga 100 ming kartadan")
        self.assertEqual(out["status"], "done", out)
        rp = RecurringPayment.objects.get()
        self.assertEqual((rp.frequency, rp.summa, rp.next_date.day), ("monthly", Decimal("100000"), 10))

    def test_goal_fund(self):
        goal_wallet = Wallet.objects.create(user=self.user, name="Mashina uchun", summa=Decimal("0"))
        SavingsGoal.objects.create(user=self.user, name="Mashina", target=Decimal("100000000"), wallet=goal_wallet)
        out = self.say("mashina maqsadiga 500 ming qo'sh kartadan")
        self.assertEqual(out["status"], "done", out)
        self.assertEqual(self.balance(goal_wallet), Decimal("500000"))

    def test_other_users_wallet_is_never_used(self):
        other = User.objects.create_user(username="begona", password="Parol-12345")
        Wallet.objects.create(user=other, name="Seyf", summa=Decimal("9000000"))
        out = self.say("seyfdan 100 ming bozorga sarfladim")
        self.assertEqual(out["status"], "ask")  # "Seyf" foydalanuvchining hamyoni emas — qaysi hamyon so'raladi
        self.assertNotIn("Seyf", out["text"])

    def test_reopened_orb_forgets_old_question(self):
        out = self.say("bozorga pul ketdi")
        self.assertEqual(out["status"], "ask", out)
        # Orb yopilib qayta ochildi (fresh) — "ellik ming" eski savolga javob deb o'qilmaydi
        res = self.api.post(API, {"text": "ellik ming", "fresh": True}, format="json")
        self.assertNotEqual(res.json()["status"], "done", res.json())
        self.assertFalse(Expense.objects.exists())
        # fresh bo'lmasa (o'sha suhbat) — savolga javob sifatida ishlaydi
        self.say("bozorga pul ketdi")
        self.assertEqual(self.say("ellik ming naqddan")["status"], "done")

    def test_not_understood(self):
        out = self.say("ob-havo qanday")
        self.assertEqual(out["status"], "reply")
        self.assertIn("Tushunmadim", out["text"])

    def test_empty_text_rejected(self):
        res = self.api.post(API, {"text": "  "}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_requires_login(self):
        res = APIClient().post(API, {"text": "qoldig'im qancha"}, format="json")
        self.assertIn(res.status_code, (401, 403))

    @override_settings(ANTHROPIC_API_KEY="test-key")
    def test_claude_used_when_rules_do_not_understand(self):
        payload = {"commands": [{
            "intent": "expense", "amount": 30000, "currency": None, "wallet_id": self.naqd.pk, "to_wallet_id": None,
            "category_id": self.food.pk, "debt_id": None, "goal_id": None, "person": None, "description": "Shirinlik",
            "date": None, "due_date": None, "period": None, "frequency": None, "day": None, "kind": None, "reply": None,
        }]}
        fake = mock.Mock(stop_reason="end_turn", content=[mock.Mock(type="text", text=json.dumps(payload))])
        client = mock.Mock()
        client.beta.messages.create.return_value = fake
        with mock.patch("mainapp.assistant._client", return_value=client):
            out = self.say("shirinlikka o'ttiz mingcha chiqib ketibdi")
        self.assertEqual(out["status"], "done", out)
        self.assertEqual(Expense.objects.get().summa, Decimal("30000"))
        kwargs = client.beta.messages.create.call_args.kwargs
        self.assertEqual(kwargs["output_config"]["format"]["type"], "json_schema")


@override_settings(ANTHROPIC_API_KEY="", OPENAI_API_KEY="test-openai-key", OPENAI_TRANSCRIBE_MODEL="gpt-4o-transcribe")
class ServerSttTests(TestCase):
    """Brauzer tanimasa ovoz yozuvi serverga keladi va OpenAI orqali taniladi (stt.py). Tarmoq mock"""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="abdurahmon", first_name="Abdurahmon", password="Parol-12345")
        self.api = APIClient()
        self.api.force_authenticate(self.user)
        self.wallet = Wallet.objects.create(user=self.user, name="Naqd pul", summa=Decimal("1000000"))
        self.food = ExpenseCategory.objects.create(name="Oziq-ovqat va bozor")

    def audio(self, content=b"x" * 4000, content_type="audio/webm"):
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile("voice.webm", content, content_type=content_type)

    def fake_openai(self, text):
        response = mock.MagicMock()
        response.read.return_value = json.dumps({"text": text}).encode()
        response.__enter__.return_value = response
        return mock.patch("mainapp.stt.urllib.request.urlopen", return_value=response)

    def test_audio_is_transcribed_and_executed(self):
        with self.fake_openai("Tushlikka 45 ming so'm sarfladim") as urlopen:
            res = self.api.post(API, {"audio": self.audio()}, format="multipart")
        self.assertEqual(res.status_code, 200, res.content)
        out = res.json()
        self.assertEqual(out["status"], "done", out)
        self.assertEqual(out["heard"], "Tushlikka 45 ming so'm sarfladim")
        self.assertEqual(Expense.objects.get().summa, Decimal("45000"))
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.openai.com/v1/audio/transcriptions")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-openai-key")
        body = request.data
        self.assertIn(b'name="language"\r\n\r\nuz', body)
        self.assertIn(b'name="model"\r\n\r\ngpt-4o-transcribe', body)

    def test_audio_answers_pending_question(self):
        self.api.post(API, {"text": "bozorga pul ketdi"}, format="json")
        with self.fake_openai("ellik ming"):
            out = self.api.post(API, {"audio": self.audio()}, format="multipart").json()
        self.assertEqual(out["status"], "done", out)
        self.assertEqual(Expense.objects.get().summa, Decimal("50000"))

    def test_empty_transcript_asks_again(self):
        with self.fake_openai(""):
            out = self.api.post(API, {"audio": self.audio()}, format="multipart").json()
        self.assertEqual(out["status"], "reply")
        self.assertTrue(out["expect_reply"])

    def test_openai_failure_is_reported(self):
        import urllib.error
        error = urllib.error.HTTPError("u", 401, "Unauthorized", {}, None)
        with mock.patch("mainapp.stt.urllib.request.urlopen", side_effect=error):
            out = self.api.post(API, {"audio": self.audio()}, format="multipart").json()
        self.assertEqual(out["status"], "error")
        self.assertIn("tanib bo'lmadi", out["text"])

    def test_bad_uploads_rejected(self):
        res = self.api.post(API, {"audio": self.audio(content_type="text/plain")}, format="multipart")
        self.assertEqual(res.status_code, 400)
        with mock.patch("mainapp.stt.MAX_AUDIO_BYTES", 100):
            res = self.api.post(API, {"audio": self.audio()}, format="multipart")
        self.assertEqual(res.status_code, 400)

    @override_settings(OPENAI_API_KEY="", GEMINI_API_KEY="")
    def test_disabled_without_key(self):
        res = self.api.post(API, {"audio": self.audio()}, format="multipart")
        self.assertEqual(res.status_code, 400)
        self.assertFalse(self.api.get("/api/v1/auth/me/").json()["user"]["voice_server_stt"])

    def test_me_reports_server_stt(self):
        self.assertTrue(self.api.get("/api/v1/auth/me/").json()["user"]["voice_server_stt"])

    def test_not_understood_text_is_flagged_for_audio_retry(self):
        out = self.api.post(API, {"text": "ob-havo qanday"}, format="json").json()
        self.assertIs(out["understood"], False)
        out = self.api.post(API, {"text": "qoldig'im qancha"}, format="json").json()
        self.assertNotIn("understood", out)


@override_settings(ANTHROPIC_API_KEY="", OPENAI_API_KEY="", AZURE_SPEECH_KEY="az-key", AZURE_SPEECH_REGION="westeurope")
class ServerTtsTests(TestCase):
    """Javobni ravon o'zbekcha ovozda o'qish (tts.py): Azure o'zbek neyron ovozi, zaxira — OpenAI. Tarmoq mock"""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="abdurahmon", password="Parol-12345")
        self.api = APIClient()
        self.api.force_authenticate(self.user)

    def fake_audio(self, data=b"ID3-mp3-bytes"):
        response = mock.MagicMock()
        response.read.return_value = data
        response.__enter__.return_value = response
        return mock.patch("mainapp.tts.urllib.request.urlopen", return_value=response)

    def say(self, text, voice="female"):
        return self.api.post("/api/v1/voice/tts/", {"text": text, "voice": voice}, format="json")

    def test_azure_uzbek_voice_and_ssml(self):
        with self.fake_audio() as urlopen:
            res = self.say("Ha, Abdurahmon, eshityapman. «Naqd» <test>", voice="male")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "audio/mpeg")
        self.assertEqual(res["Cache-Control"], "no-store")
        self.assertEqual(res.content, b"ID3-mp3-bytes")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://westeurope.tts.speech.microsoft.com/cognitiveservices/v1")
        ssml = request.data.decode()
        self.assertIn("uz-UZ-SardorNeural", ssml)
        self.assertIn("xml:lang='uz-UZ'", ssml)
        self.assertIn("&lt;test&gt;", ssml)  # matn XML sifatida ekranlanadi
        self.assertNotIn("«", ssml)          # ekrandagi qo'shtirnoq o'qilmaydi

    def test_same_phrase_is_cached(self):
        with self.fake_audio() as urlopen:
            self.say("Qancha sarfladingiz?")
            self.say("Qancha sarfladingiz?")
        self.assertEqual(urlopen.call_count, 1)

    @override_settings(AZURE_SPEECH_KEY="", OPENAI_API_KEY="sk-test")
    def test_openai_fallback_with_uzbek_instructions(self):
        with self.fake_audio() as urlopen:
            res = self.say("Salom")
        self.assertEqual(res.status_code, 200)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.openai.com/v1/audio/speech")
        body = json.loads(request.data)
        self.assertEqual(body["model"], "gpt-4o-mini-tts")
        self.assertIn("o'zbek", body["instructions"])

    @override_settings(AZURE_SPEECH_KEY="", OPENAI_API_KEY="")
    def test_without_provider_browser_voice_is_used(self):
        self.assertEqual(self.say("Salom").status_code, 503)
        self.assertIsNone(self.api.get("/api/v1/auth/me/").json()["user"]["voice_server_tts"])

    def test_me_reports_provider(self):
        self.assertEqual(self.api.get("/api/v1/auth/me/").json()["user"]["voice_server_tts"], "azure")

    def test_provider_error_returns_503(self):
        import urllib.error
        with mock.patch("mainapp.tts.urllib.request.urlopen", side_effect=urllib.error.URLError("down")):
            self.assertEqual(self.say("Salom").status_code, 503)

    def test_validation(self):
        self.assertEqual(self.say("").status_code, 400)
        self.assertEqual(self.say("a" * 700).status_code, 400)
        self.assertIn(APIClient().post("/api/v1/voice/tts/", {"text": "Salom"}, format="json").status_code, (401, 403))


@override_settings(ANTHROPIC_API_KEY="", OPENAI_API_KEY="")
class VoiceSmartTests(TestCase):
    """Takomillashtirilgan yordamchi: bir gapda bir nechta amal, oxirgisini tuzatish, hamyon ochish, a'zo,
    odatiy hamyon, ruscha buyruqlar va yangi savollar"""

    def setUp(self):
        cache.clear()
        offline = mock.patch("mainapp.currency._fetch_cbu", side_effect=OSError("testlarda internet ishlatilmaydi"))
        offline.start()
        self.addCleanup(offline.stop)
        self.user = User.objects.create_user(username="abdurahmon", first_name="Abdurahmon", password="Parol-12345")
        self.api = APIClient()
        self.api.force_authenticate(self.user)
        self.naqd = Wallet.objects.create(user=self.user, name="Naqd pul", summa=Decimal("1000000"))
        self.karta = Wallet.objects.create(user=self.user, name="Humo karta", summa=Decimal("2000000"))
        self.food = ExpenseCategory.objects.create(name="Oziq-ovqat va bozor")
        self.transport = ExpenseCategory.objects.create(name="Transport va yo'l kira")
        self.clothes = ExpenseCategory.objects.create(name="Kiyim-kechak")
        self.other = ExpenseCategory.objects.create(name="Kutilmagan xarajatlar")
        self.salary = Category.objects.create(name="Oylik maosh")
        self.other_inc = Category.objects.create(name="Boshqa daromadlar")

    def say(self, text):
        res = self.api.post(API, {"text": text}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        return res.json()

    def balance(self, wallet):
        wallet.refresh_from_db()
        return wallet.summa

    def test_several_expenses_in_one_sentence_share_wallet(self):
        out = self.say("naqddan tushlikka 45 ming, taksiga 20 ming sarfladim")
        self.assertEqual(out["status"], "done", out)
        self.assertEqual(len(out["done"]), 2)
        self.assertEqual(sorted(Expense.objects.values_list("summa", "category__name", "wallet__name")),
                         [(Decimal("20000"), "Transport va yo'l kira", "Naqd pul"),
                          (Decimal("45000"), "Oziq-ovqat va bozor", "Naqd pul")])
        self.assertEqual(len(out["items"]), 2)

    def test_several_incomes_and_comma_inside_number(self):
        out = self.say("oylik 5 million va bonus 1,5 million tushdi kartaga")
        self.assertEqual(out["status"], "done", out)
        self.assertEqual(sorted(Income.objects.values_list("summa", flat=True)), [Decimal("1500000"), Decimal("5000000")])

    def test_two_questions_in_one_sentence(self):
        Debt.objects.create(user=self.user, person_name="Akmal", debt_type="give", summa=Decimal("100000"), wallet=self.naqd)
        out = self.say("qoldig'im va qarzlarim qancha")
        self.assertEqual(out["status"], "reply")
        self.assertIn("Jami qoldiq", out["text"])
        self.assertIn("qarzdorlar", out["text"])

    def test_queue_continues_after_question(self):
        out = self.say("bozorga 45 ming, taksiga 20 ming sarfladim")
        self.assertEqual(out["status"], "ask")  # hamyon so'raladi
        out = self.say("kartadan")
        self.assertEqual(out["status"], "done", out)
        self.assertEqual(Expense.objects.count(), 2)

    def test_edit_last_amount(self):
        self.say("tushlikka 45 ming naqddan sarfladim")
        out = self.say("yo'q, 50 ming edi")
        self.assertEqual(out["status"], "done", out)
        self.assertEqual(Expense.objects.get().summa, Decimal("50000"))
        self.assertEqual(self.balance(self.naqd), Decimal("950000"))

    def test_edit_last_wallet_and_category(self):
        self.say("tushlikka 45 ming naqddan sarfladim")
        self.say("kartadan edi")
        self.say("oxirgisini transportga o'zgartir")
        expense = Expense.objects.get()
        self.assertEqual((expense.wallet, expense.category), (self.karta, self.transport))
        self.assertEqual(self.balance(self.naqd), Decimal("1000000"))
        self.assertEqual(self.balance(self.karta), Decimal("1955000"))

    def test_past_tense_is_new_expense_not_edit(self):
        out = self.say("kecha bozorga 100 ming naqddan ketgan edi")
        self.assertEqual(out["status"], "done", out)
        self.assertEqual(timezone.localtime(Expense.objects.get().date).date(), timezone.localdate() - timedelta(days=1))

    def test_edit_without_recent_action(self):
        out = self.say("yo'q, 50 ming edi")
        self.assertEqual(out["status"], "reply")
        self.assertFalse(Expense.objects.exists())

    def test_wallet_create(self):
        out = self.say("yangi hamyon och Uzcard")
        self.assertEqual(out["status"], "done", out)
        wallet = Wallet.objects.get(name="Uzcard")
        self.assertEqual((wallet.summa, wallet.currency), (Decimal("0"), "UZS"))
        self.assertEqual(out["done"][0]["type"], "wallets")
        out = self.say("dollar hamyon och 300 dollar bilan")
        self.assertEqual(out["status"], "done", out)
        self.assertTrue(Wallet.objects.filter(currency="USD", summa=Decimal("300")).exists())

    def test_wallet_create_asks_name(self):
        out = self.say("yangi hamyon och")
        self.assertEqual(out["status"], "ask")
        self.say("Seyf")
        self.assertTrue(Wallet.objects.filter(user=self.user, name="Seyf").exists())

    def test_member_is_attached(self):
        brother = Member.objects.create(user=self.user, name="Abdulaziz ukam")
        out = self.say("ukamga kiyim oldim 300 ming kartadan")
        self.assertEqual(out["status"], "done", out)
        expense = Expense.objects.get()
        self.assertEqual((expense.member, expense.category), (brother, self.clothes))
        self.assertIn("ukam uchun", out["text"])

    def test_habit_wallet_used_when_not_said(self):
        for _ in range(4):
            Expense.objects.create(user=self.user, wallet=self.karta, category=self.food, summa=Decimal("1000"),
                                   date=timezone.now())
        out = self.say("tushlikka 30 ming sarfladim")
        self.assertEqual(out["status"], "done", out)
        self.assertEqual(Expense.objects.order_by("-id").first().wallet, self.karta)

    def test_session_wallet_reused(self):
        self.say("tushlikka 30 ming naqddan sarfladim")
        out = self.say("taksiga 20 ming sarfladim")
        self.assertEqual(out["status"], "done", out)
        self.assertEqual(Expense.objects.order_by("-id").first().wallet, self.naqd)

    def test_russian_command(self):
        out = self.say("потратил на обед сорок пять тысяч с карты")
        self.assertEqual(out["status"], "done", out)
        expense = Expense.objects.get()
        self.assertEqual((expense.summa, expense.category, expense.wallet), (Decimal("45000"), self.food, self.karta))

    def test_query_top(self):
        Expense.objects.create(user=self.user, wallet=self.naqd, category=self.food, summa=Decimal("300000"), date=timezone.now())
        Expense.objects.create(user=self.user, wallet=self.naqd, category=self.transport, summa=Decimal("100000"),
                               date=timezone.now())
        out = self.say("eng ko'p nimaga sarfladim")
        self.assertEqual(out["status"], "reply")
        self.assertIn("Oziq-ovqat va bozor", out["text"])
        self.assertEqual(out["items"][0]["label"], "Oziq-ovqat va bozor")

    def test_query_goals(self):
        goal_wallet = Wallet.objects.create(user=self.user, name="Mashina uchun", summa=Decimal("2500000"))
        SavingsGoal.objects.create(user=self.user, name="Mashina", target=Decimal("10000000"), wallet=goal_wallet)
        out = self.say("maqsadimga qancha qoldi")
        self.assertIn("25% yig'ildi", out["text"])
        self.assertIn("7,500,000", out["text"])

    def test_query_recurring(self):
        tomorrow = timezone.localdate() + timedelta(days=1)
        RecurringPayment.objects.create(user=self.user, kind="expense", name="Internet", wallet=self.karta,
                                        summa=Decimal("100000"), expense_category=self.food, frequency="monthly",
                                        start_date=tomorrow, next_date=tomorrow)
        out = self.say("keyingi to'lovlar qachon")
        self.assertEqual(out["status"], "reply", out)
        self.assertIn("Internet", out["text"])
        self.assertIn("ertaga", out["say"])

    def test_query_summary_and_compare(self):
        Expense.objects.create(user=self.user, wallet=self.naqd, category=self.food, summa=Decimal("40000"), date=timezone.now())
        out = self.say("bugungi xulosa")
        self.assertEqual(out["status"], "reply")
        self.assertIn("chiqim 40,000 so'm", out["text"])
        out = self.say("o'tgan oyga nisbatan qanday")
        self.assertEqual(out["status"], "reply")
        self.assertEqual(len(out["items"]), 2)

    def test_balance_lists_wallets(self):
        out = self.say("qoldig'im qancha")
        self.assertEqual([i["label"] for i in out["items"]], ["Naqd pul", "Humo karta"])


class ParseSmartTests(TestCase):
    def amount(self, text):
        a = vp.best_amount(vp.find_amounts(vp.loose(text).split()))
        return a and (a["value"], a["currency"])

    def test_russian_numbers_and_short_forms(self):
        self.assertEqual(self.amount("сорок пять тысяч"), (45000, None))
        self.assertEqual(self.amount("сто пятьдесят тысяч сумов"), (150000, "UZS"))
        self.assertEqual(self.amount("полтора миллиона"), (1500000, None))
        self.assertEqual(self.amount("45k"), (45000, None))

    def test_new_intents(self):
        cases = {
            "yo'q, 50 ming edi": "edit_last",
            "kartadan edi": "edit_last",
            "kecha bozorga 100 ming ketgan edi": "expense",
            "kerak emas": "cancel",
            "yangi hamyon och Humo": "wallet_create",
            "hamyonlar sahifasini och": "nav_wallets",
            "eng ko'p nimaga sarfladim": "query_top",
            "maqsadimga qancha qoldi": "query_goals",
            "keyingi to'lovlar qachon": "query_recurring",
            "bugungi xulosa": "query_summary",
            "o'tgan oyga nisbatan qanday": "query_compare",
            "потратил на обед 45 тысяч": "expense",
            "получил зарплату": "income",
            "дал в долг Акмалу миллион": "debt_give",
        }
        for text, intent in cases.items():
            with self.subTest(text=text):
                self.assertEqual(vp.detect_intent(vp.loose(text)), intent)

    def test_item_phrase(self):
        self.assertEqual(vp.item_phrase(vp.normalize("tushlikka 45 ming naqddan sarfladim"), ("naqd",)), "Tushlik")
        self.assertEqual(vp.item_phrase(vp.normalize("har oy 10-sanada internetga 100 ming")), "Internet")
        self.assertEqual(vp.item_phrase(vp.normalize("Akmal uchun sovg'a oldim 300 ming")), "Akmal uchun sovg'a")


def gemini_response(text, finish="STOP"):
    response = mock.MagicMock()
    response.read.return_value = json.dumps(
        {"candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": finish}]}).encode()
    response.__enter__.return_value = response
    return response


@override_settings(ANTHROPIC_API_KEY="", OPENAI_API_KEY="", GEMINI_API_KEY="gemini-test-key", GEMINI_MODEL="gemini-test-flash",
                   GEMINI_VOICE_MODEL="")
class GeminiVoiceTests(TestCase):
    """Tekin Gemini kaliti bilan: qoidalar tushunmagan gap va ovoz yozuvi Gemini orqali. Tarmoq mock"""

    def setUp(self):
        cache.clear()
        offline = mock.patch("mainapp.currency._fetch_cbu", side_effect=OSError("testlarda internet ishlatilmaydi"))
        offline.start()
        self.addCleanup(offline.stop)
        self.user = User.objects.create_user(username="abdurahmon", first_name="Abdurahmon", password="Parol-12345")
        self.api = APIClient()
        self.api.force_authenticate(self.user)
        self.naqd = Wallet.objects.create(user=self.user, name="Naqd pul", summa=Decimal("1000000"))
        self.food = ExpenseCategory.objects.create(name="Oziq-ovqat va bozor")

    def command(self, **fields):
        item = {"intent": "expense", "amount": None, "currency": None, "wallet_id": None, "to_wallet_id": None,
                "category_id": None, "debt_id": None, "goal_id": None, "member_id": None, "name": None, "person": None,
                "description": None, "date": None, "due_date": None, "period": None, "frequency": None, "day": None,
                "kind": None, "reply": None}
        item.update(fields)
        return json.dumps({"commands": [item]})

    def audio(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile("voice.webm", b"x" * 4000, content_type="audio/webm")

    def test_gemini_parses_command_rules_do_not_understand(self):
        raw = self.command(amount=30000, wallet_id=self.naqd.pk, category_id=self.food.pk, description="Shirinlik")
        with mock.patch("mainapp.assistant.urllib.request.urlopen", return_value=gemini_response(raw)) as urlopen:
            out = self.api.post(API, {"text": "shirinlikka o'ttiz mingcha chiqib ketibdi"}, format="json").json()
        self.assertEqual(out["status"], "done", out)
        expense = Expense.objects.get()
        self.assertEqual((expense.summa, expense.category, expense.wallet), (Decimal("30000"), self.food, self.naqd))
        request = urlopen.call_args.args[0]
        self.assertIn("/models/gemini-test-flash:generateContent", request.full_url)
        self.assertEqual(request.get_header("X-goog-api-key"), "gemini-test-key")
        body = json.loads(request.data)
        self.assertEqual(body["generationConfig"]["responseMimeType"], "application/json")
        self.assertIn("responseJsonSchema", body["generationConfig"])

    def test_old_model_retries_without_new_fields(self):
        import urllib.error
        raw = self.command(amount=30000, wallet_id=self.naqd.pk, category_id=self.food.pk)
        error = urllib.error.HTTPError("u", 400, "Bad Request", {}, None)
        with mock.patch("mainapp.assistant.urllib.request.urlopen", side_effect=[error, gemini_response(raw)]) as urlopen:
            out = self.api.post(API, {"text": "shirinlikka o'ttiz mingcha chiqib ketibdi"}, format="json").json()
        self.assertEqual(out["status"], "done", out)
        relaxed = json.loads(urlopen.call_args_list[1].args[0].data)
        self.assertNotIn("responseJsonSchema", relaxed["generationConfig"])
        self.assertNotIn("thinkingConfig", relaxed["generationConfig"])

    @override_settings(GEMINI_FALLBACK_MODELS=["gemini-test-lite"])
    def test_busy_model_falls_back_to_lite(self):
        import urllib.error
        raw = self.command(amount=30000, wallet_id=self.naqd.pk, category_id=self.food.pk)
        busy = urllib.error.HTTPError("u", 503, "Service Unavailable", {}, None)
        with mock.patch("mainapp.assistant.urllib.request.urlopen", side_effect=[busy, gemini_response(raw)]) as urlopen:
            out = self.api.post(API, {"text": "shirinlikka o'ttiz mingcha chiqib ketibdi"}, format="json").json()
        self.assertEqual(out["status"], "done", out)
        self.assertIn("/models/gemini-test-lite:", urlopen.call_args.args[0].full_url)
        # Band model bir muddat chetlab o'tiladi: keyingi so'rov darhol zaxiradan boshlanadi
        with mock.patch("mainapp.assistant.urllib.request.urlopen", return_value=gemini_response(raw)) as urlopen:
            self.api.post(API, {"text": "shirinlikka o'ttiz mingcha chiqib ketibdi"}, format="json")
        self.assertIn("/models/gemini-test-lite:", urlopen.call_args_list[0].args[0].full_url)

    def test_off_topic_question_ends_conversation(self):
        raw = self.command(intent="off_topic", reply="Ob-havoni bilmayman, faqat moliya bo'yicha yordam beraman.")
        with mock.patch("mainapp.assistant.urllib.request.urlopen", return_value=gemini_response(raw)):
            out = self.api.post(API, {"text": "bugun ob-havo qanday bo'ladi"}, format="json").json()
        self.assertEqual(out["status"], "reply", out)
        self.assertTrue(out["off_topic"])
        self.assertTrue(out["end"])
        self.assertFalse(out["expect_reply"])
        self.assertIn("moliya", out["text"])
        self.assertFalse(Expense.objects.exists())

    @override_settings(GEMINI_VOICE_MODEL="gemini-test-lite")
    def test_voice_uses_fast_model_first(self):
        raw = self.command(amount=30000, wallet_id=self.naqd.pk, category_id=self.food.pk)
        with mock.patch("mainapp.assistant.urllib.request.urlopen", return_value=gemini_response(raw)) as urlopen:
            self.api.post(API, {"text": "shirinlikka o'ttiz mingcha chiqib ketibdi"}, format="json")
        self.assertIn("/models/gemini-test-lite:", urlopen.call_args.args[0].full_url)
        self.assertLessEqual(urlopen.call_args.kwargs["timeout"], 4)

    def test_slow_gemini_does_not_hang_the_reply(self):
        import socket
        clock = [1000.0]

        def slow(request, timeout):  # har urinish o'z vaqt chegarasigacha osilib, so'ng uziladi
            clock[0] += timeout
            raise socket.timeout("slow")

        with mock.patch("mainapp.assistant.time.monotonic", side_effect=lambda: clock[0]), \
                mock.patch("mainapp.assistant.urllib.request.urlopen", side_effect=slow) as urlopen:
            out = self.api.post(API, {"text": "shirinlikka o'ttiz mingcha chiqib ketibdi"}, format="json").json()
        self.assertIn("Tushunmadim", out["text"])
        # Har urinish vaqti cheklangan va jami byudjetdan (6 s) oshmaydi
        self.assertTrue(all(c.kwargs["timeout"] <= 4 for c in urlopen.call_args_list))
        self.assertLessEqual(sum(c.kwargs["timeout"] for c in urlopen.call_args_list), 6)

    def test_gemini_failure_falls_back_to_not_understood(self):
        import urllib.error
        error = urllib.error.HTTPError("u", 429, "Too Many Requests", {}, None)
        with mock.patch("mainapp.assistant.urllib.request.urlopen", side_effect=error):
            out = self.api.post(API, {"text": "shirinlikka o'ttiz mingcha chiqib ketibdi"}, format="json").json()
        self.assertEqual(out["status"], "reply")
        self.assertIn("Tushunmadim", out["text"])
        self.assertFalse(Expense.objects.exists())

    def test_gemini_garbage_is_ignored(self):
        with mock.patch("mainapp.assistant.urllib.request.urlopen", return_value=gemini_response("bu json emas")):
            out = self.api.post(API, {"text": "shirinlikka o'ttiz mingcha chiqib ketibdi"}, format="json").json()
        self.assertIn("Tushunmadim", out["text"])

    def test_foreign_ids_from_gemini_are_dropped(self):
        other = User.objects.create_user(username="begona", password="Parol-12345")
        foreign = Wallet.objects.create(user=other, name="Seyf", summa=Decimal("9000000"))
        raw = self.command(amount=30000, wallet_id=foreign.pk, category_id=self.food.pk)
        with mock.patch("mainapp.assistant.urllib.request.urlopen", return_value=gemini_response(raw)):
            self.api.post(API, {"text": "shirinlikka o'ttiz mingcha chiqib ketibdi"}, format="json")
        self.assertFalse(Expense.objects.filter(wallet=foreign).exists())

    def test_rules_still_answer_without_network(self):
        with mock.patch("mainapp.assistant.urllib.request.urlopen") as urlopen:
            out = self.api.post(API, {"text": "tushlikka 45 ming sarfladim"}, format="json").json()
        self.assertEqual(out["status"], "done", out)
        urlopen.assert_not_called()

    def test_audio_transcribed_by_gemini(self):
        self.assertTrue(self.api.get("/api/v1/auth/me/").json()["user"]["voice_server_stt"])
        with mock.patch("mainapp.assistant.urllib.request.urlopen",
                        return_value=gemini_response("Tushlikka 45 ming so'm sarfladim")) as urlopen:
            out = self.api.post(API, {"audio": self.audio()}, format="multipart").json()
        self.assertEqual(out["status"], "done", out)
        self.assertEqual(out["heard"], "Tushlikka 45 ming so'm sarfladim")
        self.assertEqual(Expense.objects.get().summa, Decimal("45000"))
        parts = json.loads(urlopen.call_args.args[0].data)["contents"][0]["parts"]
        self.assertEqual(parts[1]["inlineData"]["mimeType"], "audio/webm")

    def test_gemini_stt_failure_is_reported(self):
        import urllib.error
        error = urllib.error.HTTPError("u", 500, "Server Error", {}, None)
        with mock.patch("mainapp.assistant.urllib.request.urlopen", side_effect=error):
            out = self.api.post(API, {"audio": self.audio()}, format="multipart").json()
        self.assertEqual(out["status"], "error")
        self.assertIn("tanib bo'lmadi", out["text"])


WAV = b"RIFF\x24\x00\x00\x00WAVEfmt fake-voicelab-audio"


def http_response(body, status=200):
    response = mock.MagicMock()
    response.read.return_value = body
    response.status = status
    response.__enter__.return_value = response
    return response


@override_settings(ANTHROPIC_API_KEY="", OPENAI_API_KEY="", AZURE_SPEECH_KEY="", AZURE_SPEECH_REGION="",
                   VOICELAB_API_KEY="vlk_test", VOICELAB_VOICE_FEMALE="voice_madina", VOICELAB_VOICE_MALE="")
class VoiceLabTtsTests(TestCase):
    """VoiceLab (voicelab.uz) — birinchi navbatdagi o'zbekcha ovoz; krediti tugasa keyingi provayder. Tarmoq mock"""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="abdurahmon", password="Parol-12345")
        self.api = APIClient()
        self.api.force_authenticate(self.user)

    def say(self, text, voice="female"):
        return self.api.post("/api/v1/voice/tts/", {"text": text, "voice": voice}, format="json")

    def test_voicelab_wav_with_configured_voice(self):
        with mock.patch("mainapp.tts.urllib.request.urlopen", return_value=http_response(WAV)) as urlopen:
            res = self.say("Qoldig'ingiz «100 000» so'm.")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "audio/wav")
        self.assertEqual(res.content, WAV)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.voicelab.uz/v1/tts")
        self.assertEqual(request.get_header("Authorization"), "Bearer vlk_test")
        body = json.loads(request.data)
        self.assertEqual((body["language"], body["voice_id"]), ("uz", "voice_madina"))
        self.assertNotIn("«", body["text"])
        self.assertRegex(request.get_header("Idempotency-key"), r"^moliya-[0-9a-f]{48}$")
        self.assertEqual(self.api.get("/api/v1/auth/me/").json()["user"]["voice_server_tts"], "voicelab")

    def test_same_text_reuses_cache_and_idempotency_key(self):
        with mock.patch("mainapp.tts.urllib.request.urlopen", return_value=http_response(WAV)) as urlopen:
            self.say("Qancha sarfladingiz?")
            self.say("Qancha sarfladingiz?")
        self.assertEqual(urlopen.call_count, 1)  # ikkinchisi keshdan — kredit sarflanmaydi

    def test_male_voice_is_picked_from_catalog(self):
        voices = {"data": [{"id": "voice_ayol", "display_name": "Madina", "description": "Ayol ovozi"},
                           {"id": "voice_erkak", "display_name": "Jasur", "description": "Erkak ovozi, iliq"}]}
        responses = [http_response(json.dumps(voices).encode()), http_response(WAV)]
        with mock.patch("mainapp.tts.urllib.request.urlopen", side_effect=responses) as urlopen:
            res = self.say("Salom", voice="male")
        self.assertEqual(res.status_code, 200)
        self.assertIn("/v1/voices?language=uz", urlopen.call_args_list[0].args[0].full_url)
        self.assertEqual(json.loads(urlopen.call_args_list[1].args[0].data)["voice_id"], "voice_erkak")

    @override_settings(AZURE_SPEECH_KEY="az-key", AZURE_SPEECH_REGION="westeurope")
    def test_out_of_credits_falls_back_to_azure_and_skips_voicelab(self):
        import urllib.error
        no_credits = urllib.error.HTTPError("u", 402, "Payment Required", {}, None)
        with mock.patch("mainapp.tts.urllib.request.urlopen", side_effect=[no_credits, http_response(b"ID3-mp3")]) as urlopen:
            res = self.say("Salom")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "audio/mpeg")
        self.assertIn("microsoft.com", urlopen.call_args_list[1].args[0].full_url)
        # Keyingi javob VoiceLab'ni so'ramaydi — to'g'ridan-to'g'ri Azure
        with mock.patch("mainapp.tts.urllib.request.urlopen", return_value=http_response(b"ID3-mp3")) as urlopen:
            self.say("Yana bir gap")
        self.assertEqual(urlopen.call_count, 1)
        self.assertIn("microsoft.com", urlopen.call_args.args[0].full_url)

    def test_queued_generation_is_not_waited_for(self):
        queued = http_response(json.dumps({"id": "gen_1", "status": "queued"}).encode(), status=202)
        with mock.patch("mainapp.tts.urllib.request.urlopen", return_value=queued):
            res = self.say("Salom")
        self.assertEqual(res.status_code, 503)  # boshqa provayder yo'q — brauzer ovozi

    @override_settings(VOICELAB_VOICE_FEMALE="")
    def test_no_voice_available_falls_back(self):
        import urllib.error
        forbidden = urllib.error.HTTPError("u", 403, "Forbidden", {}, None)
        with mock.patch("mainapp.tts.urllib.request.urlopen", side_effect=forbidden):
            res = self.say("Salom")
        self.assertEqual(res.status_code, 503)


@override_settings(ANTHROPIC_API_KEY="", OPENAI_API_KEY="", GEMINI_API_KEY="", VOICELAB_API_KEY="vlk_test")
@mock.patch("mainapp.stt.VOICELAB_POLL_SECONDS", 0)
class VoiceLabSttTests(TestCase):
    """VoiceLab nutqni tanish: yozuv yuboriladi (202), natija so'rab olinadi; xato bo'lsa keyingi provayder"""

    def setUp(self):
        cache.clear()
        offline = mock.patch("mainapp.currency._fetch_cbu", side_effect=OSError("testlarda internet ishlatilmaydi"))
        offline.start()
        self.addCleanup(offline.stop)
        self.user = User.objects.create_user(username="abdurahmon", password="Parol-12345")
        self.api = APIClient()
        self.api.force_authenticate(self.user)
        Wallet.objects.create(user=self.user, name="Naqd pul", summa=Decimal("1000000"))
        ExpenseCategory.objects.create(name="Oziq-ovqat va bozor")

    def audio(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile("voice.webm", b"x" * 4000, content_type="audio/webm")

    def post_audio(self):
        return self.api.post(API, {"audio": self.audio()}, format="multipart").json()

    def test_transcribed_by_voicelab_after_polling(self):
        responses = [http_response(json.dumps({"id": "stt_1", "status": "queued"}).encode(), status=202),
                     http_response(json.dumps({"id": "stt_1", "status": "processing"}).encode()),
                     http_response(json.dumps({"id": "stt_1", "status": "completed",
                                               "transcript": "Tushlikka 45 ming so'm sarfladim"}).encode())]
        self.assertTrue(self.api.get("/api/v1/auth/me/").json()["user"]["voice_server_stt"])
        with mock.patch("mainapp.stt.urllib.request.urlopen", side_effect=responses) as urlopen:
            out = self.post_audio()
        self.assertEqual(out["status"], "done", out)
        self.assertEqual(out["heard"], "Tushlikka 45 ming so'm sarfladim")
        self.assertEqual(Expense.objects.get().summa, Decimal("45000"))
        upload = urlopen.call_args_list[0].args[0]
        self.assertEqual(upload.full_url, "https://api.voicelab.uz/v1/stt")
        self.assertEqual(upload.get_header("Authorization"), "Bearer vlk_test")
        self.assertRegex(upload.get_header("Idempotency-key"), r"^[0-9a-f-]{36}$")
        self.assertIn(b'name="language"\r\n\r\nuz', upload.data)
        self.assertEqual(urlopen.call_args_list[2].args[0].full_url, "https://api.voicelab.uz/v1/stt/transcriptions/stt_1")

    @override_settings(GEMINI_API_KEY="gemini-key", GEMINI_MODEL="gemini-test-flash", GEMINI_FALLBACK_MODELS=[])
    def test_out_of_credits_falls_back_to_gemini(self):
        import urllib.error
        no_credits = urllib.error.HTTPError("u", 402, "Payment Required", {}, None)
        with mock.patch("mainapp.stt.urllib.request.urlopen", side_effect=no_credits), \
                mock.patch("mainapp.assistant.urllib.request.urlopen",
                           return_value=gemini_response("Tushlikka 45 ming so'm sarfladim")):
            out = self.post_audio()
        self.assertEqual(out["status"], "done", out)
        # Keyingi yozuv VoiceLab'ga umuman yuborilmaydi (bir soat chetlab o'tiladi)
        with mock.patch("mainapp.stt.urllib.request.urlopen") as voicelab, \
                mock.patch("mainapp.assistant.urllib.request.urlopen", return_value=gemini_response("qoldig'im qancha")):
            self.post_audio()
        voicelab.assert_not_called()

    @mock.patch("mainapp.stt.VOICELAB_WAIT_SECONDS", 0)
    def test_slow_result_is_not_waited_forever(self):
        pending = [http_response(json.dumps({"id": "stt_1", "status": "queued"}).encode(), status=202)] + \
                  [http_response(json.dumps({"id": "stt_1", "status": "processing"}).encode()) for _ in range(5)]
        with mock.patch("mainapp.stt.urllib.request.urlopen", side_effect=pending):
            out = self.post_audio()
        self.assertEqual(out["status"], "error")
        self.assertIn("tanib bo'lmadi", out["text"])

# Eng ko'p aytiladigan gaplar: qoidalar ularni Gemini'siz, bir zumda tushunishi kerak (ovozli javob tezligi)
COMMON_PHRASES = {
    # Qoldiq / balans
    "query_balance": ["qoldig'im qancha", "balansim qancha", "pulim qancha", "qancha pulim bor", "hisobimda qancha bor",
                      "kartamda qancha pul bor", "naqd pulim qancha", "umumiy qoldiq", "hamyonimda nechi pul bor",
                      "menda qancha pul qoldi", "pul qancha qoldi", "qancha pul qoldi", "mablag'im qancha",
                      "hisobim qancha", "kartada nima qoldi", "balans"],
    "query_spent": ["bugun qancha sarfladim", "bu oy qancha xarajat qildim", "bu hafta qancha pul ketdi",
                    "kecha qancha sarfladim", "ovqatga qancha ketdi", "bu oy qancha chiqim bo'ldi",
                    "bugungi xarajatlarim", "bu oydagi xarajatlar", "xarajatlarim qancha", "qancha pul ishlatdim",
                    "transportga qancha ketdi"],
    "query_income": ["bu oy qancha kirim bo'ldi", "qancha pul tushdi", "bu oy qancha ishlab topdim",
                     "daromadim qancha", "bu oylik kirimlarim", "kirimlarim qancha"],
    "query_debts": ["qarzlarim", "kimga qarzman", "kim menga qarz", "qarzlarim qancha", "kimdan qarzim bor",
                    "menga kim qarzdor", "qarzlar ro'yxati"],
    "query_rate": ["dollar kursi qancha", "dollar necha pul", "bugungi kurs", "yevro qancha", "rubl kursi",
                   "valyuta kurslari"],
    "query_summary": ["bugungi xulosa", "bugun nima bo'ldi", "kun xulosasi", "bu oy xulosasi", "hisobot ber",
                      "umumiy holat qanday", "ahvolim qanday"],
    "query_top": ["eng ko'p nimaga sarfladim", "pulim qayerga ketyapti", "nimaga ko'p pul ketdi",
                  "eng katta xarajat", "qaysi turkumga ko'p ketdi"],
    "query_compare": ["o'tgan oyga nisbatan qanday", "o'tgan oy bilan solishtir", "xarajatim ko'paydimi"],
    "query_goals": ["maqsadimga qancha qoldi", "jamg'armam qancha", "maqsadlarim"],
    "query_recurring": ["keyingi to'lov qachon", "doimiy to'lovlarim", "qachon to'lashim kerak"],
    # Amallar
    "expense": ["tushlikka 45 ming sarfladim", "taksiga 20 ming berdim", "non oldim 5 ming", "45 ming ovqatga ketdi",
                "bozorga 200 ming ketdi", "benzin quydim 150 ming", "telefon to'ladim 50 ming",
                "internetga 100 ming to'ladim", "shirinlikka 30 ming chiqib ketdi", "dorixonaga 80 ming",
                "kiyim oldim 300 ming", "kommunalga 250 ming to'ladim"],
    "income": ["oylik tushdi 5 million", "maosh oldim 4 million", "kartaga 1 million tushdi", "bonus oldim 500 ming",
               "500 ming ishlab topdim"],
    "transfer": ["kartadan naqdga 200 ming o'tkaz", "bankomatdan 500 ming yechdim", "200 ming naqdlashtirdim"],
    "debt_give": ["akmalga 1 million qarz berdim", "ukamga 200 ming qarz berdim"],
    "debt_take": ["akamdan 500 ming qarz oldim", "do'stimdan 1 million qarz oldim"],
    "debt_repay": ["akmal qarzini qaytardi", "qarzimni qaytardim 200 ming"],
    # Bo'limlar va boshqalar
    "nav": ["hisobotni och", "qarzlar bo'limini och", "sozlamalarni och", "bosh sahifaga o't", "kurslarni ko'rsat",
            "hamyonlarni ko'rsat", "kirimlarni och"],
    "chat": ["salom", "assalomu alaykum", "rahmat", "sen kimsan", "nima qila olasan", "soat necha", "bugun nechanchi",
             "eshityapsanmi", "yordam ber"],
    "undo/cancel": ["oxirgisini o'chir", "bekor qil", "kerak emas", "to'xta", "oxirgi amalni bekor qil"],
}


class CommonPhrasesTests(TestCase):
    def test_common_phrases_understood_by_rules(self):
        for expected, phrases in COMMON_PHRASES.items():
            for phrase in phrases:
                with self.subTest(phrase=phrase):
                    got = vp.detect_intent(vp.strip_wake(vp.loose(phrase)))
                    if expected == "nav":
                        self.assertTrue(got and got.startswith("nav_"), got)
                    elif expected == "chat":
                        self.assertTrue(got and got.startswith("chat_"), got)
                    elif expected == "undo/cancel":
                        self.assertIn(got, ("undo", "cancel"))
                    else:
                        self.assertEqual(got, expected)


@override_settings(VOICELAB_API_KEY="vlk_test", VOICELAB_VOICE_FEMALE="voice_madina", VOICELAB_VOICE_MALE="voice_sardor",
                   AZURE_SPEECH_KEY="", OPENAI_API_KEY="")
class VoiceWarmupTests(TestCase):
    """Doimiy gaplar oldindan ovozga aylantiriladi: keyin brauzer so'rasa VoiceLab'ga murojaat qilinmaydi"""

    def setUp(self):
        cache.clear()

    def test_phrases_match_what_the_assistant_says(self):
        from . import voice
        phrases = voice.warmup_phrases()
        for phrase in ("Qancha sarfladingiz?", "Bu kirimmi yoki chiqim?", voice.OFF_TOPIC, "Tushunmadim.", "Ha?"):
            self.assertIn(phrase, phrases)
        self.assertIn("Ha, Abdurahmon?", voice.warmup_phrases("Abdurahmon"))

    def test_warmed_phrase_is_served_from_cache(self):
        from django.core.management import call_command
        from io import StringIO
        with mock.patch("mainapp.tts.urllib.request.urlopen", return_value=http_response(WAV)) as urlopen:
            call_command("voice_warmup", "--gender", "female", stdout=StringIO())
        self.assertGreater(urlopen.call_count, 10)
        user = User.objects.create_user(username="abdurahmon", password="Parol-12345")
        api = APIClient()
        api.force_authenticate(user)
        with mock.patch("mainapp.tts.urllib.request.urlopen") as urlopen:
            res = api.post("/api/v1/voice/tts/", {"text": "Qancha sarfladingiz?", "voice": "female"}, format="json")
        self.assertEqual(res.status_code, 200)
        urlopen.assert_not_called()

    def test_dry_run_spends_nothing(self):
        from django.core.management import call_command
        from io import StringIO
        out = StringIO()
        with mock.patch("mainapp.tts.urllib.request.urlopen") as urlopen:
            call_command("voice_warmup", "--dry-run", stdout=out)
        urlopen.assert_not_called()
        self.assertIn("Qancha sarfladingiz?", out.getvalue())
