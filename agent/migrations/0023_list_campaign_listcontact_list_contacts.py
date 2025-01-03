# Generated by Django 5.1.3 on 2024-12-24 19:25

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agent', '0022_email_phonenumber'),
    ]

    operations = [
        migrations.CreateModel(
            name='List',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Campaign',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('subject', models.CharField(blank=True, max_length=255, null=True)),
                ('content', models.TextField(blank=True, null=True)),
                ('scheduled_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('scheduled', 'Scheduled'), ('sent', 'Sent'), ('cancelled', 'Cancelled')], default='draft', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('individual_contacts', models.ManyToManyField(blank=True, related_name='campaigns', to='agent.contact')),
                ('lists', models.ManyToManyField(blank=True, related_name='campaigns', to='agent.list')),
            ],
        ),
        migrations.CreateModel(
            name='ListContact',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subscribed_at', models.DateTimeField(auto_now_add=True)),
                ('contact', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='agent.contact')),
                ('list', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='agent.list')),
            ],
            options={
                'unique_together': {('contact', 'list')},
            },
        ),
        migrations.AddField(
            model_name='list',
            name='contacts',
            field=models.ManyToManyField(related_name='lists', through='agent.ListContact', to='agent.contact'),
        ),
    ]
