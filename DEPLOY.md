# Serverga chiqarish (deploy) — qadamma-qadam

Misollarda domen `moliya.uz`, server foydalanuvchisi `moliya`, loyiha papkasi `/home/moliya/app`.
O'zingiznikiga almashtiring.

**Kerak bo'ladi:** Ubuntu **24.04** VPS (Django 6.1 Python 3.12+ talab qiladi — 22.04 to'g'ri kelmaydi),
domen, Resend akkaunti. 1 GB RAM yetadi.

> Render/Railway kabi bepul hostinglarda disk har qayta ishga tushganda tozalanadi — SQLite bazasi
> yo'qoladi. Ulardan foydalansangiz, doimiy disk yoki PostgreSQL kerak. VPS'da bunday muammo yo'q.

---

## 0. Kompyuteringizda: kodni git'ga yuborish

Serverga faqat commit qilingan kod tushadi. Avval `git status` ni tekshiring: ro'yxatda fayl qolgan bo'lsa
(ayniqsa yangi migratsiyalar), serverda sayt ishlamasligi mumkin. Maxfiy fayllar (`.env`, baza, `*.bak`) `.gitignore` da,
git'ga tushmaydi.

```bash
git add -A
git commit -m "Serverga chiqarishdan oldingi o'zgarishlar"
```

GitHub'da **Private** repozitoriy oching va yuboring:

```bash
git remote add origin https://github.com/<login>/moliya.git
git push -u origin main
```

## 1. Domen

Domen sotuvchisining DNS panelida ikkita **A** yozuv qo'shing — ikkalasi ham server IP manziliga:
`moliya.uz` va `www.moliya.uz`. Tarqalishi 5 daqiqadan bir necha soatgacha.

## 2. Serverni tayyorlash (root sifatida)

```bash
apt update && apt upgrade -y
apt install -y python3-venv python3-dev git nginx sqlite3 certbot python3-certbot-nginx
adduser moliya
ufw allow OpenSSH && ufw allow "Nginx Full" && ufw --force enable
```

SSH'ga parol o'rniga kalit bilan kirishni sozlash tavsiya etiladi (`ssh-copy-id`, so'ng
`/etc/ssh/sshd_config` da `PasswordAuthentication no`).

## 3. Loyihani o'rnatish (`moliya` foydalanuvchisi sifatida: `su - moliya`)

```bash
git clone https://github.com/<login>/moliya.git /home/moliya/app
cd /home/moliya/app
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

Repozitoriy private bo'lgani uchun `git clone` parol o'rniga GitHub tokenini so'raydi:
GitHub → Settings → Developer settings → Personal access tokens (faqat shu repo, faqat o'qish huquqi).

## 4. `.env` (serverda yangidan yoziladi, kompyuterdagini nusxalamang)

Yangi maxfiy kalit:

```bash
venv/bin/python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

`/home/moliya/app/.env`:

```env
SECRET_KEY=<yuqoridagi buyruq bergan kalit>
DEBUG=False
ALLOWED_HOSTS=moliya.uz,www.moliya.uz
CSRF_TRUSTED_ORIGINS=https://moliya.uz,https://www.moliya.uz
ADMIN_URL=<taxmin qilib bo'lmaydigan nom, masalan boshqaruv-7x2k>
PANEL_URL=<taxmin qilib bo'lmaydigan nom, masalan nazorat-4m9q>
BEHIND_PROXY=True
# Birinchi kunlar uchun 1 soat. Sayt bir necha kun HTTPS'da barqaror ishlagach 31536000 (1 yil) qiling:
# brauzer HSTS'ni eslab qoladi va uni serverdan bekor qilib bo'lmaydi
SECURE_HSTS_SECONDS=3600

EMAIL_HOST=smtp.resend.com
EMAIL_PORT=587
EMAIL_HOST_USER=resend
EMAIL_HOST_PASSWORD=<Resend API kaliti>
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=Moliya <noreply@moliya.uz>
```

