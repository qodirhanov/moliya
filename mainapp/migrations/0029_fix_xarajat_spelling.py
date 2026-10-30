"""Umumiy (seed_data) chiqim turkumi nomidagi imlo: "harajat" -> "xarajat" (adabiy imlo).
Foydalanuvchilarning o'zi yaratgan turkumlarga tegilmaydi"""
from django.db import migrations

OLD = ("Kutilmagan harajatlar", "Favqulodda va kutilmagan harajatlar")
NEW = ("Kutilmagan xarajatlar", "Favqulodda va kutilmagan xarajatlar")


def rename(apps, old, new):
    ExpenseCategory = apps.get_model("mainapp", "ExpenseCategory")
    # Yangi nomli umumiy turkum allaqachon bo'lsa (seed_data qayta ishga tushirilgan) — nom takrorlanmasin
    if ExpenseCategory.objects.filter(user__isnull=True, name=new[0]).exists():
        return
    for cat in ExpenseCategory.objects.filter(user__isnull=True, name=old[0]):
        cat.name = new[0]
        if cat.description == old[1]:
            cat.description = new[1]
        cat.save(update_fields=["name", "description"])


def forwards(apps, schema_editor):
    rename(apps, OLD, NEW)


def backwards(apps, schema_editor):
    rename(apps, NEW, OLD)


class Migration(migrations.Migration):

    dependencies = [
        ("mainapp", "0028_logincode_new_email"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
