"""Sozlamalar → Yordam (admin bilan chat) va Sozlamalar → Moliya yordamchisi API'lari.
Yangi xabarlar polling bilan olinadi: brauzer ?after=<oxirgi id> bilan so'raydi (websocket ishlatilmaydi)"""
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.html import format_html
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from . import assistant, faq
from .models import SupportMessage, User
from .notices import unread_notice_count
from .security_log import log_event

logger = logging.getLogger(__name__)

# Suhbat birinchi ochilganda shuncha oxirgi xabar yuboriladi
HISTORY_LIMIT = 100


class SupportRateThrottle(UserRateThrottle):
    """Faqat xabar yuborishni cheklaydi — GET so'rovlari (polling) umumiy "user" cheklovida qoladi"""
    scope = "support"

    def allow_request(self, request, view):
        return request.method != "POST" or super().allow_request(request, view)


class AssistantRateThrottle(UserRateThrottle):
    """Pullik Claude API ishlatilgandagina qattiq cheklov; bepul ma'lumotnoma qidiruvi umumiy "user" cheklovida"""
    scope = "assistant"

    def allow_request(self, request, view):
        return not assistant.is_enabled() or super().allow_request(request, view)


def support_message_payload(message):
    return {
        "id": message.id,
        "text": message.text,
        "from_admin": message.from_admin,
        "created_at": message.created_at.isoformat(),
    }


def unread_for_user(user):
    """Foydalanuvchi hali o'qimagan admin javoblari soni (navbar qo'ng'irog'i uchun)"""
    return SupportMessage.objects.filter(user=user, from_admin=True, is_read=False).count()


def clean_support_text(value):
    text = str(value or "").strip()
    if not text:
        raise ValueError("Xabar yozing")
    if len(text) > SupportMessage.MAX_LENGTH:
        raise ValueError(f"Xabar {SupportMessage.MAX_LENGTH} belgidan oshmasin")
    return text


def after_id(request):
    try:
        return max(int(request.query_params.get("after") or 0), 0)
    except (TypeError, ValueError):
        return 0


def messages_since(qs, after):
    """after=0 — oxirgi HISTORY_LIMIT ta xabar, aks holda faqat undan keyingilari (eskidan yangiga)"""
    if after:
        return list(qs.filter(id__gt=after).order_by("id")[:HISTORY_LIMIT])
    return list(reversed(qs.order_by("-id")[:HISTORY_LIMIT]))


def admin_notify_emails():
    """Yangi xabar haqida xat oladiganlar: .env dagi SUPPORT_NOTIFY_EMAILS, berilmagan bo'lsa —
    admin paneldagi Yordam bo'limini ko'ra oladigan faol xodimlarning emaili"""
    if settings.SUPPORT_NOTIFY_EMAILS:
        return settings.SUPPORT_NOTIFY_EMAILS
    from .panel import can_view_panel  # panel.py bu moduldan import qiladi — aylanma importdan qochish
    staff = User.objects.filter(is_staff=True, is_active=True, status=True).exclude(email="")
    return sorted({u.email for u in staff if can_view_panel(u)})


def notify_admins(request, message):
    """Adminlarga xat: kim yozdi, xabar matni va javob yozish sahifasiga havola. Fon oqimida yuboriladi —
    SMTP sekin bo'lsa ham foydalanuvchi javobni kutib qolmaydi; xat ketmasa faqat logga yoziladi"""
    recipients = admin_notify_emails()
    if not recipients:
        return
    from .views import _run_in_background  # views.py bu moduldan import qiladi
    user = message.user
    url = request.build_absolute_uri(reverse("panel-support-thread", args=[user.pk]))
    # Ism xat sarlavhasiga (Subject) tushadi — qator tashlash bo'lsa xat umuman ketmasdi
    name = " ".join(str(user).split())
    _run_in_background(_send_admin_mail, recipients, name, user.username, message.text, url)


def _send_admin_mail(recipients, name, username, text, url):
    try:
        send_mail(
            subject=f"Moliya — Yordam: {name} xabar yozdi",
            message=(
                f"{name} (@{username}) Yordam bo'limida xabar yozdi:\n\n"
                f"{text}\n\n"
                f"Javob yozish: {url}\n\n"
                "Foydalanuvchi yana yozsa, siz suhbatni ochmaguningizcha qayta xat yuborilmaydi."
            ),
            # Ism va xabar foydalanuvchi kiritgan matn — HTML ichiga format_html orqali ekranlanib qo'yiladi
            html_message=format_html(
                '<div style="font-family:Arial,sans-serif;font-size:15px;color:#1f2937;line-height:1.5">'
                "<p><b>{}</b> (@{}) Yordam bo'limida xabar yozdi:</p>"
                '<blockquote style="margin:12px 0;padding:10px 14px;background:#f3f4f6;border-radius:8px;'
                'white-space:pre-wrap">{}</blockquote>'
                '<p><a href="{}" style="display:inline-block;padding:10px 18px;background:#2F6F57;color:#fff;'
                'border-radius:8px;text-decoration:none">Javob yozish</a></p>'
                '<p style="color:#6b7280;font-size:13px">Foydalanuvchi yana yozsa, siz suhbatni ochmaguningizcha '
                "qayta xat yuborilmaydi.</p>"
                "</div>",
                name, username, text, url,
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
        )
    except Exception:
        logger.exception("Yordam xabari haqida adminga xat yuborib bo'lmadi (@%s)", username)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([UserRateThrottle, SupportRateThrottle])
def support_messages_api(request):
    """GET ?after=<id> — suhbatdagi xabarlar (admin javoblari o'qilgan deb belgilanadi); POST {text} — adminga yozish"""
    qs = SupportMessage.objects.filter(user=request.user)
    if request.method == "POST":
        try:
            text = clean_support_text(request.data.get("text"))
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        # Oldingi xabarlari hali o'qilmagan bo'lsa admin allaqachon xabardor — har xabarga yangi xat yuborilmaydi
        already_waiting = qs.filter(from_admin=False, is_read=False).exists()
        message = SupportMessage.objects.create(user=request.user, text=text)
        log_event("support_message", request, user_id=request.user.pk, username=request.user.username)
        if not already_waiting:
            notify_admins(request, message)
        return Response(support_message_payload(message), status=status.HTTP_201_CREATED)

    messages = messages_since(qs, after_id(request))
    unread_ids = [m.id for m in messages if m.from_admin and not m.is_read]
    if unread_ids:
        SupportMessage.objects.filter(id__in=unread_ids).update(is_read=True)
    return Response({"messages": [support_message_payload(m) for m in messages]})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def support_unread_api(request):
    """Navbar qo'ng'irog'i uchun: o'qilmagan admin javoblari va admin xabarlari soni"""
    return Response({"unread": unread_for_user(request.user), "notices_unread": unread_notice_count(request.user)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([UserRateThrottle, AssistantRateThrottle])
def assistant_api(request):
    """Moliya yordamchisi: {messages: [{role, content}, ...]} — suhbat tarixi brauzerda saqlanadi, serverda yozilmaydi.
    Odatda bepul: javob ma'lumotnomadan qidiriladi (faq.py). .env da ANTHROPIC_API_KEY bo'lsa — Claude javob beradi (pullik)"""
    try:
        messages = assistant.clean_history(request.data.get("messages"))
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    if not assistant.is_enabled():
        return Response({"answer": faq.answer(messages[-1]["content"])})
    try:
        answer = assistant.ask(messages)
    except RuntimeError as e:
        return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)
    return Response({"answer": answer})