Faylni faqat egasi o'qisin:

```bash
chmod 600 /home/moliya/app/.env
```

## 5. Baza, statik fayllar, admin

```bash
venv/bin/python manage.py migrate
venv/bin/python manage.py collectstatic --noinput
venv/bin/python manage.py seed_data
venv/bin/python manage.py createsuperuser
venv/bin/python manage.py check --deploy
```

- Baza serverda **yangidan** yaratiladi — kompyuterdagi `db.sqlite3` ni ko'chirmang (unda test akkauntlar bor).
- `createsuperuser` da kamida 12 belgili, boshqa joyda ishlatilmagan parol qo'ying.
- `check --deploy` da faqat `W005` / `W021` (HSTS subdomen/preload) qolishi normal.

## 6. Gunicorn (systemd xizmati, root sifatida)

`/etc/systemd/system/moliya.service`:

```ini
[Unit]
Description=Moliya (gunicorn)
After=network.target

[Service]
User=moliya
WorkingDirectory=/home/moliya/app
ExecStart=/home/moliya/app/venv/bin/gunicorn config.wsgi:application --workers 3 --threads 4 --timeout 120 --bind 127.0.0.1:8000 --access-logfile -
Restart=always

[Install]
WantedBy=multi-user.target
```

`--threads` va `--timeout` shart: AI yordamchi javobi 60 soniyagacha kutishi mumkin. Standart 30 soniyada worker
o'ldirilib foydalanuvchi 502 olardi, thread'larsiz esa 3 ta sekin so'rov butun saytni band qilardi.

```bash
systemctl daemon-reload && systemctl enable --now moliya
```

## 7. Nginx va HTTPS (root sifatida)

`/etc/nginx/sites-available/moliya`:

```nginx
server {
    listen 80;
    server_name moliya.uz www.moliya.uz;
    client_max_body_size 6m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_read_timeout 120s;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

`client_max_body_size` ovoz yozuvi limitidan (`stt.py`: 5 MB) katta bo'lishi kerak, aks holda uzun yozuv 413 xato
beradi. `proxy_read_timeout` gunicorn `--timeout` ga mos: standart 60 soniya AI javobini kesib qo'yishi mumkin.

`X-Forwarded-For` va `X-Forwarded-Proto` qatorlari shart: birinchisisiz so'rovlar cheklovi barcha
foydalanuvchilarni bitta IP deb hisoblaydi (bir kishining ko'p urinishi hammani to'sib qo'yadi),
ikkinchisisiz sayt HTTPS'ga cheksiz yo'naltirishga tushib qoladi.

```bash
ln -s /etc/nginx/sites-available/moliya /etc/nginx/sites-enabled/ && rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
certbot --nginx -d moliya.uz -d www.moliya.uz --redirect
```

Certbot sertifikatni o'zi yangilab turadi. CSS/JS ni WhiteNoise beradi — nginx'da `/static/` shart emas.

## 8. Pochta (parolni tiklash kodi)

Resend → Domains → **Add domain** → `moliya.uz`. Ko'rsatilgan DNS yozuvlarini (SPF/DKIM — TXT va MX)
domen panelingizga qo'shing va **Verify** ni bosing. Tasdiqlanmaguncha xat faqat Resend akkaunti
egasiga yetadi. Keyin xizmatni qayta ishga tushiring:

```bash
systemctl restart moliya
```

Xat fon oqimida yuboriladi va javob akkaunt borligidan qat'i nazar bir xil — pochta ishlamasa foydalanuvchi xato
ko'rmaydi, faqat logda `Parol tiklash xatini yuborib bo'lmadi` yoziladi (`journalctl -u moliya | grep "yuborib bo'lmadi"`).

## 9. Zaxira nusxa (har kecha, `moliya` foydalanuvchisining crontab'i)

```bash
mkdir -p /home/moliya/backups && crontab -e
```

