# Generated by Django 5.1.2 on 2025-01-15 17:50

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agent', '0001_initial'),
        ('contact', '0002_rename_email_contact_custom_fields_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='phonecall',
            name='contact',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='phone_calls_for_contact', to='contact.contact'),
        ),
        migrations.AlterField(
            model_name='phonecall',
            name='campaign',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='phone_calls_for_campaign', to='contact.campaign'),
        ),
    ]
