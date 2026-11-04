from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shareshelf_app', '0003_userprofile_avatar_userprofile_bio_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='avatar',
        ),
    ]
