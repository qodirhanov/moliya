"""plans.md №3: foydalanuvchi nomlari katta-kichik harfga qaramasdan noyob — kirill harflari (Али/али, ЖАСУР/жасур) uchun ham.
SQLite lower()/iexact faqat ASCII'ni tushiradi, shuning uchun noyoblik va qidiruv username_key (NFKC + casefold) bo'yicha"""
import importlib
from unittest import mock

from django.apps import apps as django_apps
from django.contrib.auth.models import Permission
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse
from rest_framework.test import APIClient

from .backends import _login_keys, find_user_by_login
from .models import USERNAME_TAKEN_MESSAGE, User
from .tests import API, PASSWORD, APITestCase, make_user, post_login

fill_migration = importlib.import_module("mainapp.migrations.0018_fill_username_key")


def key_of(user):
    """Bazadagi haqiqiy kalit (xotiradagi nusxa emas)"""
    return User.objects.values_list("username_key", flat=True).get(pk=user.pk)


def register(username):
    return APIClient().post(f"{API}/auth/register/", {"username": username, "password": PASSWORD}, format="json")


class CyrillicUniquenessTests(APITestCase):
    def test_register_rejects_case_variants_of_cyrillic_name(self):
        make_user("али")
        for name in ("АЛИ", "Али", "аЛи"):
            with self.subTest(name=name):
                res = register(name)
                self.assertEqual(res.status_code, 400, res.content)
                self.assertEqual(res.json()["error"], USERNAME_TAKEN_MESSAGE)
        self.assertEqual(User.objects.count(), 1)

    def test_register_second_variant_after_first_succeeds(self):
        self.assertEqual(register("ЖАСУР").status_code, 201)
        res = register("жасур")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["error"], "Bu foydalanuvchi nomi allaqachon band")
        self.assertEqual(User.objects.count(), 1)

    def test_different_cyrillic_names_are_independent(self):
        make_user("али")
        self.assertEqual(register("вали").status_code, 201)

    def test_model_level_duplicate_is_rejected_by_database(self):
        make_user("Али")
        for name in ("али", "АЛИ"):
            with self.subTest(name=name), self.assertRaises(IntegrityError), transaction.atomic():
                User.objects.create_user(username=name, password=PASSWORD)
        self.assertEqual(User.objects.count(), 1)

    def test_clean_reports_taken_name_but_not_own_name(self):
        ali = make_user("Али")
        with self.assertRaises(ValidationError) as ctx:
            User(username="АЛИ").clean()
        self.assertEqual(ctx.exception.message_dict, {"username": [USERNAME_TAKEN_MESSAGE]})
        ali.username = "АЛИ"  # o'z nomining harf kattaligini o'zgartirish xato emas
        ali.clean()

    def test_profile_rename_to_case_variant_of_other_cyrillic_name_is_rejected(self):
        make_user("жасур")
        ali = make_user("ali")
        self.login_as(ali)
        res = self.api.patch(f"{API}/auth/profile/", {"username": "ЖАСУР"}, format="json")
        self.assertEqual(res.status_code, 400, res.content)
        self.assertEqual(res.json()["username"], USERNAME_TAKEN_MESSAGE)
        ali.refresh_from_db()
        self.assertEqual((ali.username, key_of(ali)), ("ali", "ali"))

    def test_profile_rename_changing_only_case_of_own_name_is_allowed(self):
        ali = make_user("али")
        self.login_as(ali)
        res = self.api.patch(f"{API}/auth/profile/", {"username": "АЛИ"}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        ali.refresh_from_db()
        self.assertEqual((ali.username, key_of(ali)), ("АЛИ", "али"))

    def test_users_endpoint_rejects_cyrillic_case_variant(self):
        make_user("али")
        self.login_as(make_user("root", is_staff=True, is_superuser=True))
        res = self.api.post(f"{API}/users/", {"username": "АЛИ", "password": PASSWORD}, format="json")
        self.assertEqual(res.status_code, 400, res.content)
        self.assertEqual(User.objects.filter(username_key="али").count(), 1)

    def test_register_race_returns_friendly_400_not_500(self):
        """Ikki so'rov tekshiruvdan birga o'tib ketdi: ikkinchisini baza (username_key unique) to'xtatadi"""
        make_user("али")
        with mock.patch("mainapp.views.username_error", return_value=None):
            res = register("АЛИ")
        self.assertEqual(res.status_code, 400, res.content)
        self.assertEqual(res.json()["error"], USERNAME_TAKEN_MESSAGE)
        self.assertEqual(User.objects.count(), 1)

    def test_profile_rename_race_returns_friendly_400_not_500(self):
        make_user("жасур")
        ali = make_user("ali")
        self.login_as(ali)
        with mock.patch("mainapp.views.username_error", return_value=None):
            res = self.api.patch(f"{API}/auth/profile/", {"username": "ЖАСУР"}, format="json")
        self.assertEqual(res.status_code, 400, res.content)
        self.assertEqual(res.json()["username"], USERNAME_TAKEN_MESSAGE)
        ali.refresh_from_db()
        self.assertEqual((ali.username, key_of(ali)), ("ali", "ali"))

    def test_email_equal_to_cyrillic_username_is_taken_case_insensitively(self):
        ali = make_user("али")
        self.assertTrue(User.email_taken("АЛИ"))
        self.assertTrue(User.email_taken("Али"))
        self.assertFalse(User.email_taken("АЛИ", exclude_pk=ali.pk))
        self.assertFalse(User.email_taken("вали"))


class CyrillicLoginTests(APITestCase):
    def test_login_is_case_insensitive_for_cyrillic(self):
        make_user("али")
        for name in ("али", "АЛИ", "Али"):
            with self.subTest(name=name):
                self.assertEqual(post_login(self.api, PASSWORD, username=name).status_code, 200)

    def test_find_user_by_login_matches_cyrillic_and_fullwidth(self):
        ali = make_user("Али")
        vali = make_user("vali")
        self.assertEqual(find_user_by_login("АЛИ"), ali)
        self.assertEqual(find_user_by_login("  али "), ali)
        self.assertEqual(find_user_by_login("ＶＡＬＩ"), vali)  # ＶＡＬＩ
        self.assertIsNone(find_user_by_login("жасур"))

    def test_lockout_counters_are_shared_between_case_variants(self):
        ali = make_user("али")
        self.assertEqual(_login_keys("АЛИ", None), _login_keys("али", None))
        for _ in range(4):
            post_login(self.api, "xato", username="АЛИ")
        self.assertEqual(post_login(self.api, "xato", username="али").status_code, 429)
        self.assertEqual(post_login(self.api, PASSWORD, username="Али").status_code, 429)
        # akkaunt bo'yicha hisoblagich egasining id'siga bog'langan
        self.assertEqual(_login_keys("АЛИ", None)[1], f"login_fail:user:{ali.pk}")

    def test_lockout_key_for_unknown_name_is_shared_too(self):
        self.assertEqual(_login_keys("ЖАСУР", None), _login_keys("жасур", None))
        self.assertNotEqual(_login_keys("жасур", None), _login_keys("вали", None))

    def test_password_reset_finds_cyrillic_name_by_any_case(self):
        make_user("али", email="ali@example.com")
        cache.clear()
        res = self.api.post(f"{API}/auth/password-reset/", {"username": "АЛИ"}, format="json",
                            REMOTE_ADDR="203.0.113.9")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(len(mail.outbox), 1)


class UsernameKeySyncTests(APITestCase):
    def test_create_user_and_superuser_set_key(self):
        self.assertEqual(key_of(make_user("Али")), "али")
        root = User.objects.create_superuser(username="ЖАСУР", password=PASSWORD)
        self.assertEqual(key_of(root), "жасур")
        self.assertEqual(key_of(make_user("ＡＤＭＩＮ")), "admin")  # ＡＤＭＩＮ

    def test_key_follows_rename_via_save(self):
        user = make_user("али")
        user.username = "ВАЛИ"
        user.save()
        self.assertEqual(key_of(user), "вали")

    def test_key_follows_rename_via_update_fields(self):
        user = make_user("али")
        for update_fields in (["username"], ("username",), frozenset({"username"})):
            with self.subTest(update_fields=update_fields):
                user.username = "ЖАСУР" if user.username != "ЖАСУР" else "Вали"
                user.save(update_fields=update_fields)
                self.assertEqual(key_of(user), user.username.casefold())

    def test_update_fields_without_username_leaves_key_alone(self):
        user = make_user("Али")
        user.first_name = "Yangi"
        user.save(update_fields=["first_name"])
        self.assertEqual(key_of(user), "али")
        user.save(update_fields=[])
        self.assertEqual(key_of(user), "али")

    def test_explicit_key_in_update_fields_is_not_duplicated(self):
        user = make_user("али")
        user.username = "ВАЛИ"
        user.save(update_fields=["username", "username_key"])
        self.assertEqual(key_of(user), "вали")

    def test_deleted_account_frees_the_name(self):
        user = make_user("Али")
        user.delete()
        self.assertEqual(register("али").status_code, 201)

    def test_reserved_prefix_is_case_insensitive(self):
        res = register("DELETED_5")
        self.assertEqual(res.status_code, 400)

    def test_make_username_key(self):
        self.assertEqual(User.make_username_key("Али"), "али")
        self.assertEqual(User.make_username_key("ＡＬＩ"), "ali")
        self.assertEqual(User.make_username_key("Straße"), "strasse")
        self.assertEqual(User.make_username_key(None), "")


class PanelSearchTests(APITestCase):
    def test_panel_finds_cyrillic_name_in_any_case(self):
        boss = make_user("boss", is_staff=True)
        boss.user_permissions.add(Permission.objects.get(codename="view_user"))
        ali = make_user("Али")
        make_user("vali")
        self.client.force_login(boss)
        for query in ("али", "АЛИ", "лИ"):
            with self.subTest(query=query):
                page = self.client.get(reverse("panel-accounts"), {"q": query}).context["page"]
                self.assertEqual([u.pk for u in page], [ali.pk])


class AdminFormTests(APITestCase):
    def test_admin_add_form_rejects_cyrillic_case_variant(self):
        from django.contrib.admin import site
        make_user("али")
        admin = site._registry[User]
        form = admin.get_form(None, None, change=False)(
            {"username": "АЛИ", "password1": "Parol-12345-x", "password2": "Parol-12345-x", "usable_password": "true"},
        )
        self.assertFalse(form.is_valid())
        self.assertIn(USERNAME_TAKEN_MESSAGE, form.errors["username"])


class FillUsernameKeyMigrationTests(APITestCase):
    """0018: mavjud foydalanuvchilarga kalit yozish (funksiya bevosita chaqiriladi)"""

    def blank_keys(self):
        # Migratsiyadan oldingi holatni taqlid qilamiz: save() chetlab o'tiladi, kalit vaqtinchalik noyob qiymat
        for pk in User.objects.values_list("pk", flat=True):
            User.objects.filter(pk=pk).update(username_key=f"eski{pk}")

    def test_fills_keys_with_nfkc_and_casefold(self):
        a, b, c = make_user("Али"), make_user("Vali"), make_user("legacy")
        User.objects.filter(pk=c.pk).update(username="ＬＥＧ")  # eski, normallashmagan nom
        self.blank_keys()
        fill_migration.fill_username_key(django_apps, None)
        self.assertEqual([key_of(a), key_of(b), key_of(c)], ["али", "vali", "leg"])

    def test_empty_table_is_fine(self):
        fill_migration.fill_username_key(django_apps, None)

    def test_duplicates_fail_with_clear_message_and_write_nothing(self):
        a, b, c = make_user("Али"), make_user("вали"), make_user("жасур")
        User.objects.filter(pk=b.pk).update(username="АЛИ")  # save()'siz: "Али" bilan faqat harf kattaligida farq
        self.blank_keys()
        with self.assertRaises(RuntimeError) as ctx:
            fill_migration.fill_username_key(django_apps, None)
        message = str(ctx.exception)
        self.assertIn("Али", message)
        self.assertIn("АЛИ", message)
        self.assertNotIn("жасур", message)
        self.assertIn("qayta nomlang", message)
        self.assertEqual([key_of(u) for u in (a, b, c)], [f"eski{a.pk}", f"eski{b.pk}", f"eski{c.pk}"])
        # nomlar jimgina o'zgartirilmagan
        self.assertEqual(User.objects.get(pk=b.pk).username, "АЛИ")

    def test_duplicates_after_nfkc_are_detected_too(self):
        make_user("admin")
        other = make_user("boshqa")
        User.objects.filter(pk=other.pk).update(username="ＡＤＭＩＮ")  # ＡＤＭＩＮ
        self.blank_keys()
        with self.assertRaises(RuntimeError):
            fill_migration.fill_username_key(django_apps, None)
