# Generated by Django 5.1.3 on 2024-12-23 17:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agent', '0020_remove_contact_dnd_all_channels_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='contact',
            name='photo',
            field=models.ImageField(blank=True, null=True, upload_to='photos/'),
        ),
    ]
