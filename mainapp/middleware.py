import time

from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from .devices import LOGIN_TIME_KEY, register_device, touch_device
from .models import UserDevice


@receiver(user_logged_in)
def remember_login_time(sender, request, user, **kwargs):
    if request is not None and hasattr(request, "session"):
        request.session[LOGIN_TIME_KEY] = int(time.time())
        # Sessiya kaliti login() ichida allaqachon yangilangan — qurilma shu kalit bilan yoziladi
        register_device(request, user)


@receiver(user_logged_out)
def forget_device(sender, request, user, **kwargs):
    # Chiqishda sessiya o'chadi (logout -> flush), qurilma ham ro'yxatdan olib tashlanadi
    if request is not None and hasattr(request, "session") and request.session.session_key:
        UserDevice.objects.filter(session_key=request.session.session_key).delete()


class DeviceTrackingMiddleware:
    """Qurilmalar ro'yxati uchun: kirgan foydalanuvchining har so'rovida qurilma yozuvi yaratiladi (bu imkoniyat
    qo'shilishidan oldin ochilgan sessiyalar ham ro'yxatga tushadi) va oxirgi faollik vaqti yangilanadi"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            touch_device(request)
        return self.get_response(request)


SESSION_REFRESH_KEY = "_refreshed_at"
SESSION_REFRESH_STEP = 24 * 60 * 60


class SessionRefreshMiddleware:
    """Sessiya muddatini sirg'anuvchi (sliding) saqlaydi, lekin har so'rovda emas: SESSION_SAVE_EVERY_REQUEST o'chirilgan
    (u har so'rovda SQLite'ga yozardi). Kirgan foydalanuvchining sessiyasiga oxirgi yangilash vaqti yoziladi va u
    bir sutkadan eskirsa qayta yoziladi — sessiya 'o'zgargan' deb belgilanib, Django uni yangi SESSION_COOKIE_AGE
    bilan saqlaydi va cookie muddatini ham uzaytiradi"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            now = int(time.time())
            last = request.session.get(SESSION_REFRESH_KEY)
            if not isinstance(last, int) or now - last > SESSION_REFRESH_STEP:
                request.session[SESSION_REFRESH_KEY] = now
        return self.get_response(request)


class SessionMaxAgeMiddleware:
    """Sessiyaning mutlaq muddati (settings.SESSION_MAX_AGE). SessionRefreshMiddleware tufayli
    SESSION_COOKIE_AGE kuniga bir marta uzayadi, ya'ni faqat harakatsizlik chegarasi bo'lib qoladi.
    O'g'irlangan yoki ochiq qolgan sessiya bilan cheksiz ishlab bo'lmasligi uchun kirilgandan
    SESSION_MAX_AGE o'tgach baribir qayta kirish talab qilinadi.
    Hozir SESSION_MAX_AGE = None (o'chirilgan) — middleware hech narsa qilmaydi, kelajakda qayta yoqish uchun saqlangan"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # SESSION_MAX_AGE = None — mutlaq muddat o'chirilgan: hech narsa tekshirilmaydi va sessiyaga yozilmaydi
        max_age = getattr(settings, "SESSION_MAX_AGE", None)
        if max_age is not None and request.user.is_authenticated:
            now = int(time.time())
            # Bu cheklovdan oldin ochilgan sessiyalarda kirish vaqti yo'q — hisob hozirdan boshlanadi
            started = request.session.setdefault(LOGIN_TIME_KEY, now)
            if now - started > max_age:
                logout(request)
        return self.get_response(request)
