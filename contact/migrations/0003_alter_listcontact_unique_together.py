# Generated by Django 5.1.3 on 2025-01-15 19:20

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contact', '0002_rename_email_contact_custom_fields_and_more'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='listcontact',
            unique_together=set(),
        ),
    ]
