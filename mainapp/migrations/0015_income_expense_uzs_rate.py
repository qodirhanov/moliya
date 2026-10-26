from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mainapp', '0014_user_username_lower_unique'),
    ]

    operations = [
        migrations.AddField(
            model_name='income',
            name='uzs_rate',
            field=models.DecimalField(blank=True, decimal_places=8, help_text="Operatsiya yozilgan paytdagi kurs: 1 birlik hamyon valyutasi necha so'm (bo'sh bo'lsa statistikada bugungi kurs olinadi)", max_digits=20, null=True),
        ),
        migrations.AddField(
            model_name='expense',
            name='uzs_rate',
            field=models.DecimalField(blank=True, decimal_places=8, help_text="Operatsiya yozilgan paytdagi kurs: 1 birlik hamyon valyutasi necha so'm (bo'sh bo'lsa statistikada bugungi kurs olinadi)", max_digits=20, null=True),
        ),
    ]
