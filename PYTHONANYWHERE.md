# Bepul joylash — PythonAnywhere (qadamma-qadam)

Havola: `https://USERNAME.pythonanywhere.com`. Domen va VPS kerak emas. USERNAME — ro'yxatdan o'tganda tanlagan nomingiz.

**Cheklov:** bepul tarifda server faqat PythonAnywhere ruxsat ro'yxatidagi saytlarga ulana oladi. Ro'yxatda
bo'lmasa, Gemini/VoiceLab (ovozli yordamchi) va Gmail (parol tiklash xati) ishlamaydi; asosiy kirim-chiqim ishlaydi.
Ruxsat ro'yxati: help.pythonanywhere.com → "free accounts whitelist".

## 1. Hisob
pythonanywhere.com → Pricing → **Create a Beginner account** (bepul). Nomni o'ylab tanlang: u havolaga tushadi.

## 2. Kod
Kod GitHub'da (private) bo'lsa — token bilan, bo'lmasa Files bo'limidan zip yuklab oching. **Bash console**:

```bash
git clone https://github.com/<login>/moliya.git ~/app
cd ~/app
python3.12 -m venv venv        # Django 6.1 uchun Python 3.12+ shart; 3.13 bo'lsa shuni yozing
source venv/bin/activate
pip install -r requirements.txt
```

## 3. `.env`
`.env.server` faylining mazmunini `~/app/.env` ga ko'chiring (Files bo'limi yoki `nano ~/app/.env`).
`USERNAME` ni haqiqiy nomga almashtiring, kalitlarni to'ldiring.

## 4. Baza va statik fayllar
```bash
cd ~/app && source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py seed_data
python manage.py createsuperuser
python manage.py check --deploy
```
Kompyuterdagi `db.sqlite3` ni ko'chirmang (unda test akkauntlar bor).

## 5. Web ilova
**Web** → **Add a new web app** → **Manual configuration** → Python 3.12 (yoki yuqori). So'ng:

- **Virtualenv:** `/home/USERNAME/app/venv`
- **Source / Working directory:** `/home/USERNAME/app`
- **WSGI configuration file** havolasini oching, ichidagi hamma narsani o'chirib, shuni qo'ying:

```python
import os, sys
path = '/home/USERNAME/app'
if path not in sys.path:
    sys.path.insert(0, path)
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```
- **Force HTTPS:** yoqing.
- **Reload** tugmasini bosing, so'ng `https://USERNAME.pythonanywhere.com` ni oching.

CSS/JS ni WhiteNoise beradi, Static files bo'limiga qator qo'shish shart emas.

## 6. Tekshiruv
Ro'yxatdan o'tish, kirish, daromad/harajat qo'shish. Xato bo'lsa: Web → **Error log**.
Agar sahifa cheksiz yo'naltirilsa, `.env` ga `SECURE_SSL_REDIRECT=False` qo'shing va Reload qiling.

## Bepul tarifda bilish kerak
- Har 3 oyda Web sahifasida **"Run until 3 months from today"** tugmasini bosing, aks holda ilova o'chadi.
- Faqat bitta ilova va bitta worker. Bazani Files bo'limidan vaqti-vaqti bilan yuklab oling (zaxira).

## Uzoq kirilmagan akkauntlarni o'chirish (Scheduled tasks)
30 kun kirmagan oddiy akkaunt va uning barcha ma'lumotlari (email, login nomi ham) butunlay o'chadi — **qaytarib bo'lmaydi**.
Superuser, admin (`is_staff`) va bloklangan akkauntlar o'chmaydi. Batafsil: `DEPLOY.md` ("Uzoq kirilmagan akkauntlarni o'chirish").

1. Avval qo'lda tekshiring (Bash konsol):
   ```bash
   cd ~/app && source venv/bin/activate && python manage.py delete_inactive_accounts --dry-run
   ```
2. **Tasks** sahifasi → **Scheduled tasks** → vaqtni tanlang (masalan 03:40, kuniga bir marta) va buyruqni yozing:
   ```bash
   cd ~/app && venv/bin/python manage.py delete_inactive_accounts >> ~/inactive.log 2>&1
   ```
   (bepul tarifda faqat bitta kunlik/soatlik vazifa ruxsat etiladi; `clearsessions` ni ham shu buyruq bilan birga yozish mumkin:
   `... clearsessions && ... delete_inactive_accounts`.)
3. Natija `~/inactive.log` da: nechta akkaunt o'chgani va ularning `id`/login nomi.
4. Bir martada 100 tadan ko'p akkaunt o'chmaydi (himoya). Ko'p bo'lsa, ro'yxatni `--dry-run` bilan ko'rib, `--max-delete 500` bilan qo'lda ishga tushiring.

## Yangilash
```bash
cd ~/app && git pull && source venv/bin/activate && pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput
```
So'ng Web → Reload.
