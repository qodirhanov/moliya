from django.db import migrations, models


class Migration(migrations.Migration):
    """3/3: kalit noyob va majburiy bo'ladi. Eski Lower("username") cheklovi ortiqcha: username_key (casefold) uni
    to'liq qoplaydi va kirill harflarini ham tushiradi, eskisi esa SQLite'da faqat ASCII'ni — ikkinchi indeks keraksiz"""

    dependencies = [
        ('mainapp', '0018_fill_username_key'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='user',
            name='mainapp_user_username_lower_uniq',
        ),
        migrations.AlterField(
            model_name='user',
            name='username_key',
            field=models.CharField(blank=True, editable=False, max_length=450, unique=True),
        ),
    ]
