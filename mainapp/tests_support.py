"""Sozlamalar → Yordam (admin bilan chat), admin panelidagi javoblar va AI yordamchi.
Claude API har doim mock: testlarda haqiqiy so'rov yuborilmaydi"""
import http.client
import io
import json
import urllib.error
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth.models import Permission
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from . import assistant, faq
from .models import SupportMessage, User

API = "/api/v1"
PASSWORD = "Parol-12345"


class SupportBase(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="ali", password=PASSWORD)
        self.other = User.objects.create_user(username="vali", password=PASSWORD)
        self.api = APIClient()
        self.api.force_authenticate(self.user)
        self.staff = User.objects.create_user(username="admin1", password=PASSWORD, is_staff=True)
        self.staff.user_permissions.add(Permission.objects.get(codename="view_user"))


class SupportApiTests(SupportBase):
    def test_send_and_list_own_messages_only(self):
        res = self.api.post(f"{API}/support/messages/", {"text": "  Salom, yordam kerak  "}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["text"], "Salom, yordam kerak")
        SupportMessage.objects.create(user=self.other, text="Begona xabar")

        data = self.api.get(f"{API}/support/messages/").json()
        self.assertEqual([m["text"] for m in data["messages"]], ["Salom, yordam kerak"])

    def test_empty_and_too_long_rejected(self):
        self.assertEqual(self.api.post(f"{API}/support/messages/", {"text": "   "}, format="json").status_code, 400)
        long_text = "a" * (SupportMessage.MAX_LENGTH + 1)
        self.assertEqual(self.api.post(f"{API}/support/messages/", {"text": long_text}, format="json").status_code, 400)
        self.assertFalse(SupportMessage.objects.exists())

    def test_after_returns_only_new_and_marks_admin_replies_read(self):
        first = SupportMessage.objects.create(user=self.user, text="Savol")
        reply = SupportMessage.objects.create(user=self.user, text="Javob", from_admin=True, author=self.staff)
        self.assertEqual(self.api.get(f"{API}/auth/me/").json()["user"]["support_unread"], 1)
        self.assertEqual(self.api.get(f"{API}/support/unread/").json()["unread"], 1)

        data = self.api.get(f"{API}/support/messages/?after={first.id}").json()
        self.assertEqual([m["id"] for m in data["messages"]], [reply.id])
        self.assertTrue(data["messages"][0]["from_admin"])
        self.assertEqual(self.api.get(f"{API}/support/unread/").json()["unread"], 0)

    def test_requires_login(self):
        anon = APIClient()
        self.assertEqual(anon.get(f"{API}/support/messages/").status_code, 401)
        self.assertEqual(anon.post(f"{API}/assistant/", {}, format="json").status_code, 401)


class SupportPanelTests(SupportBase):
    def setUp(self):
        super().setUp()
        self.web = self.client
        self.web.force_login(self.staff)
        self.inbox = reverse("panel-support")
        self.thread = reverse("panel-support-thread", args=[self.user.pk])

    def test_regular_user_gets_404(self):
        self.web.force_login(self.user)
        self.assertEqual(self.web.get(self.inbox).status_code, 404)
        self.assertEqual(self.web.post(self.thread, {"text": "x"}).status_code, 404)
        self.assertFalse(SupportMessage.objects.exists())

    def test_inbox_lists_unread_first(self):
        SupportMessage.objects.create(user=self.other, text="Eski", is_read=True)
        SupportMessage.objects.create(user=self.user, text="Yangi savol")
        res = self.web.get(self.inbox)
        self.assertEqual(res.status_code, 200)
        threads = list(res.context["page"])
        self.assertEqual([u.pk for u in threads], [self.user.pk, self.other.pk])
        self.assertEqual(threads[0].unread, 1)
        self.assertEqual(res.context["unread_total"], 1)

    def test_open_thread_marks_read_and_reply_reaches_user(self):
        SupportMessage.objects.create(user=self.user, text="Savol")
        self.assertEqual(self.web.get(self.thread).status_code, 200)
        self.assertFalse(SupportMessage.objects.filter(from_admin=False, is_read=False).exists())

        res = self.web.post(self.thread, {"text": "Javobimiz"})
        self.assertRedirects(res, self.thread)
        reply = SupportMessage.objects.get(from_admin=True)
        self.assertEqual((reply.user, reply.author, reply.text), (self.user, self.staff, "Javobimiz"))
        self.assertEqual(self.api.get(f"{API}/support/unread/").json()["unread"], 1)

    def test_empty_reply_shows_error(self):
        res = self.web.post(self.thread, {"text": "  "})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.context["error"])
        self.assertFalse(SupportMessage.objects.exists())

    def test_poll_returns_new_user_messages(self):
        first = SupportMessage.objects.create(user=self.user, text="Bir")
        second = SupportMessage.objects.create(user=self.user, text="Ikki")
        data = self.web.get(reverse("panel-support-poll", args=[self.user.pk]), {"after": first.id}).json()
        self.assertEqual([m["id"] for m in data["messages"]], [second.id])
        second.refresh_from_db()
        self.assertTrue(second.is_read)


