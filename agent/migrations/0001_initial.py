# Generated by Django 5.1.3 on 2025-01-14 18:50

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contact', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='GoogleCalendarEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('summary', models.CharField(max_length=255)),
                ('start_time', models.DateTimeField()),
                ('end_time', models.DateTimeField()),
                ('description', models.TextField()),
                ('attendees', models.JSONField()),
                ('calendar_event_id', models.CharField(max_length=255, unique=True)),
                ('calendar_link', models.URLField()),
                ('status', models.CharField(choices=[('booked', 'Booked'), ('cancelled', 'Cancelled'), ('completed', 'Completed')], default='booked', max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Agent',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('agent_id', models.CharField(max_length=255, unique=True)),
                ('agent_id_hash', models.CharField(blank=True, max_length=64, null=True, unique=True)),
                ('voice', models.URLField(blank=True, null=True)),
                ('voice_speed', models.FloatField(blank=True, null=True)),
                ('display_name', models.CharField(blank=True, max_length=255, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('greeting', models.TextField(blank=True, null=True)),
                ('prompt', models.TextField(blank=True, null=True)),
                ('critical_knowledge', models.TextField(blank=True, null=True)),
                ('visibility', models.CharField(blank=True, max_length=50, null=True)),
                ('answer_only_from_critical_knowledge', models.BooleanField(blank=True, null=True)),
                ('avatar_photo_url', models.URLField(blank=True, null=True)),
                ('critical_knowledge_files', models.JSONField(blank=True, null=True)),
                ('phone_numbers', models.JSONField(blank=True, null=True)),
                ('real_agent_no', models.CharField(blank=True, max_length=20, null=True)),
                ('llm_base_url', models.URLField(blank=True, null=True)),
                ('llm_api_key', models.CharField(blank=True, max_length=255, null=True)),
                ('llm_model', models.CharField(blank=True, max_length=255, null=True)),
                ('llm_temperature', models.FloatField(blank=True, null=True)),
                ('llm_max_tokens', models.IntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='agents', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='PhoneCall',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone_number', models.CharField(max_length=20)),
                ('call_status', models.CharField(max_length=20)),
                ('twilio_call_id', models.CharField(max_length=100, null=True)),
                ('play_ai_conv_id', models.CharField(max_length=100, null=True)),
                ('feedback', models.TextField(blank=True, null=True)),
                ('is_call_forwarded', models.BooleanField(blank=True, default=False, null=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('agent_owner_id', models.CharField(max_length=100, null=True)),
                ('agent_id', models.CharField(max_length=255, null=True)),
                ('recording_presigned_url', models.URLField(max_length=500, null=True)),
                ('hand_off_summary', models.TextField(blank=True, null=True)),
                ('transcription_text', models.TextField(blank=True, null=True)),
                ('recording_url', models.URLField(max_length=500, null=True)),
                ('recording_sid', models.CharField(max_length=100, null=True)),
                ('call_duration', models.IntegerField(blank=True, null=True)),
                ('recording_duration', models.IntegerField(blank=True, null=True)),
                ('caller', models.CharField(max_length=20, null=True)),
                ('called', models.CharField(max_length=20, null=True)),
                ('direction', models.CharField(max_length=50, null=True)),
                ('from_country', models.CharField(max_length=50, null=True)),
                ('to_country', models.CharField(max_length=50, null=True)),
                ('from_city', models.CharField(max_length=100, null=True)),
                ('to_city', models.CharField(max_length=100, null=True)),
                ('agnt', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='phone_calls', to='agent.agent')),
                ('campaign', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='phone_calls', to='contact.campaign')),
                ('from_call_id', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='related_calls', to='agent.phonecall')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='phonecall', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ServiceDetail',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('service_name', models.CharField(choices=[('play_ai', 'Play.ai'), ('twilio', 'Twilio')], max_length=50)),
                ('api_key', models.CharField(blank=True, max_length=255, null=True)),
                ('account_sid', models.CharField(blank=True, max_length=255, null=True)),
                ('twilio_phone', models.CharField(blank=True, max_length=255, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='services', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'service_name')},
            },
        ),
    ]
