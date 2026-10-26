from django.core.management import call_command
from django.db import migrations


def create_cache_table(apps, schema_editor):
    # settings.CACHES baza keshini ishlatsa (REDIS_URL berilmagan), uning jadvali yaratiladi.
    # Redis ishlatilsa, buyruq hech narsa qilmaydi. `migrate` dan keyin alohida buyruq eslab qolish shart emas
    call_command("createcachetable", database=schema_editor.connection.alias, verbosity=0)


class Migration(migrations.Migration):

    dependencies = [
        ("mainapp", "0012_remove_wallet_pin"),
    ]

    operations = [
        migrations.RunPython(create_cache_table, migrations.RunPython.noop),
    ]
