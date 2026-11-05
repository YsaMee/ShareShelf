from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shareshelf_app', '0003_userprofile_avatar_userprofile_bio_and_more'),
    ]

    # Kept as an empty migration so databases that already recorded 0004
    # retain a consistent migration history. The avatar field is no longer
    # created by 0003, so there is nothing to remove here.
    operations = []
