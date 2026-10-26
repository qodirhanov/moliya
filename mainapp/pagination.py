from rest_framework.pagination import LimitOffsetPagination


class MaxLimitPagination(LimitOffsetPagination):
    """LimitOffsetPagination, lekin ?limit= yuqori chegaraga ega: aks holda ?limit=100000 bitta so'rovda butun jadvalni
    (har qatorga bir nechta SQL bilan) o'qitib, serverni band qilib qo'yardi. Standart sahifa hajmi o'zgarmagan (PAGE_SIZE).
    Chegara 200: frontend (static/js/app.js, _fetchAllPages) sahifalarni 200 tadan so'raydi va 200 dan kam qator kelganda
    to'xtaydi — chegara 200 dan kichik bo'lsa u 'oxirgi sahifa' deb oqibatda ma'lumotni kesib tashlardi"""
    max_limit = 200
