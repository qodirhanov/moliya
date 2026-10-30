# 💰 Moliya (Kalkulator) — Loyiha Rejasi va Progress

> Bu fayl loyihaning qayerga kelganini kuzatib borish uchun.
> Oxirgi yangilangan: **2026-10-30**

---

## 🐞 KAMCHILIKLAR VA XATOLAR (navbat bilan tuzatiladi)

> Tuzatilgan band shu ro'yxatdan o'chiriladi. Tartib — muhimligi bo'yicha.
> 2026-10-28: to'liq kod tekshiruvi (pul/balans, kirish/xavfsizlik, ovozli yordamchi, frontend) — topilgan 20 ta band qo'shildi; 5 ta Yuqori va «Qaysi hamyondan?» savolidagi maqsad hamyoni bandi shu kuni tuzatildi.

### O'rta
4. **Klaviaturada maqsad yoki doimiy to'lov kartochkasidagi tugma Enter bilan bosilmaydi.** Keydown handlerlari (`app.js:3891`, `app.js:4044`) `closest('[data-goal-id]')` bilan ichki tugmani ham ushlaydi va `preventDefault` qiladi. «+ Pul qo'shish» yoki o'chirish o'rniga tahrirlash oynasi ochiladi. Yechim: faqat kartochkaning o'zi (`e.target.matches(...)`).
5. **Faqat maqsad hamyonlari qolsa, chiqim/kirim qo'shib bo'lmaydi va xabar chiqmaydi.** Oxirgi oddiy hamyonni o'chirish mumkin: o'chirish tugmasi faqat `state.wallets.length > 1` ni tekshiradi (`app.js` walletCardHtml), server `destroy` ham tekshirmaydi. Shunda Chiqim/Kirim oynasida hamyon ro'yxati bo'sh qoladi va «Saqlash» jim ishlamaydi. Yechim: oxirgi oddiy hamyonni o'chirishni taqiqlash (frontend + server).
6. **«Pul qo'shish» bekor qilinsa, keyingi oddiy o'tkazmada maqsad ma'lumotlari qoladi.** `unlockTransferTarget()` (`app.js:4114`) faqat qulfni ochadi. Keyin «O'tkazma» bosilsa, «Qaysi hamyonga» = maqsad hamyoni va izoh «Maqsad: …» bo'lib turadi. Yechim: qulf ochilganda `formAddTransfer.reset()`.

