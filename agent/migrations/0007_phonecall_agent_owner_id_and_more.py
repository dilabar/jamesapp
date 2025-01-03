# Generated by Django 5.1.2 on 2024-11-11 21:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agent', '0006_phonecall_is_call_forwarded_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='phonecall',
            name='agent_owner_id',
            field=models.CharField(max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='phonecall',
            name='recording_presigned_url',
            field=models.URLField(max_length=500, null=True),
        ),
    ]
