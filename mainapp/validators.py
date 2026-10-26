from django.core.exceptions import ValidationError as DjangoValidationError


class SimplePasswordValidator:
    """
    Yengillashtirilgan "oddiy parol" tekshiruvi. Parol faqat ikki holatda rad etiladi:
    1. Parol foydalanuvchi nomi bilan bir xil bo'lsa
    2. Parol 1 yoki 2 xil belgidan iborat bo'lsa (masalan "aaaaaaaa", "abababab")

    Eng ko'p tarqalgan parollarni ("password", "qwerty12"...) Django'ning CommonPasswordValidator'i
    alohida rad etadi (settings.AUTH_PASSWORD_VALIDATORS).
    """

    def validate(self, password, user=None):
        username = getattr(user, "username", None)
        if username and password.lower() == username.lower():
            raise DjangoValidationError(
                "Parol foydalanuvchi nomi bilan bir xil bo'lishi mumkin emas.",
                code="password_same_as_username",
            )

        if len(set(password.lower())) <= 2:
            raise DjangoValidationError(
                "Parol juda oddiy — kamida 3 xil belgi ishlatilishi kerak.",
                code="password_too_simple",
            )

    def get_help_text(self):
        return (
            "Parolingiz foydalanuvchi nomi bilan bir xil bo'lmasligi va "
            "kamida 3 xil belgidan iborat bo'lishi kerak."
        )


def password_errors_uz(error):
    """Django parol validatorlari xabarlarini o'zbekchaga o'giradi (uz lokalida tarjimasi yo'q)"""
    messages = []
    for err in error.error_list:
        params = err.params or {}
        if err.code == "password_too_short":
            messages.append(f"Parol juda qisqa — kamida {params.get('min_length', 8)} ta belgi bo'lishi kerak.")
        elif err.code == "password_too_common":
            messages.append("Bu parol juda oddiy, boshqasini tanlang.")
        elif err.code == "password_entirely_numeric":
            messages.append("Parol faqat raqamlardan iborat bo'lmasligi kerak.")
        elif err.code == "password_same_as_username":
            messages.append("Parol foydalanuvchi nomi bilan bir xil bo'lishi mumkin emas.")
        elif err.code == "password_too_simple":
            messages.append("Parol juda oddiy — kamida 3 xil belgi ishlatilishi kerak.")
        else:
            messages.extend(err.messages)
    return " ".join(messages)


# O'chirilgan akkauntlar shu nom bilan qayta nomlanadi (User.close_account) — foydalanuvchi uni band qila olmaydi
RESERVED_USERNAME_PREFIX = "deleted_"


def normalize_login(value):
    """Login nomi yoki kirish identifikatorini bazada saqlanadigan ko'rinishga keltiradi: NFKC
    ("ＡＤＭＩＮ" -> "ADMIN", create_user ham shunday qiladi) va chetidagi bo'sh joylarsiz.
    Tekshiruv, qidiruv va urinishlar hisoblagichi shu ko'rinish bo'yicha yuritiladi"""
    from .models import User

    return User.normalize_username(str(value or "")).strip()


def username_error(username, exclude_pk=None):
    """Foydalanuvchi nomini tekshiradi (ro'yxatdan o'tish, profil, /users/ — hammasida bir xil qoida).
    Xato matnini yoki None qaytaradi"""
    from .models import USERNAME_TAKEN_MESSAGE, User

    # Nom bazaga normallashgan ko'rinishda tushadi — tekshiruv ham shu ko'rinishda: aks holda
    # "ＡＤＭＩＮ" "admin" bilan bir xil emas deb o'tib ketib, keyin "ADMIN" bo'lib saqlanardi
    username = normalize_login(username)
    if not username:
        return "Foydalanuvchi nomi bo'sh bo'lishi mumkin emas"
    if len(username) > 150:
        return "Foydalanuvchi nomi 150 belgidan oshmasligi kerak"
    try:
        User.username_validator(username)
    except DjangoValidationError:
        return "Foydalanuvchi nomida faqat harf, raqam va . + - _ belgilari bo'lishi mumkin"
    # "@" bor identifikator email deb qidiriladi (backends.find_user_by_login): begona odam qurbonning
    # "vera@gmail.com" loginini o'z emaili qilib qo'yib, uni kira olmaydigan qilib qo'ymasligi uchun
    if "@" in username:
        return "Foydalanuvchi nomida @ belgisi bo'lishi mumkin emas"
    if User.make_username_key(username).startswith(RESERVED_USERNAME_PREFIX):
        return f"\"{RESERVED_USERNAME_PREFIX}\" bilan boshlanadigan nomni tanlab bo'lmaydi"
    # username_key bo'yicha: SQL iexact kirillcha "Али" va "али"ni bir xil deb topmaydi
    taken = User.objects.filter(username_key=User.make_username_key(username))
    if exclude_pk:
        taken = taken.exclude(pk=exclude_pk)
    if taken.exists():
        return USERNAME_TAKEN_MESSAGE
    return None
