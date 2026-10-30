"""Ovozli yordamchi uchun nutqni server tomonda matnga aylantirish.
Brauzerning o'z tanish xizmati o'zbekchani yaxshi tanimasa yoki umuman bo'lmasa (Firefox) ishlatiladi — static/js/voice.js.
Provayderlar shu tartibda sinab ko'riladi (sozlanganlari; biri xato bersa — keyingisi):
1) OpenAI (gpt-4o-transcribe / whisper-1, pullik) — .env: OPENAI_API_KEY.
2) VoiceLab (voicelab.uz) — o'zbek nutqiga ixtisoslashgan. .env: VOICELAB_API_KEY, kalitda «Nutqdan matnga» ruxsati
   to'liq («Ruxsat»: yuborish + natijani o'qish). Bepul tarifda kreditlar TTS bilan umumiy; tugasa (402) bir soat
   chetlab o'tiladi.
3) Google Gemini (ovozni o'zi tinglaydi, tekin rejasi bor) — .env: GEMINI_API_KEY.
Ovoz yozuvi diskka yozilmaydi — xotiradan to'g'ridan-to'g'ri provayderga yuboriladi. Qo'shimcha kutubxona kerak
emas (urllib)"""
import base64
import json
import time
import uuid
import logging
import secrets
import urllib.error
import urllib.request

from django.conf import settings
from django.core.cache import cache

from . import assistant

logger = logging.getLogger(__name__)

API_URL = "https://api.openai.com/v1/audio/transcriptions"
TIMEOUT_SECONDS = 30
# ~1 daqiqalik opus/webm yozuv 0.5 MB atrofida; brauzer 15 soniyadan uzun yozmaydi
MAX_AUDIO_BYTES = 5 * 1024 * 1024
ALLOWED_TYPES = ("audio/webm", "audio/ogg", "audio/mp4", "audio/mpeg", "audio/wav", "audio/x-wav", "audio/aac",
                 "audio/m4a", "audio/x-m4a", "video/webm", "video/mp4")
EXTENSIONS = {"webm": "webm", "ogg": "ogg", "mp4": "mp4", "mpeg": "mp3", "wav": "wav", "x-wav": "wav", "aac": "aac",
              "m4a": "m4a", "x-m4a": "m4a"}
# Tanish modeliga ilova so'zlari va o'zbek lotin yozuvi namunasi: "so'm", "hamyon", "Moliya" to'g'ri yozilishi uchun
PROMPT = ("Salom Moliya. Tushlikka 45 ming so'm sarfladim. Oylik tushdi 5 million kartaga. Kartadan naqdga 200 ming "
          "o'tkaz. Akmalga 1 million qarz berdim. Qoldig'im qancha? Hamyon, kirim, chiqim, qarz, dollar, kurs.")

FAILED_MESSAGE = "Ovozni tanib bo'lmadi. Qaytadan ayting yoki buyruqni yozing."
# Gemini'ga: faqat eshitilganini yoz, javob berma/tarjima qilma. Jim yoki shovqin bo'lsa — bo'sh satr
GEMINI_PROMPT = ("Bu — moliya ilovasining ovozli yordamchisiga aytilgan qisqa o'zbekcha buyruq. Uni so'zma-so'z, "
                 "o'zbek lotin yozuvida (o', g', sh, ch, ' belgilari bilan) yoz. Sonlarni raqam bilan yoz (45 ming, "
                 "1,5 million). Tarjima qilma, javob berma, izoh qo'shma — faqat aytilgan gapning o'zi. Nutq "
                 "eshitilmasa yoki faqat shovqin bo'lsa — hech narsa yozma. Ilova so'zlari namunasi: " + PROMPT)
GEMINI_TIMEOUT_SECONDS = 5
GEMINI_BUDGET_SECONDS = 8

VOICELAB_API = "https://api.voicelab.uz/v1"
# VoiceLab yozuvni navbatga qo'yadi (202), natija so'rab olinadi. Qisqa buyruq odatda 1–3 soniyada tayyor; shundan
# uzoq kutilmaydi — keyingi provayder (Gemini) taniydi
VOICELAB_WAIT_SECONDS = 6
VOICELAB_POLL_SECONDS = 0.5
VOICELAB_OFF_SECONDS = {402: 60 * 60, 401: 10 * 60, 403: 10 * 60}


class SttError(Exception):
    pass


def providers():
    names = []
    if settings.OPENAI_API_KEY:
        names.append("openai")
    if settings.VOICELAB_API_KEY:
        names.append("voicelab")
    if settings.GEMINI_API_KEY:
        names.append("gemini")
    return names


def provider():
    names = providers()
    return names[0] if names else None


def is_enabled():
    return provider() is not None


def check_upload(upload):
    """Yuklangan fayl tekshiruvi. Muammo bo'lsa — foydalanuvchiga ko'rsatiladigan matn, aks holda None"""
    if upload is None:
        return "Ovoz yozuvi yuborilmadi"
    if upload.size == 0:
        return "Ovoz yozuvi bo'sh"
    if upload.size > MAX_AUDIO_BYTES:
        return "Ovoz yozuvi juda uzun. Qisqaroq ayting"
    content_type = (upload.content_type or "").split(";")[0].strip().lower()
    if content_type not in ALLOWED_TYPES:
        return "Ovoz yozuvi formati qo'llanmaydi"
    return None


