from django.contrib.auth.backends import ModelBackend

from .models import User


def find_user_by_login(identifier):
    """Foydalanuvchini nomi yoki emaili bo'yicha topadi (kirish va parolni tiklashda ishlatiladi)"""
    identifier = (identifier or "").strip()
    if not identifier:
        return None
    user = None
    if "@" in identifier:
        user = User.objects.filter(email__iexact=identifier).order_by("id").first()
    if user is None:
        user = User.objects.filter(username=identifier).first()
    return user


class UsernameOrEmailBackend(ModelBackend):
    """Foydalanuvchi nomi YOKI email + parol bilan kirish"""

    def authenticate(self, request, username=None, password=None, email=None, **kwargs):
        identifier = email or username or kwargs.get(User.USERNAME_FIELD)
        if password is None:
            return None

        user = find_user_by_login(identifier)
        if user is None:
            # Vaqt bo'yicha foydalanuvchi mavjudligini bilib olishning oldini olish
            User().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