def fake_response(text="Hamyonlar bo'limida qo'shish tugmasini bosing.", stop_reason="end_turn"):
    return SimpleNamespace(stop_reason=stop_reason, content=[SimpleNamespace(type="text", text=text)])


class AssistantTests(SupportBase):
    @override_settings(ANTHROPIC_API_KEY="", GEMINI_API_KEY="")
    def test_free_mode_answers_from_help_without_api(self):
        with mock.patch.object(assistant, "_client") as client:
            res = self.api.post(f"{API}/assistant/", {"messages": [
                {"role": "user", "content": "Salom"},
                {"role": "assistant", "content": "..."},
                {"role": "user", "content": "hamyonni qanday o'chiraman"},
            ]}, format="json")
        client.assert_not_called()
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["answer"].startswith("Hamyonlar: Hamyonni qanday o'chiraman?"))

    @override_settings(ANTHROPIC_API_KEY="test-key", GEMINI_API_KEY="gemini-key")
    def test_answer_uses_grounded_system_prompt(self):
        with mock.patch.object(assistant, "_client") as client:
            client.return_value.beta.messages.create.return_value = fake_response()
            res = self.api.post(f"{API}/assistant/", {"messages": [
                {"role": "assistant", "content": "kesilgan tarixdan qolgan"},
                {"role": "user", "content": "Hamyonni qanday qo'shaman?"},
            ]}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Hamyonlar", res.json()["answer"])
        kwargs = client.return_value.beta.messages.create.call_args.kwargs
        self.assertEqual(kwargs["model"], assistant.MODEL)
        self.assertIn("Hamyon nima?", kwargs["system"][0]["text"])
        # Yordamchi o'zini ilova nomi bilan tanishtiradi, model/kompaniyani aytmaydi
        self.assertIn("Moliya yordamchisi", kwargs["system"][0]["text"])
        self.assertEqual(set(res.json()), {"answer"})
        # Tarix user xabari bilan boshlanadi
        self.assertEqual(kwargs["messages"], [{"role": "user", "content": "Hamyonni qanday qo'shaman?"}])

    @override_settings(ANTHROPIC_API_KEY="test-key")
    def test_refusal_and_bad_input(self):
        with mock.patch.object(assistant, "_client") as client:
            client.return_value.beta.messages.create.return_value = fake_response("", stop_reason="refusal")
            res = self.api.post(f"{API}/assistant/", {"messages": [{"role": "user", "content": "?"}]}, format="json")
        self.assertEqual(res.json()["answer"], assistant.REFUSED_MESSAGE)
        for bad in (None, [], [{"role": "system", "content": "x"}], [{"role": "user", "content": "a" * 1001}]):
            res = self.api.post(f"{API}/assistant/", {"messages": bad}, format="json")
            self.assertEqual(res.status_code, 400, bad)


class FakeHttpResponse:
    def __init__(self, payload):
        self.body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def gemini_payload(text="Hamyonlar bo'limida «+ Qo'shish» ni bosing.", finish="STOP"):
    return {"candidates": [{"content": {"role": "model", "parts": [{"text": text}]}, "finishReason": finish}]}


@override_settings(ANTHROPIC_API_KEY="", GEMINI_API_KEY="gemini-test-key", GEMINI_MODEL="gemini-test-flash")
class GeminiAssistantTests(SupportBase):
    """Gemini REST API tarmoqsiz (urlopen mock) tekshiriladi"""

    def post(self, messages):
        return self.api.post(f"{API}/assistant/", {"messages": messages}, format="json")

    def test_request_shape_and_answer(self):
        with mock.patch("mainapp.assistant.urllib.request.urlopen", return_value=FakeHttpResponse(gemini_payload())) as urlopen:
            res = self.post([
                {"role": "user", "content": "Salom"},
                {"role": "assistant", "content": "Salom! Qanday yordam beray?"},
                {"role": "user", "content": "Hamyonni qanday qo'shaman?"},
            ])
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json(), {"answer": "Hamyonlar bo'limida «+ Qo'shish» ni bosing."})
        request = urlopen.call_args.args[0]
        self.assertIn("/models/gemini-test-flash:generateContent", request.full_url)
        # Kalit URL da emas, sarlavhada
        self.assertNotIn("gemini-test-key", request.full_url)
        self.assertEqual(request.get_header("X-goog-api-key"), "gemini-test-key")
        body = json.loads(request.data)
        self.assertIn("Moliya yordamchisi", body["systemInstruction"]["parts"][0]["text"])
        self.assertIn("Hamyon nima?", body["systemInstruction"]["parts"][0]["text"])
        self.assertEqual([c["role"] for c in body["contents"]], ["user", "model", "user"])
        self.assertEqual(body["contents"][-1]["parts"][0]["text"], "Hamyonni qanday qo'shaman?")

    def test_thought_parts_are_hidden(self):
        payload = {"candidates": [{"finishReason": "STOP", "content": {"parts": [
            {"text": "ichki o'ylash", "thought": True}, {"text": "Tayyor javob"}]}}]}
        with mock.patch("mainapp.assistant.urllib.request.urlopen", return_value=FakeHttpResponse(payload)):
            res = self.post([{"role": "user", "content": "?"}])
        self.assertEqual(res.json()["answer"], "Tayyor javob")

    def test_blocked_answer_is_refusal(self):
        for payload in (gemini_payload("", finish="SAFETY"), {"promptFeedback": {"blockReason": "SAFETY"}}):
            with mock.patch("mainapp.assistant.urllib.request.urlopen", return_value=FakeHttpResponse(payload)):
                res = self.post([{"role": "user", "content": "?"}])
            self.assertEqual(res.json()["answer"], assistant.REFUSED_MESSAGE, payload)

    def test_api_errors_give_friendly_502(self):
        errors = [
            urllib.error.HTTPError("u", 429, "Too Many Requests", {}, io.BytesIO(b"{}")),
            urllib.error.HTTPError("u", 400, "API_KEY_INVALID", {}, io.BytesIO(b"{}")),
            urllib.error.URLError("timeout"),
            http.client.IncompleteRead(b"{"),
        ]
        for error in errors:
            with mock.patch("mainapp.assistant.urllib.request.urlopen", side_effect=error):
                res = self.post([{"role": "user", "content": "?"}])
            self.assertEqual(res.status_code, 502, error)
            self.assertEqual(res.json()["error"], assistant.FAILED_MESSAGE)
        with mock.patch("mainapp.assistant.urllib.request.urlopen", return_value=FakeHttpResponse(["not", "dict"])):
            self.assertEqual(self.post([{"role": "user", "content": "?"}]).status_code, 502)

    @override_settings(ANTHROPIC_API_KEY="claude-key")
    def test_claude_key_takes_priority(self):
        self.assertEqual(assistant.provider(), "anthropic")
        with override_settings(ANTHROPIC_API_KEY="", GEMINI_API_KEY=""):
            self.assertIsNone(assistant.provider())
            self.assertFalse(assistant.is_enabled())


