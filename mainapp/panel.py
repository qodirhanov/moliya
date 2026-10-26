"""Admin panel: akkauntlar haqida ma'lumot. Faqat akkauntlarni ko'rish huquqi bor xodimlar ko'radi (qarang: can_view_panel) va faqat o'qiladi —
akkauntni tahrirlash Django admin orqali qilinadi"""
from datetime import timedelta
from functools import wraps

from django.core.paginator import Paginator
from django.db.models import Count, F, IntegerField, Max, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache

from .db_functions import casefold_contains_q
from .models import (AdminNotice, AdminNoticeRead, Category, Debt, Expense, ExpenseCategory, Income, Member, SupportMessage, Transfer, User,
                     Wallet)
from .notices import clean_notice_text
from .support import clean_support_text, messages_since, support_message_payload

PAGE_SIZE = 25
OPERATION_MODELS = (Income, Expense, Transfer)

ACTIVE_Q = Q(status=True, is_active=True)
# Foydalanuvchi o'zi o'chirgan (status=False) yoki admin bloklagan (is_active=False) akkauntlar
CLOSED_Q = Q(status=False) | Q(is_active=False)

FILTERS = {
    "all": ("Hammasi", Q()),
    "active": ("Faol", ACTIVE_Q),
    "closed": ("Nofaol", CLOSED_Q),
    "staff": ("Adminlar", Q(is_staff=True)),
}

SORTS = {
    "new": ("Yangi qo'shilgan", ["-date_joined", "-pk"]),
    "login": ("Oxirgi kirish", [F("last_login").desc(nulls_last=True), "-pk"]),
    "ops": ("Ko'p operatsiya", ["-ops_count", "-pk"]),
}


def can_view_panel(user):
    """Xodim (is_staff) va akkauntlarni ko'rish huquqi bor (superuser yoki "mainapp.view_user" ruxsati).
    Faqat is_staff yetarli emas: Django adminda ham xodim ruxsatsiz User ro'yxatini ko'ra olmaydi"""
    return user.is_authenticated and user.is_staff and (user.is_superuser or user.has_perm("mainapp.view_user"))


def staff_only(view):
    """Ruxsati yo'q har bir kishi (kirmagan ham, ruxsatsiz xodim yoki oddiy foydalanuvchi ham) uchun panel
    umuman yo'qdek — mavjud bo'lmagan manzil bilan bir xil 404. Kirmaganni login sahifasiga yo'naltirish
    PANEL_URL ni topishga imkon berardi: yo'naltirish = manzil bor.
    Xodim avval bosh sahifada (yoki admin kirish sahifasida) tizimga kiradi, so'ng panel manzilini ochadi"""
    @wraps(view)
    @never_cache
    def wrapper(request, *args, **kwargs):
        if not can_view_panel(request.user):
            raise Http404
        return view(request, *args, **kwargs)
    return wrapper


def _count(model):
    """Har bir foydalanuvchining faol yozuvlari soni. Bir nechta Count(...) JOIN bilan qatorlarni
    bir-biriga ko'paytirib yuboradi — shuning uchun har biri alohida subquery"""
    qs = (model.objects.filter(user=OuterRef("pk"), status=True)
          .order_by().values("user").annotate(c=Count("pk")).values("c"))
    return Coalesce(Subquery(qs, output_field=IntegerField()), Value(0))


def _last_created(model):
    return Subquery(
        model.objects.filter(user=OuterRef("pk"), status=True).order_by("-created_at").values("created_at")[:1]
    )


def users_with_stats():
    return User.objects.annotate(
        wallets_count=_count(Wallet),
        incomes_count=_count(Income),
        expenses_count=_count(Expense),
        transfers_count=_count(Transfer),
        last_income=_last_created(Income),
        last_expense=_last_created(Expense),
        last_transfer=_last_created(Transfer),
    ).annotate(ops_count=F("incomes_count") + F("expenses_count") + F("transfers_count"))


def last_activity(user):
    """Oxirgi qo'shilgan operatsiya vaqti (kirim, chiqim yoki o'tkazma)"""
    dates = [d for d in (user.last_income, user.last_expense, user.last_transfer) if d]
    return max(dates) if dates else None


def account_state(user):
    if not user.status:
        return "closed", "Nofaol"
    if not user.is_active:
        return "closed", "Bloklangan"
    return "active", "Faol"


