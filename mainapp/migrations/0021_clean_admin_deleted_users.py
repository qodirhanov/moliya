import secrets

from django.contrib.auth.hashers import make_password
from django.db import migrations


def clean_deleted_users(apps, schema_editor):
    """Avval admin o'chirgan akkauntlar (User.delete) faqat status=False bo'lardi — ism, email, telefon, parol va
    login nomi qolib ketardi. Ularni User.close_account() bilan bir xil holatga keltiramiz"""
    User = apps.get_model("mainapp", "User")
    PasswordResetCode = apps.get_model("mainapp", "PasswordResetCode")
    for user in User.objects.filter(status=False).exclude(username__startswith="deleted_"):
        username = f"deleted_{user.pk}"
        if User.objects.filter(username_key=username).exclude(pk=user.pk).exists():
            username = f"{username}_{secrets.token_hex(4)}"
        user.username = username
        user.username_key = username  # ASCII kichik harf — NFKC + casefold natijasi o'zi
        user.first_name = ""
        user.last_name = ""
        user.email = ""
        user.phone = None
        user.password = make_password(None)
        user.is_active = False
        user.save(update_fields=[
            "username", "username_key", "first_name", "last_name", "email", "phone", "password", "is_active",
        ])
        PasswordResetCode.objects.filter(user=user, used=False).update(used=True)


class Migration(migrations.Migration):

    dependencies = [
        ("mainapp", "0020_user_session_epoch"),
    ]

    operations = [
        migrations.RunPython(clean_deleted_users, migrations.RunPython.noop),
    ]
