# Generated by Django 5.1.2 on 2024-10-31 17:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agent', '0004_rename_auth_token_servicedetail_twilio_phone_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='phonecall',
            name='twilio_call_id',
            field=models.CharField(max_length=100, null=True),
        ),
    ]
