# Generated by Django 5.1.2 on 2024-12-02 17:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agent', '0013_phonecall_transcription_text'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='agent',
            name='name',
        ),
        migrations.AddField(
            model_name='agent',
            name='answer_only_from_critical_knowledge',
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='agent',
            name='avatar_photo_url',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='agent',
            name='critical_knowledge',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='agent',
            name='critical_knowledge_files',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='agent',
            name='display_name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='agent',
            name='greeting',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='agent',
            name='llm_api_key',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='agent',
            name='llm_base_url',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='agent',
            name='llm_max_tokens',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='agent',
            name='llm_model',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='agent',
            name='llm_temperature',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='agent',
            name='phone_numbers',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='agent',
            name='prompt',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='agent',
            name='visibility',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='agent',
            name='voice',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='agent',
            name='voice_speed',
            field=models.FloatField(blank=True, null=True),
        ),
    ]