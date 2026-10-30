"""Ovozli yordamchi javoblarini ravon o'zbekcha ovozda o'qish (matn -> nutq, server tomonda).
Brauzerlarning o'zida o'zbekcha ovoz deyarli yo'q (faqat Edge'da), shuning uchun boshqa brauzerlarda turkcha ovoz
o'zbekcha matnni g'alati o'qirdi. Provayderlar shu tartibda sinab ko'riladi (sozlanganlari):
1) VoiceLab (voicelab.uz) — o'zbek tiliga ixtisoslashgan ovozlar, WAV 24 kHz. .env: VOICELAB_API_KEY (tts:write),
   ixtiyoriy VOICELAB_VOICE_FEMALE / VOICELAB_VOICE_MALE (ro'yxat: manage.py voicelab_voices). Bepul tarif oyiga
   2 000 belgi: kredit tugasa (402) bir soatga chetlab o'tiladi va keyingi provayder ishlaydi.
2) Microsoft Azure Speech — haqiqiy o'zbek neyron ovozlari: uz-UZ-MadinaNeural (ayol), uz-UZ-SardorNeural (erkak).
   .env: AZURE_SPEECH_KEY, AZURE_SPEECH_REGION. Oyiga 500 000 belgigacha bepul.
3) OpenAI (gpt-4o-mini-tts) — .env: OPENAI_API_KEY (nutqni tanish bilan bir xil kalit). Ko'p tilli ovoz, o'zbekchani
   biroz urg'u bilan o'qiydi.
Hech biri bo'lmasa — brauzer o'z ovozida o'qiydi (static/js/voice.js). Bir xil gaplar ("Qancha sarfladingiz?")
keshlanadi: qayta pul to'lanmaydi va javob darhol chiqadi. Qo'shimcha kutubxona kerak emas (urllib)"""
import hashlib
import http.client
import json
import logging
import re
import urllib.error
import urllib.request
from xml.sax.saxutils import escape

from django.conf import settings
from django.core.cache import cache

from .voice_parse import spell_numbers

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 15
MAX_TEXT_LENGTH = 600
CACHE_SECONDS = 60 * 60 * 24 * 30
# Juda katta javoblar keshlanmaydi (kesh jadvalini to'ldirmasin). VoiceLab WAV ~48 KB/soniya — ~20 soniyagacha
MAX_CACHED_BYTES = 1024 * 1024

VOICELAB_API = "https://api.voicelab.uz/v1"
# Kredit tugasa yoki kalit noto'g'ri bo'lsa provayder shuncha vaqt chetlab o'tiladi (har javobda behuda so'rov ketmasin)
VOICELAB_OFF_SECONDS = {402: 60 * 60, 401: 10 * 60, 403: 10 * 60}
VOICELAB_VOICES_CACHE_SECONDS = 60 * 60 * 24
# Ovoz ID berilmasa ro'yxatdan tanlanadi: jinsi — "gender" maydoni, bo'sh bo'lsa tavsifdagi alohida so'z
# ("female" ichidagi "male" hisoblanmaydi). Moliya yordamchisiga xotirjam, aniq ovozlar mos — uslub (orb_palette)
# shu tartibda afzal; streamer, anime qahramoni kabi ovozlar tanlanmaydi
VOICELAB_GENDER_WORDS = {"female": ("ayol", "female", "woman", "qiz"), "male": ("erkak", "male", "man", "yigit")}
VOICELAB_PALETTES = ("support", "steady", "calm", "narrator")

AZURE_VOICES = {"female": "uz-UZ-MadinaNeural", "male": "uz-UZ-SardorNeural"}
OPENAI_VOICES = {"female": "coral", "male": "ash"}
OPENAI_INSTRUCTIONS = ("Matn o'zbek tilida (lotin yozuvi). Uni ona tili o'zbek bo'lgan odamdek tabiiy, ravon va iliq "
                       "ohangda o'qi: o', g', sh, ch, ng tovushlarini to'g'ri talaffuz qil, so'zlarni rus yoki turk "
                       "talaffuzida o'qima. Tez emas, xotirjam gapir.")


class TtsError(Exception):
    pass


class _Skip(Exception):
    """Shu provayder hozir javob bera olmadi — keyingisi sinab ko'riladi"""


