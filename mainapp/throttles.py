from rest_framework.throttling import SimpleRateThrottle


class AuthRateThrottle(SimpleRateThrottle):
    """Kirish, ro'yxatdan o'tish va parol tiklash uchun IP bo'yicha qattiqroq cheklov
    (settings: DEFAULT_THROTTLE_RATES["auth"]) — parol tanlash, hisob spami va elektron pochta-bombaga qarshi"""
    scope = "auth"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


def client_ip(request):
    """Foydalanuvchi IP manzili — so'rovlar cheklovi (throttle) bilan bir xil usulda: X-Forwarded-For
    faqat settings.NUM_PROXIES bo'yicha ishonchli proksilar qo'shgan qismida olinadi, soxta sarlavha o'tmaydi.
    request None bo'lishi mumkin (admin/konsol/testlar) — u holda bo'sh qator"""
    if request is None or not hasattr(request, "META"):
        return ""
    return (AuthRateThrottle().get_ident(request) or "")[:64]