def _multipart(fields, file_field, filename, content_type, data):
    boundary = f"----moliya{secrets.token_hex(12)}"
    parts = []
    for name, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n".encode() + data + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def transcribe(upload):
    """Yuklangan ovoz fayli -> matn. Provayderlar navbat bilan; hammasi xato bersa SttError(FAILED_MESSAGE)"""
    content_type = (upload.content_type or "audio/webm").split(";")[0].strip().lower()
    data = upload.read()
    for name in providers():
        if cache.get(f"stt:off:{name}"):
            continue
        try:
            return PROVIDERS[name](data, content_type)
        except SttError:
            continue
    raise SttError(FAILED_MESSAGE)


def _gemini(data, content_type):
    body = {
        "contents": [{"role": "user", "parts": [
            {"text": GEMINI_PROMPT},
            {"inlineData": {"mimeType": content_type, "data": base64.b64encode(data).decode("ascii")}},
        ]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 512, "thinkingConfig": {"thinkingLevel": "low"}},
    }
    relaxed = {"contents": body["contents"], "generationConfig": {"temperature": 0, "maxOutputTokens": 512}}
    try:
        payload = assistant.gemini_generate(body, relaxed, timeout=GEMINI_TIMEOUT_SECONDS, label="Ovozni tanish",
                                            first_model=settings.GEMINI_VOICE_MODEL, budget=GEMINI_BUDGET_SECONDS)
    except RuntimeError:
        raise SttError(FAILED_MESSAGE)
    text, blocked = assistant.gemini_text(payload)
    if blocked:
        raise SttError(FAILED_MESSAGE)
    return text.strip().strip('"«»').strip()


def _openai(data, content_type):
    ext = EXTENSIONS.get(content_type.split("/")[-1], "webm")
    body, header = _multipart(
        {"model": settings.OPENAI_TRANSCRIBE_MODEL, "language": "uz", "prompt": PROMPT, "response_format": "json"},
        "file", f"voice.{ext}", content_type, data,
    )
    request = urllib.request.Request(API_URL, data=body, method="POST", headers={
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": header,
    })
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # Kalit yoki limit muammosi — sababi logga, foydalanuvchiga umumiy xabar
        logger.error("Ovozni tanish: OpenAI xatosi %s", e.code)
        raise SttError(FAILED_MESSAGE)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        logger.warning("Ovozni tanish: OpenAI ga ulanib bo'lmadi")
        raise SttError(FAILED_MESSAGE)
    return str(payload.get("text") or "").strip()


def _voicelab_get(path, data=None, headers=None):
    request = urllib.request.Request(f"{VOICELAB_API}{path}", data=data, method="POST" if data else "GET", headers={
        "Authorization": f"Bearer {settings.VOICELAB_API_KEY}", "User-Agent": "moliya", **(headers or {}),
    })
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def _voicelab(data, content_type):
    """VoiceLab STT: yozuv yuboriladi (202 + id), natija VOICELAB_WAIT_SECONDS gacha so'rab turiladi"""
    ext = EXTENSIONS.get(content_type.split("/")[-1], "webm")
    body, header = _multipart({"language": "uz", "include_speakers": "false"}, "audio", f"voice.{ext}", content_type, data)
    try:
        job = _voicelab_get("/stt", body, {"Content-Type": header, "Idempotency-Key": str(uuid.uuid4())})
        deadline = time.monotonic() + VOICELAB_WAIT_SECONDS
        while True:
            result = _voicelab_get(f"/stt/transcriptions/{job['id']}")
            if result.get("status") == "completed":
                return str(result.get("transcript") or "").strip()
            if result.get("status") == "failed":
                logger.warning("Ovozni tanish (VoiceLab): tanib bo'lmadi (%s)", (result.get("error") or {}).get("code"))
                raise SttError(FAILED_MESSAGE)
            if time.monotonic() >= deadline:
                logger.warning("Ovozni tanish (VoiceLab): natija %s soniyada tayyor bo'lmadi", VOICELAB_WAIT_SECONDS)
                raise SttError(FAILED_MESSAGE)
            time.sleep(VOICELAB_POLL_SECONDS)
    except urllib.error.HTTPError as e:
        if e.code in VOICELAB_OFF_SECONDS:
            cache.set("stt:off:voicelab", True, VOICELAB_OFF_SECONDS[e.code])
        if e.code == 402:
            logger.warning("Ovozni tanish (VoiceLab): kreditlar tugadi — bir soat keyingi provayder ishlatiladi")
        else:
            # 403 — kalitda «Nutqdan matnga» ruxsati yo'q yoki faqat «Yozish» (natijani o'qib bo'lmaydi)
            logger.error("Ovozni tanish (VoiceLab): xato %s", e.code)
        raise SttError(FAILED_MESSAGE)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError, TypeError):
        logger.warning("Ovozni tanish (VoiceLab): ulanib bo'lmadi yoki javob buzilgan")
        raise SttError(FAILED_MESSAGE)


PROVIDERS = {"openai": _openai, "voicelab": _voicelab, "gemini": _gemini}
