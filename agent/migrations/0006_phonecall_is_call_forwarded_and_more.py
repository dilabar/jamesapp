# Generated by Django 5.1.2 on 2024-11-11 19:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agent', '0005_phonecall_twilio_call_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='phonecall',
            name='is_call_forwarded',
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
        migrations.AddField(
            model_name='phonecall',
            name='play_ai_conv_id',
            field=models.CharField(max_length=100, null=True),
        ),
    ]
