from django.db import migrations, models
from django.db.models import F


def fill_transfer_and_debt_currency(apps, schema_editor):
    Transfer = apps.get_model("mainapp", "Transfer")
    Debt = apps.get_model("mainapp", "Debt")
    # Eski o'tkazmalar kurssiz yozilgan: hamyon balanslari o'zgarmasligi uchun tushgan summa = yechilgan summa
    Transfer.objects.update(to_summa=F("summa"), rate=1)
    for debt in Debt.objects.filter(wallet__isnull=False).select_related("wallet"):
        debt.currency = (debt.wallet.currency or "UZS").upper()
        debt.save(update_fields=["currency"])


class Migration(migrations.Migration):

    dependencies = [
        ("mainapp", "0009_hidden_categories"),
    ]

    operations = [
        # Katta summalar uchun (IntegerField chegarasi ~2.1 mlrd)
        migrations.AlterField(model_name="wallet", name="summa", field=models.BigIntegerField(default=0)),
        migrations.AlterField(model_name="income", name="summa", field=models.BigIntegerField()),
        migrations.AlterField(model_name="expense", name="summa", field=models.BigIntegerField()),
        migrations.AlterField(
            model_name="transfer", name="summa",
            field=models.BigIntegerField(help_text="Chiqadigan hamyondan yechilgan summa (uning valyutasida)"),
        ),
        migrations.AlterField(model_name="debt", name="summa", field=models.BigIntegerField(help_text="Umumiy qarz summasi")),
        migrations.AlterField(
            model_name="debt", name="paid_summa",
            field=models.BigIntegerField(default=0, help_text="Hozirgacha qaytarilgan summa"),
        ),
        # Hamyon PIN-kodi: noto'g'ri urinishlar hisobi
        migrations.AddField(
            model_name="wallet", name="pin_attempts",
            field=models.PositiveSmallIntegerField(default=0, help_text="Ketma-ket noto'g'ri PIN urinishlari"),
        ),
        migrations.AddField(
            model_name="wallet", name="pin_locked_until",
            field=models.DateTimeField(blank=True, null=True, help_text="Shu vaqtgacha PIN kiritish bloklangan"),
        ),
        # Valyuta: o'tkazmada tushgan summa va kurs, qarz valyutasi
        migrations.AddField(
            model_name="transfer", name="to_summa",
            field=models.BigIntegerField(default=0, help_text="Tushadigan hamyonga qo'shilgan summa (uning valyutasida)"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="transfer", name="rate",
            field=models.DecimalField(
                decimal_places=8, default=1, max_digits=20,
                help_text="1 birlik chiqim valyutasi = rate birlik kirim valyutasi",
            ),
        ),
        migrations.AddField(
            model_name="debt", name="currency",
            field=models.CharField(
                default="UZS", max_length=10,
                help_text="Qarz valyutasi (hamyon tanlansa — hamyon valyutasi)",
            ),
        ),
        migrations.CreateModel(
            name="ExchangeRate",
            fields=[
                ("currency", models.CharField(max_length=10, primary_key=True, serialize=False)),
                ("rate", models.DecimalField(decimal_places=8, help_text="1 birlik = rate UZS", max_digits=20)),
                ("rate_date", models.CharField(blank=True, help_text="Markaziy bank e'lon qilgan sana", max_length=20)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Valyuta kursi", "verbose_name_plural": "Valyuta kurslari"},
        ),
        migrations.RunPython(fill_transfer_and_debt_currency, migrations.RunPython.noop),
    ]