class FaqSearchTests(TestCase):
    """Bepul rejim: savolning turli shakllari (qo'shimcha, sinonim, kirill yozuv) to'g'ri javobga olib keladi"""
    def first_line(self, question):
        return faq.answer(question).splitlines()[0]

    def test_word_forms_synonyms_and_cyrillic(self):
        cases = {
            "hamyonni qanday o'chiraman": "Hamyonni qanday o'chiraman?",
            "chiqimni qanday yozaman": "Chiqimni qanday yozaman?",
            "qarzni qisman qaytarsa boladimi": "Qarzni qisman qaytarsa bo'ladimi?",
            "tilni o‘zgartirish": "Ilova tilini qanday almashtiraman?",
            "doimiy to'lov qo'shish": "Qanday qo'shaman?",
            "turkum qo'shish": "Turkumlarni qayerda sozlayman?",
            "балансни яшириш": "Qoldiqni qanday yashiraman?",
        }
        for question, expected in cases.items():
            self.assertIn(expected, self.first_line(question), question)

    def test_unrelated_greeting_and_thanks(self):
        self.assertEqual(faq.answer("python dasturlash"), faq.NOT_FOUND_MESSAGE)
        self.assertEqual(faq.answer("Assalomu alaykum"), faq.GREETING_MESSAGE)
        self.assertEqual(faq.answer("rahmat!"), faq.THANKS_MESSAGE)

    def test_short_question_gets_topic_prefix(self):
        self.assertEqual(self.first_line("doimiy to'lov qo'shish"), "Doimiy to'lovlar: Qanday qo'shaman?")


