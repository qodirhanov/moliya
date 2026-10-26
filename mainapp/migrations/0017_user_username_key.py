from django.db import migrations, models


class Migration(migrations.Migration):
    """1/3: katta-kichik harfga qaramaydigan nom kaliti avval bo'sh (NULL) maydon sifatida qo'shiladi — mavjud
    foydalanuvchilar to'ldirilgach (0018) maydon noyob va majburiy qilinadi (0019)"""

    dependencies = [
        ('mainapp', '0016_fill_uzs_rate'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='username_key',
            field=models.CharField(blank=True, editable=False, max_length=450, null=True),
        ),
    ]
