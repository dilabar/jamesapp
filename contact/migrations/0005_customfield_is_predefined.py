# Generated by Django 5.1.2 on 2025-01-19 07:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contact', '0004_customfield'),
    ]

    operations = [
        migrations.AddField(
            model_name='customfield',
            name='is_predefined',
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
    ]