@staff_only
def accounts_view(request):
    now = timezone.now()
    summary = User.objects.aggregate(
        total=Count("pk"),
        active=Count("pk", filter=ACTIVE_Q),
        closed=Count("pk", filter=CLOSED_Q),
        new_30d=Count("pk", filter=Q(date_joined__gte=now - timedelta(days=30))),
        seen_7d=Count("pk", filter=Q(last_login__gte=now - timedelta(days=7))),
    )
    summary["operations"] = sum(m.objects.filter(status=True).count() for m in OPERATION_MODELS)

    status_key = request.GET.get("status") if request.GET.get("status") in FILTERS else "all"
    sort_key = request.GET.get("sort") if request.GET.get("sort") in SORTS else "new"
    query = request.GET.get("q", "").strip()[:100]

    users = users_with_stats().filter(FILTERS[status_key][1])
    if query:
        users = users.filter(
            # Nom username_key bo'yicha, ism/familiya/email Casefold bo'yicha: SQL icontains kirillcha "али" bilan "Али"ni topmaydi
            Q(username_key__contains=User.make_username_key(query))
            | casefold_contains_q(("first_name", "last_name", "email"), query) | Q(phone__icontains=query)
        )
    users = users.order_by(*SORTS[sort_key][1])

    page = Paginator(users, PAGE_SIZE).get_page(request.GET.get("page"))
    for user in page:
        user.state, user.state_label = account_state(user)

    return render(request, "panel/accounts.html", {
        "summary": summary,
        "page": page,
        "query": query,
        "status_key": status_key,
        "sort_key": sort_key,
        "filters": [(key, label) for key, (label, _) in FILTERS.items()],
        "sorts": [(key, label) for key, (label, _) in SORTS.items()],
        "generated_at": now,
    })


@staff_only
def account_detail_view(request, pk):
    user = get_object_or_404(users_with_stats(), pk=pk)
    user.state, user.state_label = account_state(user)

    since = timezone.now() - timedelta(days=30)
    debts = Debt.objects.filter(user=user, status=True)
    currencies = sorted(set(Wallet.objects.filter(user=user, status=True).values_list("currency", flat=True)))

    return render(request, "panel/account_detail.html", {
        "account": user,
        "last_activity": last_activity(user),
        "ops_30d": sum(m.objects.filter(user=user, status=True, created_at__gte=since).count() for m in OPERATION_MODELS),
        "currencies": currencies,
        "debts_count": debts.count(),
        "open_debts_count": debts.filter(is_settled=False).count(),
        "members_count": Member.objects.filter(user=user, status=True).count(),
        "categories_count": (
            Category.objects.filter(user=user, status=True).count()
            + ExpenseCategory.objects.filter(user=user, status=True).count()
        ),
        "admin_url": reverse("admin:mainapp_user_change", args=[user.pk]),
        "support_count": SupportMessage.objects.filter(user=user).count(),
    })


# ==========================================
# YORDAM: foydalanuvchilar yozgan xabarlar va ularga javob (Sozlamalar → Yordam ning admin tomoni)
# ==========================================
def _unread_from_user():
    return SupportMessage.objects.filter(from_admin=False, is_read=False)


@staff_only
def support_inbox_view(request):
    """Suhbatlar ro'yxati: javob kutayotganlari (o'qilmagan xabari bor) tepada, keyin oxirgi xabar vaqti bo'yicha"""
    last = SupportMessage.objects.filter(user=OuterRef("pk")).order_by("-id")
    unread = (_unread_from_user().filter(user=OuterRef("pk"))
              .order_by().values("user").annotate(c=Count("pk")).values("c"))
    threads = (
        User.objects.filter(support_messages__isnull=False)
        .annotate(
            last_at=Max("support_messages__created_at"),
            last_text=Subquery(last.values("text")[:1]),
            last_from_admin=Subquery(last.values("from_admin")[:1]),
            unread=Coalesce(Subquery(unread, output_field=IntegerField()), Value(0)),
        )
        .order_by(F("unread").desc(), "-last_at", "-pk")
    )
    page = Paginator(threads, PAGE_SIZE).get_page(request.GET.get("page"))
    return render(request, "panel/support.html", {
        "page": page,
        "unread_total": _unread_from_user().count(),
    })


