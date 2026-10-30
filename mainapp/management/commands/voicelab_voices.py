from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from mainapp import tts


class Command(BaseCommand):
    help = "VoiceLab'dagi o'zbekcha ovozlar ro'yxati — .env dagi VOICELAB_VOICE_FEMALE / VOICELAB_VOICE_MALE uchun ID"

    def add_arguments(self, parser):
        parser.add_argument("--language", default="uz", help="Til kodi (standart: uz)")

    def handle(self, *args, **options):
        if not settings.VOICELAB_API_KEY:
            raise CommandError(".env da VOICELAB_API_KEY yo'q")
        try:
            voices = tts.voicelab_voices(options["language"])
        except tts.TtsError as e:
            raise CommandError(f"{e}. Kalitda voices:read ruxsati borligini tekshiring")
        if not voices:
            self.stdout.write("Bu tilda ovoz topilmadi")
            return
        for voice in voices:
            about = voice.get("short_description") or voice.get("description") or ""
            self.stdout.write(f"{voice['id']}  {voice.get('display_name', '')}  — {about}")
        self.stdout.write("\n.env ga yozing: VOICELAB_VOICE_FEMALE=voice_...  VOICELAB_VOICE_MALE=voice_...")
