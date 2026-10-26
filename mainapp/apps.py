from django.apps import AppConfig


class MainappConfig(AppConfig):
    name = 'mainapp'

    def ready(self):
        # user_logged_in signali (kirish vaqtini sessiyaga yozish) ulanadi
        from . import middleware  # noqa: F401
        # SQLite'da kirillcha katta-kichik harfga qaramaydigan qidiruv uchun unicode_casefold funksiyasi
        from . import db_functions
        db_functions.install()
