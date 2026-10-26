"""Admin xabarlari: admin panelidan bitta foydalanuvchiga yoki hammaga yuboriladi, ilovada navbar qo'ng'irog'idagi
"Xabarlar" ro'yxatida chiqadi. Yangilari Yordam bilan bir xil polling bilan bilinadi (support/unread/ da notices_unread)"""
from datetime import timedelta

from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import AdminNotice, AdminNoticeRead

# O'qilgan xabar qo'ng'iroqda shuncha kun turadi, o'qilmagani — o'qilguncha
KEEP_READ_DAYS = 30
LIST_LIMIT = 20


def clean_notice_text(value):
    text = str(value or "").strip()
    if not text:
        raise ValueError("Xabar yozing")
    if len(text) > AdminNotice.MAX_LENGTH:
        raise ValueError(f"Xabar {AdminNotice.MAX_LENGTH} belgidan oshmasin")
    return text


def notices_for(user):
    """Shaxsan unga yozilganlar va u ro'yxatdan o'tgandan keyin hammaga yuborilganlar"""
    return AdminNotice.objects.filter(
        Q(recipient=user) | Q(recipient__isnull=True, created_at__gte=user.date_joined)
    )


def _read_by(user):
    return Exists(AdminNoticeRead.objects.filter(notice=OuterRef("pk"), user=user))


def unread_notices_for(user):
    return notices_for(user).exclude(_read_by(user))


def unread_notice_count(user):
    return unread_notices_for(user).count()


def notice_payload(notice):
    return {
        "id": notice.id,
        "text": notice.text,
        "broadcast": notice.recipient_id is None,
        "is_read": notice.is_read,
        "created_at": notice.created_at.isoformat(),
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notices_api(request):
    """Qo'ng'iroq uchun: o'qilmaganlar va oxirgi KEEP_READ_DAYS kunda o'qilganlar (yangidan eskiga)"""
    since = timezone.now() - timedelta(days=KEEP_READ_DAYS)
    notices = (notices_for(request.user).annotate(is_read=_read_by(request.user))
               .filter(Q(is_read=False) | Q(created_at__gte=since)).order_by("-id")[:LIST_LIMIT])
    notices = list(notices)
    return Response({
        "notices": [notice_payload(n) for n in notices],
        "unread": sum(not n.is_read for n in notices),
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def notices_read_api(request):
    """Qo'ng'iroq ochilganda: barcha o'qilmagan admin xabarlari o'qilgan deb belgilanadi"""
    ids = list(unread_notices_for(request.user).values_list("id", flat=True))
    AdminNoticeRead.objects.bulk_create(
        [AdminNoticeRead(notice_id=i, user=request.user) for i in ids], ignore_conflicts=True
    )
    return Response({"unread": 0})
