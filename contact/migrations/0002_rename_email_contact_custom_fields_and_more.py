# Generated by Django 5.1.4 on 2025-01-14 18:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contact', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='contact',
            old_name='email',
            new_name='custom_fields',
        ),
        migrations.RemoveField(
            model_name='contact',
            name='phone',
        ),
        migrations.AddField(
            model_name='phonenumber',
            name='country_code',
            field=models.CharField(blank=True, max_length=15, null=True),
        ),
    ]
