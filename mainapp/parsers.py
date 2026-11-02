import json

from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser


class ObjectJSONParser(JSONParser):
    """API faqat JSON obyekt qabul qiladi. Aks holda `[1, 2]` yuborilganda request.data.get(...) yiqilib, view'lar 500
    qaytarardi. Har bir view'da tekshirish o'rniga shu yerda: yangi endpointlar ham avtomatik himoyalanadi.
    Yolg'iz surrogat belgisi (JSON'dagi u-d800 escape'i) ham rad etiladi: JSON uni qabul qiladi, lekin UTF-8 ga
    o'girilmaydi — bazaga yozish yoki so'rovga qo'yishda UnicodeEncodeError bo'lib, login, ro'yxatdan o'tish va profil
    500 xato qaytarardi"""
    def parse(self, stream, media_type=None, parser_context=None):
        try:
            data = super().parse(stream, media_type, parser_context)
        except RecursionError:
            # Juda chuqur ichma-ich JSON ("[[[[...") json.loads'ni yiqitadi — DRF faqat ValueError'ni ushlaydi
            raise ParseError("So'rov tanasi juda murakkab (ichma-ich daraja haddan ortiq)")
        if not isinstance(data, dict):
            raise ParseError("So'rov tanasi JSON obyekt bo'lishi kerak")
        try:
            # Kalitlar va qiymatlar bitta o'tishda tekshiriladi (ensure_ascii=False: surrogatlar o'z holicha qoladi)
            json.dumps(data, ensure_ascii=False).encode("utf-8")
        except UnicodeEncodeError:
            raise ParseError("So'rovda yaroqsiz Unicode belgi bor")
        except RecursionError:
            raise ParseError("So'rov tanasi juda murakkab (ichma-ich daraja haddan ortiq)")
        return data
