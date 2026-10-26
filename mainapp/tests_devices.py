from datetime import timedelta

from django.contrib.sessions.models import Session
from django.utils import timezone
from rest_framework.test import APIClient

from .devices import describe_device
from .models import UserDevice
from .tests import API, PASSWORD, APITestCase, make_user

PHONE_UA = "Mozilla/5.0 (Linux; Android 14; SM-A546E) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Mobile Safari/537.36"
LAPTOP_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36"


class DeviceTests(APITestCase):
    """Sozlamalar → Qurilmalar: ro'yxat, bitta yoki boshqa barcha qurilmalarni chiqarish, 15 kunlik qoida"""

    def setUp(self):
        super().setUp()
        self.user = make_user("ali")

    def login(self, ua=LAPTOP_UA, username="ali"):
        client = APIClient(HTTP_USER_AGENT=ua)
        res = client.post(f"{API}/auth/login/", {"username": username, "password": PASSWORD}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        return client

    def devices(self, client):
        res = client.get(f"{API}/auth/devices/")
        self.assertEqual(res.status_code, 200, res.content)
        return res.json()

    def age_current(self, client, days):
        """Joriy qurilmada kirish vaqtini orqaga suradi"""
        key = client.cookies["sessionid"].value
        UserDevice.objects.filter(session_key=key).update(created_at=timezone.now() - timedelta(days=days))

    def signed_in(self, client):
        return client.get(f"{API}/auth/me/").json()["authenticated"]

    def test_login_registers_device_with_time_ip_and_name(self):
        laptop = self.login()
        data = self.devices(laptop)
        self.assertEqual(len(data["devices"]), 1)
        device = data["devices"][0]
        self.assertTrue(device["current"])
        self.assertEqual((device["browser"], device["os"], device["kind"]), ("Chrome 141", "Windows", "desktop"))
        self.assertTrue(device["ip"])
        self.assertTrue(device["created_at"])
        self.assertEqual(data["min_days"], 15)
        self.assertFalse(data["can_terminate"])

    def test_lists_every_device_current_first(self):
        laptop, phone = self.login(), self.login(PHONE_UA)
        data = self.devices(phone)
        self.assertEqual(len(data["devices"]), 2)
        self.assertTrue(data["devices"][0]["current"])
        self.assertEqual(data["devices"][0]["kind"], "mobile")

    def test_other_users_devices_are_hidden(self):
        make_user("vali")
        self.login(username="vali")
        self.assertEqual(len(self.devices(self.login())["devices"]), 1)

    def test_cannot_terminate_before_15_days(self):
        laptop, phone = self.login(), self.login(PHONE_UA)
        self.age_current(laptop, 14)
        phone_id = next(d["id"] for d in self.devices(phone)["devices"] if d["current"])
        res = laptop.post(f"{API}/auth/devices/{phone_id}/terminate/")
        self.assertEqual(res.status_code, 403)
        self.assertIn("15 kun", res.json()["error"])
        self.assertEqual(laptop.post(f"{API}/auth/devices/terminate-others/").status_code, 403)
        self.assertTrue(self.signed_in(phone))

    def test_new_device_cannot_kick_the_old_one(self):
        """O'g'irlangan (yangi) sessiya egasining eski qurilmasini chiqara olmaydi"""
        owner, intruder = self.login(), self.login(PHONE_UA)
        self.age_current(owner, 30)
        owner_id = next(d["id"] for d in self.devices(owner)["devices"] if d["current"])
        self.assertEqual(intruder.post(f"{API}/auth/devices/{owner_id}/terminate/").status_code, 403)
        self.assertTrue(self.signed_in(owner))

    def test_terminate_one_device_after_15_days(self):
        laptop, phone, tablet = self.login(), self.login(PHONE_UA), self.login()
        self.age_current(laptop, 15)
        self.assertTrue(self.devices(laptop)["can_terminate"])
        phone_id = next(d["id"] for d in self.devices(phone)["devices"] if d["current"])
        res = laptop.post(f"{API}/auth/devices/{phone_id}/terminate/")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertFalse(self.signed_in(phone))
        self.assertEqual(phone.get(f"{API}/wallets/").status_code, 401)
        self.assertTrue(self.signed_in(tablet))
        self.assertEqual(len(self.devices(laptop)["devices"]), 2)

    def test_terminate_others_keeps_current(self):
        laptop, phone, tablet = self.login(), self.login(PHONE_UA), self.login()
        self.age_current(laptop, 20)
        res = laptop.post(f"{API}/auth/devices/terminate-others/")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["count"], 2)
        self.assertTrue(self.signed_in(laptop))
        self.assertFalse(self.signed_in(phone) or self.signed_in(tablet))
        self.assertEqual(len(self.devices(laptop)["devices"]), 1)

    def test_current_device_is_not_terminated_via_list(self):
        laptop = self.login()
        self.age_current(laptop, 20)
        my_id = self.devices(laptop)["devices"][0]["id"]
        self.assertEqual(laptop.post(f"{API}/auth/devices/{my_id}/terminate/").status_code, 400)
        self.assertTrue(self.signed_in(laptop))

    def test_cannot_terminate_someone_elses_device(self):
        make_user("vali")
        stranger = self.login(username="vali")
        their_id = self.devices(stranger)["devices"][0]["id"]
        mine = self.login()
        self.age_current(mine, 20)
        self.assertEqual(mine.post(f"{API}/auth/devices/{their_id}/terminate/").status_code, 404)
        self.assertTrue(self.signed_in(stranger))

    def test_logout_removes_device(self):
        laptop, phone = self.login(), self.login(PHONE_UA)
        phone.post(f"{API}/auth/logout/")
        self.assertEqual(len(self.devices(laptop)["devices"]), 1)

    def test_password_change_drops_other_devices_and_keeps_login_time(self):
        laptop, phone = self.login(), self.login(PHONE_UA)
        self.age_current(laptop, 20)
        res = laptop.post(f"{API}/auth/change-password/",
                          {"old_password": PASSWORD, "new_password": "Yangi-parol-2026"}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        data = self.devices(laptop)
        self.assertEqual(len(data["devices"]), 1)
        self.assertTrue(data["devices"][0]["current"])
        # Sessiya kaliti almashdi, lekin asl kirish vaqti saqlandi — 15 kunlik qoida qayta boshlanmaydi
        self.assertTrue(data["can_terminate"])

    def test_session_without_device_row_is_picked_up(self):
        """Bu imkoniyatdan oldin ochilgan sessiya birinchi so'rovda ro'yxatga tushadi"""
        laptop = self.login()
        UserDevice.objects.all().delete()
        self.assertEqual(len(self.devices(laptop)["devices"]), 1)

    def test_logout_all_empties_the_list(self):
        laptop, phone = self.login(), self.login(PHONE_UA)
        laptop.post(f"{API}/auth/logout-all/")
        fresh = self.login()
        self.assertEqual(len(self.devices(fresh)["devices"]), 1)
        self.assertEqual(Session.objects.count(), 1)

    def test_requires_login(self):
        self.assertIn(APIClient().get(f"{API}/auth/devices/").status_code, (401, 403))

    def test_describe_device(self):
        self.assertEqual(describe_device("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
                                         "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"),
                         {"browser": "Safari 18", "os": "iPhone", "kind": "mobile"})
        self.assertEqual(describe_device(LAPTOP_UA.replace("Safari/537.36", "Safari/537.36 Edg/141.0"))["browser"],
                         "Edge 141")
        self.assertEqual(describe_device(""), {"browser": "", "os": "", "kind": "desktop"})
