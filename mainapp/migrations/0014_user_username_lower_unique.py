from django.db.models.functions import Lower
from django.db import migrations, models


def check_no_case_duplicates(apps, schema_editor):
    """Faqat harf kattaligi bilan farq qiladigan nomlar (masalan "Ali" va "ali") bo'lsa, cheklov o'rnatilmaydi —
    tushunarsiz "UNIQUE constraint failed" o'rniga qaysi nomlar to'qnashgani aytiladi"""
    User = apps.get_model("mainapp", "User")
    duplicates = (
        User.objects.annotate(lowered=Lower("username"))
        .values("lowered").annotate(total=models.Count("id")).filter(total__gt=1)
    )
    names = [row["lowered"] for row in duplicates]
    if names:
        raise RuntimeError(
            "Katta-kichik harfigina farq qiladigan foydalanuvchi nomlari bor: "
            + ", ".join(names)
            + ". Migratsiyadan oldin ulardan birini qayta nomlang."
        )


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('mainapp', '0013_create_cache_table'),
    ]

    operations = [
        migrations.RunPython(check_no_case_duplicates, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='user',
            constraint=models.UniqueConstraint(Lower('username'), name='mainapp_user_username_lower_uniq', violation_error_message='Bu foydalanuvchi nomi allaqachon band'),
        ),
    ]
