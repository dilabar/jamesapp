# Generated by Django 5.1.3 on 2024-12-23 17:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agent', '0019_remove_contactphone_contact_alter_contact_options_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='contact',
            name='dnd_all_channels',
        ),
        migrations.RemoveField(
            model_name='contact',
            name='dnd_preferences',
        ),
        migrations.RemoveField(
            model_name='contact',
            name='image',
        ),
        migrations.AlterField(
            model_name='contact',
            name='contact_type',
            field=models.CharField(choices=[('Customer', 'Customer'), ('Vendor', 'Vendor')], max_length=50),
        ),
        migrations.AlterField(
            model_name='contact',
            name='first_name',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='contact',
            name='last_name',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='contact',
            name='time_zone',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]