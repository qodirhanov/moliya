from django.db import migrations


def purge_closed_accounts(apps, schema_editor):
    """Eski "soft delete" (close_account) qoldirgan `deleted_N` akkauntlar: shaxsiy ma'lumotlari allaqachon tozalangan,
    lekin qatorlar va moliyaviy yozuvlar qolgan edi. Endi o'chirish haqiqiy — ularni ham bazadan butunlay olib tashlaymiz.
    Faqat ilovaning o'zi yopgan akkauntlar: status=False, nom `deleted_` bilan, email bo'sh, parol yaroqsiz, admin/staff emas"""
    User = apps.get_model("mainapp", "User")
    qs = User.objects.filter(
        status=False, is_active=False, is_superuser=False, is_staff=False,
        username__startswith="deleted_", email="", password__startswith="!",
    )
    for user in qs:
        user.delete()  # tarixiy modelda custom delete() yo'q — Django CASCADE bilan bog'liq hammasini o'chiradi


class Migration(migrations.Migration):

    dependencies = [
        ("mainapp", "0030_wallet_is_goal"),
    ]

    operations = [
        migrations.RunPython(purge_closed_accounts, migrations.RunPython.noop),
    ]