@staff_only
def support_thread_view(request, pk):
    """Bitta foydalanuvchi bilan suhbat. POST — javob yozish (yuborilgach sahifa qayta ochiladi: PRG)"""
    account = get_object_or_404(User, pk=pk)
    error = ""
    if request.method == "POST":
        try:
            text = clean_support_text(request.POST.get("text"))
        except ValueError as e:
            error = str(e)
        else:
            SupportMessage.objects.create(user=account, from_admin=True, author=request.user, text=text)
            return redirect("panel-support-thread", pk=account.pk)

    messages = messages_since(SupportMessage.objects.filter(user=account).select_related("author"), 0)
    _unread_from_user().filter(user=account).update(is_read=True)
    return render(request, "panel/support_thread.html", {
        "account": account,
        "messages": messages,
        "last_id": messages[-1].id if messages else 0,
        "error": error,
        "draft": request.POST.get("text", "") if error else "",
        "max_length": SupportMessage.MAX_LENGTH,
    })


@staff_only
def support_thread_poll_view(request, pk):
    """Ochiq suhbat sahifasi uchun yangi xabarlar (?after=<oxirgi id>) — static/js/panel-support.js har necha soniyada so'raydi"""
    account = get_object_or_404(User, pk=pk)
    try:
        after = max(int(request.GET.get("after") or 0), 0)
    except ValueError:
        after = 0
    messages = messages_since(SupportMessage.objects.filter(user=account), after) if after else []
    _unread_from_user().filter(user=account, id__in=[m.id for m in messages]).update(is_read=True)
    return JsonResponse({"messages": [support_message_payload(m) for m in messages]})


# ==========================================
# XABAR YUBORISH: bitta foydalanuvchiga yoki hammaga (ilovada navbar qo'ng'irog'idagi "Xabarlar"ga tushadi)
# ==========================================
def _find_recipient(username):
    username = str(username or "").strip().lstrip("@")
    if not username:
        raise ValueError("Kimga yuborishni yozing (login)")
    user = User.objects.filter(username_key=User.make_username_key(username)).first()
    if not user:
        raise ValueError(f"@{username} topilmadi")
    if not (user.status and user.is_active):
        raise ValueError(f"@{user.username} akkaunti faol emas")
    return user


@staff_only
def notices_view(request):
    """GET — yuborish formasi va yuborilganlar ro'yxati (?to=<login> — bitta foydalanuvchiga tayyor forma).
    POST — yuborish (PRG: yuborilgach sahifa qayta ochiladi)"""
    error = ""
    target = request.POST.get("target") if request.method == "POST" else ("user" if request.GET.get("to") else "all")
    to = (request.POST.get("to") if request.method == "POST" else request.GET.get("to", "")) or ""
    if request.method == "POST":
        try:
            text = clean_notice_text(request.POST.get("text"))
            recipient = _find_recipient(to) if target == "user" else None
        except ValueError as e:
            error = str(e)
        else:
            AdminNotice.objects.create(author=request.user, recipient=recipient, text=text)
            return redirect(f"{reverse('panel-notices')}?sent=1")

    # Hammaga yuborilgani o'sha paytda ro'yxatdan o'tganlarga ko'rinadi (notices.notices_for)
    joined_before = (User.objects.filter(date_joined__lte=OuterRef("created_at"))
                     .order_by().annotate(g=Value(1)).values("g").annotate(c=Count("pk")).values("c"))
    reads = (AdminNoticeRead.objects.filter(notice=OuterRef("pk"))
             .order_by().values("notice").annotate(c=Count("pk")).values("c"))
    notices = (AdminNotice.objects.select_related("author", "recipient")
               .annotate(read_count=Coalesce(Subquery(reads, output_field=IntegerField()), Value(0)),
                         joined_count=Coalesce(Subquery(joined_before, output_field=IntegerField()), Value(0)))
               .order_by("-id"))
    page = Paginator(notices, PAGE_SIZE).get_page(request.GET.get("page"))
    for n in page:
        n.audience = 1 if n.recipient_id else n.joined_count
    return render(request, "panel/notices.html", {
        "page": page,
        "error": error,
        "target": target if target in ("all", "user") else "all",
        "to": to.strip()[:150],
        "draft": request.POST.get("text", "") if error else "",
        "sent": request.GET.get("sent") == "1",
        "max_length": AdminNotice.MAX_LENGTH,
        "active_users": User.objects.filter(ACTIVE_Q).count(),
    })


@staff_only
def notice_delete_view(request, pk):
    """Yuborilgan xabarni qaytarib olish: foydalanuvchilar qo'ng'irog'idan ham yo'qoladi"""
    if request.method != "POST":
        raise Http404
    get_object_or_404(AdminNotice, pk=pk).delete()
    return redirect("panel-notices")
