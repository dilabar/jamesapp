# Generated by Django 5.1.2 on 2025-04-23 15:22

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agent', '0009_twiliophonenumber'),
        ('contact', '0013_revokedtask'),
    ]

    operations = [
        migrations.AddField(
            model_name='campaign',
            name='twilio_phone',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='agent.twiliophonenumber'),
        ),
    ]