Qo'shiladigan qator (14 kundan eski nusxalar o'chadi):

```cron
0 3 * * * cd /home/moliya/app && sqlite3 db.sqlite3 ".backup '/home/moliya/backups/db-$(date +\%F).sqlite3'" && find /home/moliya/backups -name 'db-*.sqlite3' -mtime +14 -delete
```

Vaqti-vaqti bilan bir nusxani serverdan tashqariga ham yuklab oling. Nusxalarda foydalanuvchilar
ma'lumotlari bor — hech kimga bermang.

### Eskirgan sessiyalarni tozalash (haftasiga bir marta)

Django muddati o'tgan sessiyalarni o'zi o'chirmaydi — `django_session` jadvali o'sib boradi
(har so'rovda sessiya yangilangani uchun tez). Uni `clearsessions` buyrug'i tozalaydi.

Linux — yuqoridagi `moliya` crontab'iga qator qo'shing (har yakshanba 03:30):

```cron
30 3 * * 0 cd /home/moliya/app && venv/bin/python manage.py clearsessions
```

Windows — Task Scheduler (loyiha `C:\moliya\app`, virtual muhit `myenv` bo'lsa; yo'llarni o'zingiznikiga almashtiring):

```bat
schtasks /Create /SC WEEKLY /D SUN /ST 03:30 /TN "Moliya clearsessions" /TR "cmd /c cd /d C:\moliya\app && myenv\Scripts\python.exe manage.py clearsessions"
```

## 10. Tekshiruv

- `https://moliya.uz` ochiladi, `http://` avtomatik `https://` ga o'tadi.
- Ro'yxatdan o'tish, kirish, daromad/harajat qo'shish ishlaydi.
- "Parolni unutdingizmi?" — kod boshqa pochta manziliga ham keladi.
- `https://moliya.uz/<ADMIN_URL>/` ochiladi, `/admin/` esa 404.
- Xatolar: `journalctl -u moliya -f`
- Xavfsizlik hodisalari (noto'g'ri kirish, bloklash, parol tiklash/o'zgartirish, akkaunt o'chirish):
  `journalctl -u moliya | grep security`. Qatorlarda login nomi va mijoz IP'si bor (`ip='...'`) — IP
  hammada `127.0.0.1` bo'lib chiqsa, proksi sarlavhalari yetib kelmayapti (nginx qatorlari yoki, Windows'da,
  waitress'ning `--trusted-proxy` bayrog'i, pastga qarang). Parol va tiklash kodi logga yozilmaydi.

## Keyinchalik yangilash

Kompyuterda `git push` qilgandan keyin serverda (`moliya` sifatida):

```bash
cd /home/moliya/app && git pull && venv/bin/pip install -r requirements.txt && venv/bin/python manage.py migrate && venv/bin/python manage.py collectstatic --noinput
```

So'ng root sifatida:

```bash
systemctl restart moliya
```

Yangilashdan oldin bazaning nusxasini oling (9-bo'lim buyrug'ini qo'lda ishga tushiring).

---

## Mobil ilova va bot haqida

Sayt va PWA/WebView ilova hozirgi cookie-sessiya bilan ishlaydi. Alohida native ilova
(Flutter, React Native) va Telegram bot uchun quyidagilar hali yo'q:

- token autentifikatsiya (masalan, JWT) — cookie + CSRF faqat brauzerda ishlaydi;
- bot uchun: Telegram akkauntini saytdagi akkauntga xavfsiz bog'lash (bir martalik kod),
  bot tokenini `.env` da saqlash va webhook so'rovlarini maxfiy kalit bilan tekshirish.

## Admin panel

Admin barcha foydalanuvchilarning moliyaviy ma'lumotlarini ko'radi: kuchli parol qo'ying,
`ADMIN_URL` va `PANEL_URL` ni o'zgartiring va admin akkauntlarini kam tuting.
Akkauntlar paneliga navbarda havola yo'q — xodim `https://moliya.uz/<PANEL_URL>/` manzilini o'zi ochadi.

Panelga kirish uchun akkaunt `is_staff` bo'lishi **va** superuser yoki `mainapp | Foydalanuvchi | Can view`
(`view_user`) ruxsatiga ega bo'lishi kerak (admin → Foydalanuvchilar yoki Guruhlar orqali beriladi).
Ruxsati yo'q har bir kishiga — kirmagan odamga ham — panel manzili mavjud bo'lmagan sahifa kabi 404 beradi
(yo'naltirish `PANEL_URL` borligini oshkor qilardi). Shuning uchun xodim **avval** saytda (yoki
`https://moliya.uz/<ADMIN_URL>/` da) tizimga kiradi, so'ng panel manzilini ochadi.

## Ixtiyoriy sozlamalar

- `REDIS_URL=redis://127.0.0.1:6379/1` — ko'p foydalanuvchi bo'lsa (`apt install redis-server`,
  `venv/bin/pip install redis`). Berilmasa hisoblagichlar bazada saqlanadi: SQLite bilan bir nechta
  worker'da ham to'g'ri sanaladi (yozish qulfi tufayli), lekin ma'lumotlar bazasi PostgreSQL kabi
  boshqasiga almashtirilsa `REDIS_URL` majburiy.
- `migrate` 0014 migratsiyasi katta-kichik harfigina farq qiladigan foydalanuvchi nomlari ("Ali" va "ali")
  bo'lsa xato beradi va to'qnashgan nomlarni ko'rsatadi — birini qayta nomlab, qayta ishga tushiring.
- `SECURE_HSTS_INCLUDE_SUBDOMAINS=True` — faqat barcha subdomenlar HTTPS bilan ishlasa.
## Windows server (waitress)

gunicorn Windows'da ishlamaydi — o'rniga waitress. Proksi (nginx, IIS+ARR, Caddy) orqasida u **faqat
quyidagi bayroqlar bilan** to'g'ri ishlaydi:

```bat
waitress-serve --listen=127.0.0.1:8000 --trusted-proxy=127.0.0.1 --trusted-proxy-headers="x-forwarded-for x-forwarded-proto x-forwarded-host" --clear-untrusted-proxy-headers config.wsgi:application
```

`--trusted-proxy` bo'lmasa waitress 3.x barcha `X-Forwarded-*` sarlavhalarini tashlab yuboradi. Oqibati:
Django so'rovni HTTP deb o'ylab `SECURE_SSL_REDIRECT` bilan cheksiz yo'naltirishga tushadi, hamma foydalanuvchi
IP'si `127.0.0.1` bo'lib qoladi (so'rovlar cheklovi va login bloklash hammaga birdek ta'sir qiladi, loglarda
haqiqiy IP yo'q).

- `--trusted-proxy` — proksi waitress'ga qaysi manzildan ulanishi (bir mashinada bo'lsa `127.0.0.1`).
  `*` **qo'ymang**: aks holda har kim soxta sarlavha yuboradi.
- `--clear-untrusted-proxy-headers` — ishonchsiz manbadan kelgan sarlavhalarni o'chiradi (3.x da standart, aniqlik uchun yozilgan).
- `.env` da `BEHIND_PROXY=True` (`NUM_PROXIES` avtomatik 1). Bu waitress'ning `--trusted-proxy-count` (standart 1) bilan mos:
  ikki proksi ketma-ket tursa ikkalasida ham `2` qo'ying (`--trusted-proxy-count=2`, `NUM_PROXIES=2`).
- Proksi `X-Forwarded-For` va `X-Forwarded-Proto` ni **o'zi** yuborishi shart (7-bo'limdagi nginx qatorlari).
- Tekshirish: noto'g'ri parol bilan kirib ko'ring va `grep security` qatorida `ip='...'` sizning haqiqiy IP'ngiz
  ekanini, sayt HTTPS'da yo'naltirishsiz ochilishini ko'ring.
