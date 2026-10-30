from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from mainapp import tts, voice


class Command(BaseCommand):
    help = ("Ovozli yordamchining doimiy gaplarini oldindan ovozga aylantirib keshga yozadi — birinchi marta ham darhol "
            "yangraydi. Keshdagilari qayta sarflanmaydi; yangilari VoiceLab kreditidan (1 belgi = 1 kredit) olinadi")

    def add_arguments(self, parser):
        parser.add_argument("--gender", choices=["female", "male", "both"], default="both")
        parser.add_argument("--with-names", action="store_true",
                            help="Har foydalanuvchi uchun ism bilan salomlashish («Ha, Abdurahmon?») ham")
        parser.add_argument("--dry-run", action="store_true", help="Faqat ro'yxat va belgilar soni, ovoz yaratilmaydi")

    def handle(self, *args, **options):
        if not tts.is_enabled():
            raise CommandError("Server ovozi sozlanmagan (.env: VOICELAB_API_KEY yoki AZURE_SPEECH_KEY)")
        phrases = voice.warmup_phrases()
        if options["with_names"]:
            names = get_user_model().objects.filter(is_active=True).exclude(first_name="").values_list("first_name", flat=True)
            for name in sorted(set(names)):
                phrases += [p for p in voice.warmup_phrases(name) if p not in phrases]
        genders = ["female", "male"] if options["gender"] == "both" else [options["gender"]]
        chars = sum(len(tts.clean_text(p)) for p in phrases) * len(genders)
        self.stdout.write(f"{len(phrases)} ta gap x {len(genders)} ovoz, ko'pi bilan {chars} belgi (keshdagilari tekin)")
        if options["dry_run"]:
            for phrase in phrases:
                self.stdout.write(f"  {phrase}")
            return
        done = failed = 0
        for gender in genders:
            for phrase in phrases:
                try:
                    tts.synthesize(phrase, gender)
                    done += 1
                except tts.TtsError as e:
                    failed += 1
                    self.stderr.write(f"  xato ({gender}): {phrase} — {e}")
        self.stdout.write(self.style.SUCCESS(f"Tayyor: {done}") + (f", xato: {failed}" if failed else ""))