def providers():
    """Sozlangan provayderlar ustuvorlik tartibida"""
    names = []
    if settings.VOICELAB_API_KEY:
        names.append("voicelab")
    if settings.AZURE_SPEECH_KEY and settings.AZURE_SPEECH_REGION:
        names.append("azure")
    if settings.OPENAI_API_KEY:
        names.append("openai")
    return names


def provider():
    """Asosiy provayder nomi (brauzerga: server ovozi bormi) yoki None"""
    names = providers()
    return names[0] if names else None


def is_enabled():
    return provider() is not None


def clean_text(text):
    """Ekrandagi belgilar ovozda o'qilmasin: «», ·, → kabi"""
    text = str(text or "")
    for old, new in (("«", ""), ("»", ""), ("·", ","), ("→", "dan"), ("—", ","), ("…", "."), ("`", "'"),
                     ("‘", "'"), ("’", "'"), ("ʻ", "'"), ("ʼ", "'")):
        text = text.replace(old, new)
    # Raqamlar so'z bilan: sintezator ularni o'zicha o'qib, xato qilardi ("bir yuzi yigirma ikki")
    return spell_numbers(text)[:MAX_TEXT_LENGTH]


def _azure(text, gender):
    voice = AZURE_VOICES.get(gender, AZURE_VOICES["female"])
    ssml = (f"<speak version='1.0' xml:lang='uz-UZ'><voice name='{voice}'>"
            f"<prosody rate='-4%'>{escape(text)}</prosody></voice></speak>")
    request = urllib.request.Request(
        f"https://{settings.AZURE_SPEECH_REGION}.tts.speech.microsoft.com/cognitiveservices/v1",
        data=ssml.encode("utf-8"), method="POST", headers={
            "Ocp-Apim-Subscription-Key": settings.AZURE_SPEECH_KEY,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
            "User-Agent": "moliya",
        })
    return request


def _voicelab_headers():
    return {"Authorization": f"Bearer {settings.VOICELAB_API_KEY}", "User-Agent": "moliya"}


def voicelab_voices(language="uz"):
    """VoiceLab'dagi ovozlar ro'yxati ([{id, display_name, description, ...}]). Kalitga voices:read kerak.
    Xato bo'lsa TtsError"""
    request = urllib.request.Request(f"{VOICELAB_API}/voices?language={language}", headers=_voicelab_headers())
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        logger.error("VoiceLab: ovozlar ro'yxati olinmadi (HTTP %s)", e.code)
        raise TtsError("VoiceLab ovozlari olinmadi")
    except (urllib.error.URLError, http.client.HTTPException, TimeoutError, OSError, ValueError):
        raise TtsError("VoiceLab ga ulanib bo'lmadi")
    if not isinstance(payload, dict):
        raise TtsError("VoiceLab javobi buzilgan")
    return [v for v in (payload.get("data") or []) if isinstance(v, dict) and v.get("id")]


def _voicelab_voice(gender):
    """.env dagi ovoz ID, bo'lmasa o'zbekcha ovozlar ro'yxatidan jinsi bo'yicha (ro'yxat bir kun keshlanadi)"""
    configured = settings.VOICELAB_VOICE_MALE if gender == "male" else settings.VOICELAB_VOICE_FEMALE
    if configured:
        return configured
    voices = cache.get("tts:voicelab:voices")
    if voices is None:
        try:
            voices = voicelab_voices()
        except TtsError:
            voices = []
        cache.set("tts:voicelab:voices", voices, VOICELAB_VOICES_CACHE_SECONDS if voices else 10 * 60)
    same = [v for v in voices if _voice_gender(v) == gender]
    suitable = [v for v in voices if v.get("orb_palette") in VOICELAB_PALETTES]
    for pool in ([v for v in same if v in suitable], same, suitable, voices):
        if pool:
            return min(pool, key=lambda v: VOICELAB_PALETTES.index(v["orb_palette"])
                       if v.get("orb_palette") in VOICELAB_PALETTES else len(VOICELAB_PALETTES))["id"]
    # Ro'yxat yo'q (kalitda voices:read yo'q): ikkinchi jinsning ID si bo'lsa — o'sha
    return settings.VOICELAB_VOICE_FEMALE or settings.VOICELAB_VOICE_MALE or None


