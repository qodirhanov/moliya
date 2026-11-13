from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from mainapp.security_log import log_event

DEFAULT_DAYS = 30
# Himoya: bir ishga tushirishda shundan ko'p akkaunt o'chmaydi (xato yoki bazani qayta tiklash natijasida
# hamma last_login bo'sh/eski bo'lib qolsa, hammasi birdan o'chib ketmasligi uchun). Kerak bo'lsa --max-delete bilan oshiring
DEFAULT_MAX_DELETE = 100


def inactive_accounts(days=DEFAULT_DAYS, now=None):
    """Oxirgi `days` kun ichida kirmagan oddiy akkauntlar.

    Faollik = last_login, ro'yxatdan o'tgan sana (date_joined) va qurilmalarning oxirgi so'rov vaqti (UserDevice.last_seen)
    ichidagi eng yangisi. last_seen hisobga olinadi, chunki sessiya cookie'da uzoq saqlanadi: foydalanuvchi ilovani
    har kuni ochsa ham qayta "kirmaydi" (last_login yangilanmaydi) — faqat last_login'ga qarasak, faol odam o'chib ketardi.
    HECH QACHON o'chmaydi: superuser, staff (admin), bloklangan (is_active=False — blok chetlab o'tilmasligi uchun)"""
    User = get_user_model()
    cutoff = (now or timezone.now()) - timedelta(days=days)
    return (
        User.objects
        .filter(is_superuser=False, is_staff=False, is_active=True, date_joined__lt=cutoff)
        .filter(Q(last_login__isnull=True) | Q(last_login__lt=cutoff))
        .exclude(devices__last_seen__gte=cutoff)
        .order_by("pk")
    )


class Command(BaseCommand):
    help = ("Oxirgi 30 kun (--days) davomida kirmagan akkauntlarni va ularning BARCHA ma'lumotlarini (email, login nomi, "
            "hamyon, kirim/chiqim, qarz va h.k.) butunlay o'chiradi. Qaytarib bo'lmaydi — avval --dry-run bilan tekshiring. "
            "Superuser, staff va bloklangan akkauntlar o'chmaydi")

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=DEFAULT_DAYS,
                            help=f"Necha kun kirmagan akkaunt o'chadi (standart: {DEFAULT_DAYS})")
        parser.add_argument("--dry-run", action="store_true", help="Faqat ro'yxatni ko'rsatadi, hech narsa o'chirmaydi")
        parser.add_argument("--max-delete", type=int, default=DEFAULT_MAX_DELETE,
                            help=f"Bir ishga tushirishda eng ko'pi bilan shuncha akkaunt (standart: {DEFAULT_MAX_DELETE}); "
                                 "oshib ketsa hech narsa o'chirilmaydi")

    def handle(self, *args, **options):
        days = options["days"]
        if days < 1:
            raise CommandError("--days kamida 1 bo'lishi kerak")
        users = list(inactive_accounts(days))
        dry_run = options["dry_run"]
        label = "[DRY-RUN] " if dry_run else ""
        self.stdout.write(f"{label}{days} kundan beri kirmagan akkauntlar: {len(users)} ta")

        if len(users) > options["max_delete"]:
            raise CommandError(
                f"{len(users)} ta akkaunt chegaradan ({options['max_delete']}) ko'p — hech narsa o'chirilmadi. "
                "Ro'yxatni --dry-run bilan tekshiring va ishonch hosil qilsangiz --max-delete ni oshiring"
            )

        deleted = 0
        for user in users:
            line = f"id={user.pk} username={user.username!r} last_login={user.last_login} joined={user.date_joined:%Y-%m-%d}"
            if dry_run:
                self.stdout.write(f"  {line}")
                continue
            # Har akkaunt o'z tranzaksiyasida: birida xato chiqsa qolganlari ta'sirlanmaydi, yarim o'chgan holat qolmaydi
            try:
                with transaction.atomic():
                    user.delete()
            except Exception as exc:  # noqa: BLE001 — bitta akkaunt butun ishni to'xtatmasin
                self.stderr.write(f"  XATO {line}: {exc}")
                log_event("inactive_account_delete_failed", None, level=40, user_id=user.pk, error=exc)
                continue
            deleted += 1
            self.stdout.write(f"  o'chirildi {line}")
            log_event("inactive_account_deleted", None, user_id=user.pk, username=user.username, days=days)

        if dry_run:
            self.stdout.write("Hech narsa o'chirilmadi (dry-run)")
        else:
            self.stdout.write(f"Jami o'chirildi: {deleted} ta")
