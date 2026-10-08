from django.core.exceptions import ValidationError as DjangoValidationError


class SimplePasswordValidator:
    """
    Yengillashtirilgan "oddiy parol" tekshiruvi. Parol faqat ikki holatda rad etiladi:
    1. Parol foydalanuvchi nomi bilan bir xil bo'lsa
    2. Parol 1 yoki 2 xil belgidan iborat bo'lsa (masalan "aaaaaaaa", "abababab")

    Django'ning CommonPasswordValidator o'rniga ishlatiladi — u juda qattiq edi
    va "password", "qwerty12" kabi parollarni ham rad qilardi.
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