def _voice_gender(voice):
    gender = str(voice.get("gender") or "").lower()
    if gender in ("female", "male"):
        return gender
    about = " ".join(str(voice.get(k) or "") for k in ("display_name", "description", "short_description")).lower()
    words = set(re.findall(r"\w+", about))
    for name, hints in VOICELAB_GENDER_WORDS.items():
        if words & set(hints):
            return name
    return None


def _voicelab(text, gender):
    voice = _voicelab_voice(gender)
    if not voice:
        logger.error("VoiceLab: o'zbekcha ovoz topilmadi — .env ga VOICELAB_VOICE_FEMALE yozing (manage.py voicelab_voices)")
        raise _Skip()
    body = json.dumps({"text": text, "language": "uz", "voice_id": voice, "speed": 1}).encode("utf-8")
    # Bir xil matn va ovoz — bir xil kalit: qayta so'ralsa VoiceLab saqlangan audioni kredit olmasdan qaytaradi
    idempotency = "moliya-" + hashlib.sha256(f"{voice}|{text}".encode()).hexdigest()[:48]
    return urllib.request.Request(f"{VOICELAB_API}/tts", data=body, method="POST", headers={
        **_voicelab_headers(),
        "Content-Type": "application/json",
        "Accept": "audio/wav",
        "Idempotency-Key": idempotency,
    })


def _openai(text, gender):
    body = json.dumps({
        "model": settings.OPENAI_TTS_MODEL,
        "voice": OPENAI_VOICES.get(gender, OPENAI_VOICES["female"]),
        "input": text,
        "instructions": OPENAI_INSTRUCTIONS,
        "response_format": "mp3",
    }).encode("utf-8")
    return urllib.request.Request("https://api.openai.com/v1/audio/speech", data=body, method="POST", headers={
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    })


BUILDERS = {"voicelab": _voicelab, "azure": _azure, "openai": _openai}


def content_type(audio):
    """VoiceLab WAV, qolganlari MP3 qaytaradi"""
    return "audio/wav" if audio[:4] == b"RIFF" else "audio/mpeg"


def _fetch(name, text, gender):
    request = BUILDERS[name](text, gender)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            # VoiceLab: audio so'rov vaqtida tayyor bo'lmasa 202 (navbat) — ovozli javob kutib turolmaydi
            if getattr(response, "status", None) == 202:
                logger.warning("Ovozli javob (%s): audio o'z vaqtida tayyor bo'lmadi (HTTP %s)", name, response.status)
                raise _Skip()
            return response.read()
    except urllib.error.HTTPError as e:
        if name == "voicelab" and e.code in VOICELAB_OFF_SECONDS:
            cache.set("tts:off:voicelab", True, VOICELAB_OFF_SECONDS[e.code])
            if e.code == 402:
                logger.warning("Ovozli javob (VoiceLab): kreditlar tugadi — bir soat keyingi provayder ishlatiladi")
            else:
                logger.error("Ovozli javob (VoiceLab): kalit noto'g'ri yoki tts:write ruxsati yo'q (HTTP %s)", e.code)
        else:
            logger.error("Ovozli javob (%s): xato %s", name, e.code)
        raise _Skip()
    except (urllib.error.URLError, http.client.HTTPException, TimeoutError, OSError):
        logger.warning("Ovozli javob (%s): ulanib bo'lmadi", name)
        raise _Skip()


def synthesize(text, gender="female"):
    """Matn -> audio baytlar (WAV yoki MP3, content_type()). Provayderlar navbat bilan sinab ko'riladi; hech biri
    sozlanmagan yoki hammasi xato bersa TtsError (brauzer o'z ovozida o'qiydi)"""
    names = providers()
    if not names:
        raise TtsError("Server ovozi sozlanmagan")
    text = clean_text(text)
    if not text:
        raise TtsError("Matn bo'sh")
    gender = gender if gender in ("female", "male") else "female"
    for name in names:
        if cache.get(f"tts:off:{name}"):
            continue
        key = "tts:" + hashlib.sha256(f"{name}|{gender}|{settings.OPENAI_TTS_MODEL}|{text}".encode()).hexdigest()
        audio = cache.get(key)
        if audio:
            return audio
        try:
            audio = _fetch(name, text, gender)
        except _Skip:
            continue
        if not audio:
            continue
        if len(audio) <= MAX_CACHED_BYTES:
            cache.set(key, audio, CACHE_SECONDS)
        return audio
    raise TtsError("Ovozli javob tayyorlanmadi")
