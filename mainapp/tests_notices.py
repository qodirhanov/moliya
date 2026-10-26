"""Admin xabarlari: admin panelidan bitta foydalanuvchiga yoki hammaga yuborish va ilovadagi qo'ng'iroq API'si"""
from datetime import timedelta

from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from .models import AdminNotice, AdminNoticeRead, User

API = "/api/v1"
PASSWORD = "Parol-12345"


class NoticeBase(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="ali", password=PASSWORD)
        self.other = User.objects.create_user(username="vali", password=PASSWORD)
        self.api = APIClient()
        self.api.force_authenticate(self.user)
        self.staff = User.objects.create_user(username="admin1", password=PASSWORD, is_staff=True)
        self.staff.user_permissions.add(Permission.objects.get(codename="view_user"))


class NoticeApiTests(NoticeBase):
    def test_user_sees_own_and_broadcast_only(self):
        AdminNotice.objects.create(author=self.staff, recipient=self.user, text="Sizga")
        AdminNotice.objects.create(author=self.staff, recipient=self.other, text="Begona")
        AdminNotice.objects.create(author=self.staff, text="Hammaga")
        data = self.api.get(f"{API}/notices/").json()
        self.assertEqual([n["text"] for n in data["notices"]], ["Hammaga", "Sizga"])
        self.assertEqual([n["broadcast"] for n in data["notices"]], [True, False])
        self.assertEqual(data["unread"], 2)
        self.assertEqual(self.api.get(f"{API}/auth/me/").json()["user"]["notices_unread"], 2)
        self.assertEqual(self.api.get(f"{API}/support/unread/").json()["notices_unread"], 2)

    def test_broadcast_before_signup_hidden(self):
        old = AdminNotice.objects.create(author=self.staff, text="Eski e'lon")
        AdminNotice.objects.filter(pk=old.pk).update(created_at=self.user.date_joined - timedelta(days=1))
        self.assertEqual(self.api.get(f"{API}/notices/").json()["notices"], [])

    def test_mark_read_per_user(self):
        AdminNotice.objects.create(author=self.staff, text="Hammaga")
        self.assertEqual(self.api.post(f"{API}/notices/read/").status_code, 200)
        self.api.post(f"{API}/notices/read/")  # takroriy chaqiruv xato bermaydi
        data = self.api.get(f"{API}/notices/").json()
        self.assertEqual(data["unread"], 0)
        self.assertTrue(data["notices"][0]["is_read"])
        other = APIClient()
        other.force_authenticate(self.other)
        self.assertEqual(other.get(f"{API}/notices/").json()["unread"], 1)

    def test_old_read_notices_drop_off_unread_stay(self):
        read = AdminNotice.objects.create(author=self.staff, recipient=self.user, text="O'qilgan")
        unread = AdminNotice.objects.create(author=self.staff, recipient=self.user, text="O'qilmagan")
        AdminNoticeRead.objects.create(notice=read, user=self.user)
        AdminNotice.objects.update(created_at=timezone.now() - timedelta(days=40))
        self.assertEqual([n["id"] for n in self.api.get(f"{API}/notices/").json()["notices"]], [unread.id])

    def test_requires_login(self):
        self.assertIn(APIClient().get(f"{API}/notices/").status_code, (401, 403))


class PanelNoticeTests(NoticeBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.staff)
        self.url = reverse("panel-notices")

    def test_send_to_all(self):
        res = self.client.post(self.url, {"target": "all", "text": "  Yangilanish  "})
        self.assertRedirects(res, f"{self.url}?sent=1")
        n = AdminNotice.objects.get()
        self.assertIsNone(n.recipient)
        self.assertEqual((n.text, n.author), ("Yangilanish", self.staff))

    def test_send_to_one_user_by_login(self):
        self.client.post(self.url, {"target": "user", "to": "@ALI", "text": "Salom"})
        self.assertEqual(AdminNotice.objects.get().recipient, self.user)

    def test_errors_keep_draft(self):
        res = self.client.post(self.url, {"target": "user", "to": "yoq", "text": "Matn"})
        self.assertContains(res, "@yoq topilmadi")
        self.assertContains(res, "Matn")
        res = self.client.post(self.url, {"target": "all", "text": "  "})
        self.assertContains(res, "Xabar yozing")
        self.assertFalse(AdminNotice.objects.exists())

    def test_list_and_delete(self):
        n = AdminNotice.objects.create(author=self.staff, text="Hammaga xabar")
        AdminNoticeRead.objects.create(notice=n, user=self.user)
        res = self.client.get(self.url)
        self.assertContains(res, "Hammaga xabar")
        self.assertContains(res, "1 / 3 o'qidi")
        self.assertEqual(self.client.get(reverse("panel-notice-delete", args=[n.pk])).status_code, 404)
        self.client.post(reverse("panel-notice-delete", args=[n.pk]))
        self.assertFalse(AdminNotice.objects.exists())

    def test_prefill_from_account_page(self):
        res = self.client.get(f"{self.url}?to=ali")
        self.assertContains(res, 'value="ali"')
        self.assertContains(res, 'value="user" checked')

    def test_hidden_from_non_staff(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url, {"target": "all", "text": "x"}).status_code, 404)
        self.assertFalse(AdminNotice.objects.exists())
