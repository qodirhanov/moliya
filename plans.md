# 💰 Moliya (Kalkulator) — Loyiha Rejasi va Progress

> Bu fayl loyihaning qayerga kelganini kuzatib borish uchun.
> Oxirgi yangilangan: **2026-10-02 18:32**

---

## 📊 UMUMIY HOLAT — Bajarilgan Ishlar

| # | Bosqich / Modul | Holati | Sana |
|---|-----------------|--------|------|
| 1 | Modellarni to'liq qayta ishlash (User, Wallet, Income, Expense, Transfer, Debt, Category) | ✅ Bajarildi | 2026-10-01 |
| 2 | Biznes logikasi (balans, atomic update, rollback, soft-delete) | ✅ Bajarildi | 2026-10-01 |
| 3 | Serializer va API (validatsiyalar, munosabatlar, read_only user) | ✅ Bajarildi | 2026-10-01 |
| 4 | Views va URLlar (qidiruv, filtr, ordering, summary endpoint) | ✅ Bajarildi | 2026-10-01 |
| 5 | Hamyonlararo o'tkazma (`Transfer` moduli) | ✅ Bajarildi | 2026-10-01 |
| 6 | Qarzlar daftari (`Debt` moduli va `/repay/` endpoint) | ✅ Bajarildi | 2026-10-01 |
| 7 | Frontend — Zamonaviy Fintech Dashboard | ✅ Bajarildi | 2026-10-01 |
| 8 | CSRF + SECRET_KEY xavfsizlik (.env bilan) | ✅ Bajarildi | 2026-10-01 |
| 9 | Qarz balansini hamyonga avtomatik yozish (create/delete) | ✅ Bajarildi | 2026-10-01 |
| 10 | Login / Logout / Register (parol bilan autentifikatsiya) | ✅ Bajarildi | 2026-10-01 |
| 11 | Ko'p foydalanuvchilik (Multi-tenant, user-scoped data) | ✅ Bajarildi | 2026-10-01 |
| 12 | Tranzaksiyalar paginatsiyasi (15 tadan yuklash) | ✅ Bajarildi | 2026-10-01 |
| 13 | Kategoriya bo'yicha oylik harajatlar taqsimoti (📊 progress bars) | ✅ Bajarildi | 2026-10-01 |
| 14 | 7 kunlik chiziqli grafik dinamikasi (📈 Canvas bezier chart) | ✅ Bajarildi | 2026-10-01 |
| 15 | Grafik razmerini kichraytirish va qulaylashtirish | ✅ Bajarildi | 2026-10-01 |
| 16 | 401 sessiya tugashi — avtomatik login ekraniga qaytarish | ✅ Bajarildi | 2026-10-01 |
| 17 | Parol ko'z belgisi — bachkana emoji o'rniga vektorli SVG (`eye-show` / `eye-hide`) | ✅ Bajarildi | 2026-10-02 |
| 18 | Brauzer keshi (cache) boshqaruvi — static assetlarga versiya (`?v=2.2`) qo'shish | ✅ Bajarildi | 2026-10-02 |
| 19 | Brauzer yopilganda sessiyani yakunlash (`SESSION_EXPIRE_AT_BROWSER_CLOSE`) | ✅ Bajarildi | 2026-10-02 |
| 20 | Eski duplikat `modalAuth` ni tozalash va toza DOM arxitekturasi | ✅ Bajarildi | 2026-10-02 |
| 21 | Harajat modalida **Summa** maydonini 1-o'ringa ko'chirish (UX bir xilligi) | ✅ Bajarildi | 2026-10-02 |

---

## 🏗️ ARXITEKTURA

### Backend (Django + DRF)
- **Framework:** Django 5.x + Django REST Framework
- **DB:** SQLite (`db.sqlite3`)
- **Virtual env:** `myenv/` (Python 3.12)
- **Secret management:** `.env` fayl (`python-dotenv`)
- **Auth:** Django Session Authentication (cookie-based)
- **API prefix:** `/api/v1/`

### Fayl tuzilmasi
```
Newproject/
├── config/          # Django settings, urls, wsgi
│   ├── settings.py
│   └── urls.py
├── mainapp/         # Asosiy ilova
│   ├── models.py    # User, Wallet, Income, Expense, Transfer, Debt, Category, ExpenseCategory
│   ├── views.py     # Auth API + ViewSets + summary endpoint
│   ├── serializers.py
│   ├── urls.py      # Router + auth urls
│   └── admin.py
├── templates/
│   └── index.html   # SPA-style Dashboard (Auth + Main App)
├── static/
│   ├── css/style.css  # Premium dark fintech design system
│   └── js/app.js      # Vanilla JS frontend engine
├── .env             # SECRET_KEY, DEBUG
├── db.sqlite3       # Ma'lumotlar bazasi
├── plans.md         # ← SHU FAYL
└── requirements.txt
```

