# Generated by Django 5.1.2 on 2024-11-12 09:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agent', '0007_phonecall_agent_owner_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='phonecall',
            name='agent_id',
            field=models.CharField(max_length=255, null=True),
        ),
    ]