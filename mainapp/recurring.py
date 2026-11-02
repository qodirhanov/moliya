"""Doimiy to'lovlar: muddati kelganlarini daromad/xarajat sifatida yozish.

Alohida fon jarayoni (cron) kerak emas: foydalanuvchi ilovani ochganda (views.py: me_api) va doimiy to'lovlar
ro'yxati so'ralganda chaqiriladi. Ilova bir necha kun ochilmagan bo'lsa, o'tib ketgan sanalarning hammasi yoziladi.
"""
from datetime import datetime, time

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Expense, Income, RecurringPayment, prepare_uzs_rate

# Bitta to'lov uchun bir chaqiruvda yoziladigan eng ko'p sana: "har kuni" to'lov yil davomida ochilmasa ham
# so'rov uzoq cho'zilib ketmasin. Qolganlari keyingi ochilishda yoziladi
MAX_CATCH_UP = 60


def _operation_for(payment, day):
    """Shu sanadagi daromad yoki xarajat (hali saqlanmagan)"""
    today = timezone.localdate()
    # Bugungi to'lov hozirgi vaqt bilan, o'tgan kunniki kun o'rtasi bilan yoziladi — o'sha kun ro'yxatida tursin
    when = timezone.now() if day == today else timezone.make_aware(datetime.combine(day, time(12, 0)))
    note = f"Doimiy: {payment.name}"
    if payment.kind == RecurringPayment.KIND_INCOME:
        return Income(user=payment.user, wallet=payment.wallet, summa=payment.summa,
                      category=payment.income_category, description=note, date=when)
    return Expense(user=payment.user, wallet=payment.wallet, summa=payment.summa,
                   category=payment.expense_category, member=payment.member, description=note, date=when)


def process_payment(payment, today=None):
    """Bitta doimiy to'lovning muddati kelgan sanalarini yozadi. Yozilganlar sonini qaytaradi.
    Har sana alohida tranzaksiya: next_date shartli update bilan suriladi — ikki parallel so'rov bir sanani
    ikki marta yoza olmaydi (birinchisi surgach ikkinchisining sharti mos kelmaydi)"""
    today = today or timezone.localdate()
    created = 0
    for _ in range(MAX_CATCH_UP):
        due = payment.next_date
        if due > today or (payment.end_date and due > payment.end_date):
            break
        if not payment.wallet.status:
            error = "Hamyon o'chirilgan — to'lov to'xtatildi"
            if payment.last_error != error:
                RecurringPayment.objects.filter(pk=payment.pk).update(last_error=error)
                payment.last_error = error
            break
        following = payment.date_after(due)
        operation = _operation_for(payment, due)
        # Kurs tranzaksiyadan oldin olinadi: cbu.uz 10 soniyagacha javob bermasligi mumkin, shu payt yozuv qulfi band bo'lmasin
        prepare_uzs_rate(operation)
        try:
            with transaction.atomic():
                moved = RecurringPayment.objects.filter(pk=payment.pk, next_date=due, status=True).update(
                    next_date=following, last_error="")
                if not moved:
                    break  # boshqa so'rov allaqachon yozgan yoki to'lov o'chirilgan
                operation.save()
        except (ValueError, ValidationError) as e:
            # Odatda hamyonda pul yetmaydi: sana surilmaydi, keyingi ochilishda yana urinib ko'riladi
            error = str(e.messages[0] if isinstance(e, ValidationError) else e)[:255]
            RecurringPayment.objects.filter(pk=payment.pk).update(last_error=error)
            payment.last_error = error
            break
        payment.next_date = following
        payment.last_error = ""
        created += 1
    return created


def process_due(user):
    """Foydalanuvchining muddati kelgan barcha doimiy to'lovlarini yozadi"""
    today = timezone.localdate()
    due = RecurringPayment.objects.filter(user=user, status=True, next_date__lte=today).select_related("wallet", "user", "income_category", "expense_category", "member")
    return sum(process_payment(payment, today) for payment in due)
