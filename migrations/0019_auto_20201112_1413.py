# Generated by Django 2.2.13 on 2020-11-12 14:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('osis_common', '0018_auto_20190506_1610'),
    ]

    operations = [
        migrations.AlterField(
            model_name='messagehistory',
            name='receiver_email',
            field=models.TextField(blank=True, null=True),
        ),
    ]