### API Endpointlar
| Method | URL | Tavsif |
|--------|-----|--------|
| POST | `/api/v1/auth/login/` | Tizimga kirish |
| POST | `/api/v1/auth/logout/` | Tizimdan chiqish |
| GET | `/api/v1/auth/me/` | Joriy foydalanuvchi holati |
| POST | `/api/v1/auth/register/` | Yangi foydalanuvchi ro'yxati |
| GET | `/api/v1/wallets/` | Hamyonlar ro'yxati |
| GET | `/api/v1/wallets/summary/` | Umumiy statistika (balans, kirim, chiqim, qarz, kategoriya taqsimoti, 7 kunlik trend) |
| CRUD | `/api/v1/incomes/` | Daromadlar |
| CRUD | `/api/v1/expenses/` | Harajatlar |
| CRUD | `/api/v1/transfers/` | O'tkazmalar |
| CRUD | `/api/v1/debts/` | Qarzlar |
| POST | `/api/v1/debts/{id}/repay/` | Qarzni to'lash |
| CRUD | `/api/v1/categories/` | Daromad kategoriyalari |
| CRUD | `/api/v1/expense-categories/` | Harajat kategoriyalari |

---

## 🎨 FRONTEND IMKONIYATLARI

### Autentifikatsiya ekrani (`#authSection`)
- **Login formasi** — username + password (vektorli SVG `eye-show` / `eye-hide` toggle bilan, bachkana emojilarsiz)
- **Register formasi** — username, password, ism, telefon
- **Tab switcher** — "Tizimga kirish" / "Ro'yxatdan o'tish"
- Login bo'lmaganda boshqa hech narsa ko'rinmaydi

### Asosiy Dashboard (`#mainApp`)
1. **Navbar:** Moliya logo, foydalanuvchi avatar/ismi, Chiqish tugmasi, Admin panel link
2. **Hero Balance Banner:** Indigo gradient karta — umumiy balans, kirim, harajat
3. **4 ta Tezkor Tugma:** Harajat, Kirim, O'tkazma, Qarz
4. **So'nggi Operatsiyalar:** Filter pills (Barchasi/Chiqim/Kirim/O'tkazma), clean list, "Yana yuklash" pagination
5. **Analitika Grid (2 ustunli):**
   - Oylik harajatlar taqsimoti — kategoriya nomi, summa, foiz, progress bar
   - 7 kunlik dinamika — compact canvas grafik (kirim=yashil, chiqim=qizil, bezier curves)
6. **Hamyonlar va Qarzlar:** Compact card'lar (balans, to'lash tugmasi)
7. **Modal dialog'lar:** Harajat, Kirim, O'tkazma, Qarz, Hamyon yaratish
   - Harajat va Kirim modallarida **Summa (so'm)** maydoni qulaylik uchun eng 1-o'rinda turadi

### Dizayn tizimi
- **Tema:** Premium dark (bg: #080c16, surface: #0f172a)
- **Shriftlar:** Plus Jakarta Sans + Outfit (Google Fonts)
- **Ranglar:** Indigo (#6366f1), Emerald (#10b981), Rose (#f43f5e), Cyan (#06b6d4), Amber (#f59e0b)
- **Effektlar:** Glassmorphism, gradient glow, bezier animatsiyalar, hover transitions, vector SVG icons
- **Kesh boshqaruvi:** Statik fayllar versiyalash bilan chaqiriladi (`?v=2.2`)

---

## 🔐 XAVFSIZLIK

- `SECRET_KEY` — `.env` faylda saqlanadi (git'ga tushmaydi)
- CSRF token — global fetch interceptor orqali avtomatik qo'shiladi
- Session Authentication — cookie-based, server-side
- `SESSION_EXPIRE_AT_BROWSER_CLOSE = True` — brauzer yopilishi bilan sessiya o'chiriladi va avtomatik akkauntdan chiqiladi
- User-scoped data — har bir foydalanuvchi faqat o'z ma'lumotlarini ko'radi
- 401 javob kelsa — avtomatik login ekraniga qaytaradi

---

## 👤 ADMIN HISOB

- **Username:** `admin`
- **Password:** `admin123`
- **Admin panel:** http://localhost:8000/admin/

---

## 🚀 ISHGA TUSHIRISH

```bash
cd c:\Users\User\Desktop\Kalkulator\Newproject
.\myenv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

- **Dashboard:** http://localhost:8000/
- **API:** http://localhost:8000/api/v1/
- **Admin:** http://localhost:8000/admin/

---

## 💡 KELGUSI REJALAR (Qilinishi mumkin bo'lgan ishlar)

- [ ] Parolni unutdim (Password reset)
- [ ] Profil sahifasi (ism, telefon, parolni o'zgartirish)
- [ ] Oylik byudjet limiti belgilash (va ogohlantirish)
- [ ] Kategoriyalarni tahrirlash/o'chirish interfeysi
- [ ] Valyuta konvertori (USD/EUR/RUB)
- [ ] Ma'lumotlarni Excel/PDF export qilish
- [ ] Mobil-responsive optimizatsiya (kichik ekranlar uchun)
- [ ] Telegram bot integratsiyasi
- [ ] Production deploy (Gunicorn + Nginx + PostgreSQL)
