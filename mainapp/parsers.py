from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser


class ObjectJSONParser(JSONParser):
    """API faqat JSON obyekt qabul qiladi. Aks holda `[1, 2]` yuborilganda request.data.get(...) yiqilib, view'lar 500
    qaytarardi. Har bir view'da tekshirish o'rniga shu yerda: yangi endpointlar ham avtomatik himoyalanadi"""
    def parse(self, stream, media_type=None, parser_context=None):
        data = super().parse(stream, media_type, parser_context)
        if not isinstance(data, dict):
            raise ParseError("So'rov tanasi JSON obyekt bo'lishi kerak")
        return data