### Past
7. **Parolni tiklash xati spamga tushadi.** Xat shaxsiy Gmail (`smtp.gmail.com`) orqali ketadi va har qanday manzilga yetadi, lekin yangi qabul qiluvchilarda Spam papkasiga tushishi mumkin (ekranda "spam papkasini ham tekshiring" eslatmasi bor). To'liq yechim — o'z domeningiz + Resend (SPF/DKIM), DEPLOY.md 163-qator; eski Resend sozlamasi `.env` da izoh sifatida turibdi. Gmail limiti — kuniga ~500 xat. Xat endi matn + HTML ko'rinishida (2026-10-21) — bu yordam berishi mumkin, lekin kafolat emas.
8. **"Dastur haqida" to'ldirilmagan.** Dasturchi ismi va kontaktlari `templates/index.html` dagi "Dastur haqida" blokida hozircha «—».
9. SQLite summalarni float'da qo'shadi: ko'p yozuvlarning **jami** ~10¹³ dan oshsa, tiyin noaniq bo'lishi mumkin (bitta summa ≤ 10¹² bo'lgani uchun alohida qiymatlar aniq). PostgreSQL'ga o'tilganda o'z-o'zidan yo'qoladi.
10. **JSON massiv yuborilsa auth endpointlari 500 qaytaradi.** `login_api`, `register_api`, `password_reset_request_api`, `login_2fa_api` va boshqa `request.data.get(...)` joylari (`views.py`, `support.py`): `POST /auth/login/` ga `[1,2]` yuborilsa `AttributeError` chiqadi. Yechim: `request.data` dict bo'lmasa 400.
11. **Email almashtirilganda eski manzilga yuborilgan parol tiklash kodi ishlab qoladi.** `profile_api` (`views.py:443`) va `confirm_email_api` (`views.py:921`) `password_reset_codes` ni bekor qilmaydi (`change_password_api` qiladi). Yechim: email saqlangach `user.password_reset_codes.filter(used=False).update(used=True)`.
12. **Django admin parol almashtirish formasi joriy parolni taxmin qilish limitini chetlab o'tadi.** `/<ADMIN_URL>/password_change/` `verify_current_password` (15 daqiqada 5 urinish) orqali o'tmaydi. Yechim: `clean_old_password` da `verify_current_password`.
13. **Doimiy to'lovlarni yozishda valyuta kursi tranzaksiya ichida olinadi.** `recurring.py:50-55`: `_operation_for(...).save()` atomic ichida, `prepare_uzs_rate` esa cbu.uz ga chiqishi mumkin (10 soniyagacha). SQLite'da shu payt boshqa yozuvlar kutib qoladi. Yechim: `prepare_uzs_rate(op)` ni atomic'dan oldin chaqirish.
15. **STT/TTS provayderi uzilib qolsa 500 xato.** `stt.py:78-86`, `tts.py:102-110`: `http.client.IncompleteRead` `OSError` emas, ushlanmaydi. STT'da JSON obyekt bo'lmasa `payload.get` ham yiqiladi. Yechim: `http.client.HTTPException` ni ham ushlash va `isinstance(payload, dict)`.
16. **Mikrofon ochilayotgan paytda yopilsa, yonib qolishi mumkin.** `voice.js:209-224`: `getUserMedia` kutilayotganda `releaseMicNow()` hech narsa qilmaydi, keyin kelgan oqim saqlanib qoladi (masalan, sahifa ochilishi bilan boshqa tabga o'tilsa). Yechim: so'rovdan keyin release bo'lgan bo'lsa, `.then` da oqimni darhol to'xtatish.

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
| 22 | Admin panel (`/panel/`): akkauntlar ro'yxati, qidiruv, filtrlar, akkaunt sahifasi | ✅ Bajarildi | 2026-10-15 |
| 23 | Kamchiliklar ro'yxatidagi 13 ta xato tuzatildi (oy bo'yicha operatsiyalar, ikki marta yuborish, hamyon o'chirish, `status` himoyasi va b.) | ✅ Bajarildi | 2026-10-15 |
| 24 | Chiqish/sessiya tugashida oldingi foydalanuvchi ma'lumotlari tozalanadi; o'chirilgan hamyon yozuvlarini bekor qilish taqiqlandi | ✅ Bajarildi | 2026-10-15 |
| 25 | Yangi navbar va "Oltin" rang mavzusi (to'q ko'k + oltin) | ✅ Bajarildi | 2026-10-16 |
| 26 | Tor telefonlarda navbar, ro'yxatdan o'tishda email, Esc va telefon "orqaga" tugmasi, oynalarda fokus | ✅ Bajarildi | 2026-10-16 |
| 27 | Segmentli tugmalar (Sozlamalar, kirish, toifalar, bo'lim filtrlari) yangi kapsula uslubida | ✅ Bajarildi | 2026-10-20 |
| 28 | Davr filtri: tezkor davrlar va "dan — gacha" oralig'i (`date_from` / `date_to`, statistika ham) | ✅ Bajarildi | 2026-10-20 |
| 29 | Kamchiliklar ro'yxatidagi 24 ta band tuzatildi: login bloklash va Unicode nomlar, xodim/superuser himoyasi, tahrirda balans (faqat farq qo'llanadi), qarz tahriri, `/repay/` tekshiruvi, parol tiklashda akkaunt sir saqlanishi, xavfsizlik logi, panel 404, N+1 so'rovlar va `limit` ≤ 200, frontend mayda xatolari (testlar: 364 ta) | ✅ Bajarildi | 2026-10-21 |
| 30 | Har bir daromad/harajatning so'mdagi kursi (`uzs_rate`) yozilgan kuni saqlanadi — o'tgan oylar statistikasi endi kundan-kunga o'zgarmaydi (eski yozuvlarga 2026-10-21 kursi yozildi; testlar: 380 ta) | ✅ Bajarildi | 2026-10-21 |
| 31 | Login nomlari kirill harflarida ham katta-kichikka qaramay yagona (`username_key`): "Али" va "али" bitta akkaunt, kirish va bloklash hisoblagichi ham umumiy (testlar: 411 ta) | ✅ Bajarildi | 2026-10-21 |
| 32 | `/users/` da parallel so'rovdagi login to'qnashuvi 500 o'rniga 400 beradi; `/users/?search=` va paneldagi qidiruv kirill harflarida katta-kichikni farqlamaydi; band login xabari o'zbekcha (testlar: 438 ta) | ✅ Bajarildi | 2026-10-21 |
| 33 | O'tkazma kursi 0 ga yaxlitlanib saqlanmaydi: kursning pastki chegarasi 0.00000001, undan kichigi tushunarli xato bilan rad etiladi (testlar: 446 ta) | ✅ Bajarildi | 2026-10-21 |
| 34 | "Shisha" (Liquid Glass) tugmacha: navbar bo'limlari va barcha segmentli tugmalarda tanlov linzaga aylanib prujinali suzadi, barmoq/sichqoncha bilan surib tanlash mumkin (`app.js: initGlassTrack`) | ✅ Bajarildi | 2026-10-21 |
| 35 | Sessiya "Chiqish" bosilguncha saqlanadi: brauzer/ilova yopilganda va 12/24 soatdan keyin ham parol so'ralmaydi (testlar: 454 ta) | ✅ Bajarildi | 2026-10-21 |
| 36 | "Barcha qurilmalardan chiqish" tugmasi (Sozlamalar → Profil): shu va boshqa barcha qurilmalardagi sessiyalar yopiladi (`/api/v1/auth/logout-all/`, `User.session_epoch`; testlar: 463 ta) | ✅ Bajarildi | 2026-10-21 |
| 37 | Parolni tiklash xati Resend sinov manzili o'rniga Gmail SMTP (App parol) orqali yuboriladi — endi har qanday foydalanuvchi pochtasiga yetadi; App paroldagi bo'sh joylar avtomatik olib tashlanadi (testlar: 463 ta) | ✅ Bajarildi | 2026-10-21 |
| 38 | Admin o'chirgan akkaunt ham foydalanuvchi o'zi o'chirgandagidek tozalanadi (ism, email, telefon, parol; login nomi bo'shaydi) — `User.delete()` → `close_account()`; avval o'chirilgan 8 ta akkaunt ham tozalandi (migratsiya 0021) | ✅ Bajarildi | 2026-10-21 |
| 39 | Summalarda tiyin/sent: barcha valyutalarda 2 xonali kasr (`DecimalField(15,2)`, migratsiya 0022), eng kichigi 0.01, eng kattasi 1 000 000 000 000; balans yangilanishi `Round(…, 2)` bilan; frontendda `readAmount()` va brauzerga bog'liq bo'lmagan son formati (testlar: 491 ta) | ✅ Bajarildi | 2026-10-21 |
| 40 | "Muzlatilgan shisha" (iOS tab bar uslubi): navbar shaffof, ostidan sahifa xira ko'rinadi (`backdrop-filter` alohida `::before` qatlamda), tanlangan bo'lim yorqinroq shisha tugmacha; segmentli tugmalar, davr tanlash, oynalar, toast, ochiladigan ro'yxatlar, Xabarlar paneli ham shu uslubda. `--glass-*` o'zgaruvchilari — 5 rang mavzusi va ikkala rejimda; xiralashtirish yo'q brauzerda va `prefers-reduced-transparency` da fon to'liq yopiq (style.css v10.13) | ✅ Bajarildi | 2026-10-21 |
| 41 | Navbarda "Moliya" (bosh sahifa) Kirim / Chiqim / Qarz bilan bitta shisha kapsulada: kirilgandan keyin alohida logotip yashiriladi, bosh sahifada (statistika, hamyon sahifalarida ham) "Moliya" tanlangan bo'ladi, bosilsa ochiq sahifa yopiladi (`setNavActive`, style.css v10.14, app.js v3.76) | ✅ Bajarildi | 2026-10-21 |
| 42 | Sozlamalarga 3 bo'lim: **Moliya yordamchisi** — bepul: savolga `assistant_knowledge.md` (Ma'lumotnoma nusxasi) dan kalit so'z qidiruvi bilan javob topadi (`mainapp/faq.py`: qo'shimchasiz solishtirish, sinonimlar, kirill yozuv); `.env` da `ANTHROPIC_API_KEY` bo'lsa ixtiyoriy ravishda Claude javob beradi (pullik, 30/soat, model nomi ko'rsatilmaydi), **Yordam** — admin bilan chat (`SupportMessage`, migratsiya 0025, polling; admin javobi `panel/support/`, navbar qo'ng'irog'ida "Admin javob berdi"; yangi xabar haqida adminlarga email — admin o'qimaguncha qayta yuborilmaydi, manzillar `SUPPORT_NOTIFY_EMAILS` yoki panelga kira oladigan xodimlar emaili), **Dastur haqida** (style.css v10.41, app.js v3.98, panel.css v7, i18n v10) | ✅ Bajarildi | 2026-10-23 |
| 43 | Kamchiliklar ro'yxatidagi 6 ta band tuzatildi: 2FA yoqilganda yangi email kod bilan tasdiqlanadi (`/auth/profile/confirm-email/`, `LoginCode.new_email`, migratsiya 0028; kod maqsadlari ajratilgan), 2FA kodi urinishi tekshiruvdan oldin bazada band qilinadi (parallel so'rovlar limitni aylanib o'tmaydi), o'tgan sanadagi operatsiyaga o'sha kungi CBU kursi yoziladi (arxiv keshlanadi), sessiya har so'rovda emas kuniga bir marta yangilanadi (`SessionRefreshMiddleware`), yordamchi tarixi qisqartiriladi, kod git'ga commit qilindi (testlar: 587 ta; app.js v4.12, i18n v21) | ✅ Bajarildi | 2026-10-26 |
| 44 | Kod tekshiruvidagi 5 ta Yuqori band tuzatildi: Django admin kirishida 2FA chetlab o'tilmaydi (`TwoFactorAdminAuthenticationForm`), `/api/v1/users/` da xodimga `view/change/delete_user` huquqi kerak va boshqa xodim akkauntini faqat superuser o'zgartiradi, yozuvni parallel ikki marta o'chirish pulni ikki marta qaytarmaydi (qator atomik egallanadi), ovozda maqsad hamyoni nomi tanlangan hamyondan ustun kelmaydi, «45.000» minglik ajratgich bilan o'qiladi, «Qaysi hamyondan?» savolida maqsad hamyoni taklif qilinmaydi (testlar: 681 ta) | ✅ Bajarildi | 2026-10-28 |
| 45 | Maqsad o'chirilsa uning hamyoni ham o'chadi: hamyonda pul bo'lsa, avval qaysi oddiy hamyonga o'tkazilishi so'raladi (boshqa valyutaga Markaziy bank kursi bo'yicha), pul O'tkazma bilan o'tadi, so'ng hamyon o'chadi; eski (oddiy hamyonga bog'langan) maqsadda hamyon joyida qoladi (testlar: 685 ta; app.js v4.28, i18n v29) | ✅ Bajarildi | 2026-10-28 |
| 46 | O'tkazmada «Qaysi hamyonga» ro'yxatida «Qaysi hamyondan» da tanlangan hamyon ko'rinmaydi (Bank → Bank tanlab bo'lmaydi; `syncTransferTargets`); shu bilan «Naqd → Naqd» standart tanlovi ham yo'qoldi (app.js v4.29) | ✅ Bajarildi | 2026-10-28 |
| 47 | Hamyonni tahrirlashda qoldiqni ham o'zgartirish mumkin («Hamyondagi pul»): summa to'g'ridan-to'g'ri almashtiriladi, kirim/chiqim yozilmaydi (foydalanuvchi qarori — tarixdagi amallar yig'indisi qoldiqqa mos kelmasligi mumkin); maqsad hamyoni avvalgidek tahrirlanmaydi (testlar: 686 ta; app.js v4.30, i18n v30) | ✅ Bajarildi | 2026-10-28 |
| 48 | Navbardagi «Moliya» bosilsa ochiq bo'lim sahifasi yopiladi, bosh sahifa eng tepaga chiqadi va ma'lumotlar serverdan yangilanadi — tortib yangilashdagi logotip kapsulasi ko'rinadi (`goHome`, `_ptrRefresh`; app.js v4.31, i18n v31) | ✅ Bajarildi | 2026-10-28 |
| 49 | Moliya yordamchisiga Google Gemini ulandi: `.env` da `GEMINI_API_KEY` bo'lsa Gemini javob beradi (tekin rejasi bor; model `GEMINI_MODEL`, standart `gemini-3.6-flash`), `ANTHROPIC_API_KEY` bo'lsa Claude ustun, ikkalasi ham bo'lmasa bepul `faq.py`. REST API (kutubxonasiz), kalit sarlavhada (testlar: 691 ta) | ✅ Bajarildi | 2026-10-28 |
| 50 | Qo'llanma to'ldirildi: Kurs sahifasi va kalkulyator, admin bilan chat, maqsad hamyonini o'chirish; «Ilova haqida → Imkoniyatlar» yangilandi; Ovozli yordamchi bo'limi 6 tilga tarjima qilindi (buyruq misollari o'zbekcha qoladi; app.js v4.42, i18n v35) | ✅ Bajarildi | 2026-10-30 |
| 51 | Serverga chiqish tayyorgarligi: doimiy to'lov yoki maqsadi bor hamyon valyutasi qulflanadi; jadval o'zgarsa bugungi to'lov qayta yozilmaydi; ovozda «3 marta» sana emas, «20 ming 2 kishiga» 20 002 emas, «3 kun oldin» o'tgan sana; DEPLOY.md: gunicorn `--threads 4 --timeout 120`, nginx `6m` va `proxy_read_timeout 120s`, boshlang'ich HSTS 1 soat (testlar: 730 ta) | ✅ Bajarildi | 2026-10-30 |

---

## 🏗️ ARXITEKTURA

### Backend (Django + DRF)
- **Framework:** Django 6.1 + Django REST Framework
- **DB:** SQLite (`db.sqlite3`, WAL rejimi); zaxiralar `Kalkulator/backups/` da
- **Virtual env:** `myenv/` (Python 3.12)
- **Secret management:** `.env` fayl (`python-dotenv`), namuna — `.env.example`
- **Auth:** Django Session Authentication (cookie), login yoki email bilan kirish
- **Valyuta kursi:** O'zbekiston Markaziy banki (cbu.uz), `ExchangeRate` jadvalida saqlanadi
- **API prefix:** `/api/v1/`

### Fayl tuzilmasi
```
Newproject/
├── config/              # settings.py, urls.py, wsgi.py
├── mainapp/
│   ├── models.py        # User, Wallet, Member, Category, ExpenseCategory, Income, Expense, Transfer, Debt, ...
│   ├── serializers.py
│   ├── views.py         # Auth API + ViewSet'lar + statistika
│   ├── panel.py         # Admin panel (/panel/) — akkauntlar haqida ma'lumot
│   ├── currency.py      # Markaziy bank kursi va valyuta o'girish
│   ├── backends.py      # Login/email bilan kirish, urinishlar cheklovi
│   ├── middleware.py    # Sessiyaning mutlaq muddati
│   ├── templatetags/    # Panel uchun o'zbekcha sana filtrlari
│   └── tests.py
├── templates/
│   ├── index.html       # Asosiy ilova (SPA)
│   └── panel/           # Admin panel sahifalari
├── static/
│   ├── css/style.css, css/panel.css
│   └── js/app.js, js/theme-init.js
├── DEPLOY.md            # Serverga joylash yo'riqnomasi
└── plans.md             # ← SHU FAYL
```

### API Endpointlar
| Method | URL | Tavsif |
|--------|-----|--------|
| POST | `/api/v1/auth/login/`, `/auth/logout/`, `/auth/register/` | Kirish, chiqish, ro'yxatdan o'tish |
| GET | `/api/v1/auth/me/` | Joriy foydalanuvchi |
| PATCH / POST | `/api/v1/auth/profile/`, `/auth/change-password/`, `/auth/delete-account/` | Sozlamalar |
| POST | `/api/v1/auth/password-reset/` (+ `verify/`, `confirm/`) | Parolni email orqali tiklash |
| CRUD | `/api/v1/wallets/` (+ `summary/`) | Hamyonlar va umumiy statistika |
| CRUD | `/api/v1/incomes/`, `/expenses/`, `/transfers/` | Operatsiyalar (`?year=&month=` yoki `?date_from=&date_to=` — YYYY-MM-DD, ikkala kun ham kiradi) |
| CRUD | `/api/v1/debts/` (+ `{id}/repay/`) | Qarzlar daftari |
| CRUD | `/api/v1/members/` | A'zolar (xarajat kimga) |
| CRUD | `/api/v1/categories/`, `/expense-categories/` (+ `{id}/restore/`) | Daromad va harajat toifalari |
| GET | `/api/v1/stats/monthly/?year=&month=` yoki `?date_from=&date_to=` | Oy yoki oraliq statistikasi (oraliq ≤ 366 kun, aks holda 400) |
| GET | `/api/v1/rates/convert/?from=&to=&amount=` | Valyuta kalkulyatori |

---

## 🎨 FRONTEND IMKONIYATLARI

- **Kirish ekrani:** login (yoki email) + parol, ro'yxatdan o'tish, parolni email orqali tiklash
- **Navbar:** Kirim / Chiqim / Qarz bo'limlari, profil (Sozlamalar), tema, xabarlar, adminlar uchun Admin panel belgisi
- **Bosh sahifa:** umumiy balans (valyutalar bo'yicha), tezkor tugmalar (Harajat, Kirim, O'tkazma, Qarz), so'nggi operatsiyalar, hafta kunlari bo'yicha harajat, hamyonlar, qarzlar, a'zolar
- **Bo'lim sahifalari:** barcha operatsiyalar va statistika (oy, tezkor davr yoki "dan — gacha" oralig'i bo'yicha), qarzlar tarixi, hamyon sahifasi
- **Dizayn:** "Ledger Light" — och fon va moy-yashil urg'u, qorong'u rejim va 5 ta rang mavzusi
- **Kesh boshqaruvi:** statik fayllar versiya bilan chaqiriladi (`style.css?v=…`, `app.js?v=…`)

---

## 🔐 XAVFSIZLIK

- `SECRET_KEY` — `.env` faylda saqlanadi (git'ga tushmaydi)
- CSRF token — global fetch interceptor orqali avtomatik qo'shiladi; Content-Security-Policy inline skriptlarni bloklaydi
- Login va joriy parolni tekshirish: 15 daqiqada (akkaunt + IP) bo'yicha 5 ta, akkaunt bo'yicha jami 30 ta, bitta IP dan jami 30 ta noto'g'ri urinishdan keyin bloklanadi
- Parol tiklash javoblari akkaunt bor-yo'qligini oshkor qilmaydi; xat fonda yuboriladi
- Xavfsizlik hodisalari (kirish, bloklash, parol tiklash/o'zgartirish, akkaunt o'chirish) `security` logger'iga IP bilan yoziladi
- Sessiya: brauzer/ilova yopilsa ham saqlanadi; parol faqat "Chiqish" bosilgach yoki parol almashgach (boshqa qurilmalar chiqib ketadi) qayta so'raladi; Sozlamalardagi "Barcha qurilmalardan chiqish" hamma joydagi sessiyalarni yopadi. Sessiya 1 yil umuman ochilmasa tugaydi (`SESSION_MAX_AGE` ga son qo'yilsa mutlaq muddat qayta yoqiladi)
- Har bir foydalanuvchi faqat o'z ma'lumotlarini ko'radi; 401 javobida kirish ekraniga qaytaradi

---

## 👤 ADMIN

- Admin akkaunt `python manage.py createsuperuser` bilan yaratiladi. Parollar bu faylga yozilmaydi.
- **Admin panel (akkauntlar haqida ma'lumot):** `.env` dagi `PANEL_URL` manzili (standart: http://localhost:8000/panel/) — faqat superuser yoki `view_user` ruxsati bor xodimlar. Kirmagan odamga oddiy 404 chiqadi: avval bosh sahifada (yoki Django admin'da) kiring, keyin panel manzilini oching. Navbarda havola yo'q
- **Django admin (tahrirlash):** `.env` dagi `ADMIN_URL` manzili (standart: http://localhost:8000/admin/)

---

## 🚀 ISHGA TUSHIRISH

```bash
cd c:\Users\User\Desktop\Kalkulator\Newproject
.\myenv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

- **Dashboard:** http://localhost:8000/
- **API:** http://localhost:8000/api/v1/
- Serverga joylash: `DEPLOY.md`

---

## 💡 KELGUSI REJALAR (Qilinishi mumkin bo'lgan ishlar)

- [ ] Oylik byudjet limiti belgilash (va ogohlantirish)
- [ ] Operatsiyalarni tahrirlash (hozir faqat o'chirish mumkin)
- [ ] Ma'lumotlarni Excel/PDF export qilish
- [ ] Telegram bot integratsiyasi
- [ ] Production: PostgreSQL ga o'tish