class SupportEmailTests(SupportBase):
    """Yordamga yangi xabar — adminga xat (testlarda MAIL_IN_BACKGROUND=False, xat mail.outbox ga tushadi)"""
    def setUp(self):
        super().setUp()
        self.staff.email = "admin1@example.com"
        self.staff.save()
        # Ruxsatsiz xodim va oddiy foydalanuvchi xat olmaydi
        User.objects.create_user(username="xodim2", password=PASSWORD, is_staff=True, email="xodim2@example.com")
        self.other.email = "vali@example.com"
        self.other.save()

    def send(self, text):
        return self.api.post(f"{API}/support/messages/", {"text": text}, format="json")

    def test_first_message_emails_panel_admins_with_link(self):
        self.send("<b>Yordam</b> kerak")
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ["admin1@example.com"])
        self.assertIn("<b>Yordam</b> kerak", msg.body)
        self.assertIn(reverse("panel-support-thread", args=[self.user.pk]), msg.body)
        html = msg.alternatives[0][0]
        self.assertIn("&lt;b&gt;Yordam&lt;/b&gt;", html)  # foydalanuvchi matni ekranlangan

    def test_no_repeat_until_admin_reads(self):
        self.send("Birinchi")
        self.send("Ikkinchi")
        self.assertEqual(len(mail.outbox), 1)
        SupportMessage.objects.filter(user=self.user).update(is_read=True)
        self.send("Uchinchi")
        self.assertEqual(len(mail.outbox), 2)

    @override_settings(SUPPORT_NOTIFY_EMAILS=["help@example.com"])
    def test_env_recipients_override(self):
        self.send("Salom")
        self.assertEqual(mail.outbox[0].to, ["help@example.com"])

    def test_mail_failure_does_not_break_sending(self):
        with mock.patch("mainapp.support.send_mail", side_effect=OSError("SMTP yo'q")):
            res = self.send("Salom")
        self.assertEqual(res.status_code, 201)
        self.assertTrue(SupportMessage.objects.filter(text="Salom").exists())
