from decimal import Decimal

from django.db import migrations

# Hamyon valyutasi serializerda ISO kodiga keltirib saqlanadi; eski qo'lda kiritilgan nomlar uchun faqat so'm yozilishlari
UZS_NAMES = {"UZS", "SO'M", "SO‘M", "SOʻM", "SOM", "SUM", "СУМ", "СЎМ"}


def fill_uzs_rate(apps, schema_editor):
    """Mavjud daromad/harajatlarga BIR MARTA ExchangeRate jadvalidagi hozirgi kursni yozadi (tarmoqqa chiqmaydi):
    eski operatsiyaning haqiqiy o'sha kundagi kursi noma'lum, shuning uchun shu kundan boshlab ular qotadi.
    So'm qatorlariga 1; jadvalda kursi yo'q valyutalar NULL qoladi (statistika ularni bugungi kurs bilan hisoblaydi).
    Valyuta bo'yicha guruhlab, har valyuta va model uchun bitta UPDATE"""
    ExchangeRate = apps.get_model("mainapp", "ExchangeRate")
    Wallet = apps.get_model("mainapp", "Wallet")
    stored = {row.currency.upper(): row.rate for row in ExchangeRate.objects.all()}
    currencies = Wallet.objects.order_by().values_list("currency", flat=True).distinct()
    for currency in currencies:
        code = (currency or "").strip().upper()
        rate = Decimal(1) if code in UZS_NAMES else stored.get(code)
        if rate is None:
            continue
        for model_name in ("Income", "Expense"):
            model = apps.get_model("mainapp", model_name)
            model.objects.filter(wallet__currency=currency, uzs_rate__isnull=True).update(uzs_rate=rate)


class Migration(migrations.Migration):

    dependencies = [
        ('mainapp', '0015_income_expense_uzs_rate'),
    ]

    operations = [
        migrations.RunPython(fill_uzs_rate, migrations.RunPython.noop),
    ]
