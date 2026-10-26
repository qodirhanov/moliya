import unicodedata

from django.db import migrations


def fill_username_key(apps, schema_editor):
    """Mavjud foydalanuvchilarga username_key yozadi: NFKC + casefold (User.make_username_key bilan bir xil;
    migratsiya modelga bog'lanmasligi uchun qoida shu yerda takrorlangan). Kalitlari to'qnashadigan nomlar bo'lsa
    (masalan "Али" va "али") hech narsa yozilmaydi va qaysi nomlar to'qnashgani aytiladi — nomlar jimgina o'zgartirilmaydi"""
    User = apps.get_model("mainapp", "User")
    rows = list(User.objects.order_by("pk").only("pk", "username"))
    by_key = {}
    for user in rows:
        user.username_key = unicodedata.normalize("NFKC", user.username).casefold()
        by_key.setdefault(user.username_key, []).append(user.username)
    clashes = ["/".join(names) for names in by_key.values() if len(names) > 1]
    if clashes:
        raise RuntimeError(
            "Katta-kichik harfigina (yoki yozilishigagina) farq qiladigan foydalanuvchi nomlari bor: "
            + ", ".join(clashes)
            + ". Migratsiyadan oldin ulardan birini qayta nomlang."
        )
    User.objects.bulk_update(rows, ["username_key"], batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ('mainapp', '0017_user_username_key'),
    ]

    operations = [
        migrations.RunPython(fill_username_key, migrations.RunPython.noop),
    ]
