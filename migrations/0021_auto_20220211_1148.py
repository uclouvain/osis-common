
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('osis_common', '0020_alter_documentfile_file'),
    ]

    operations = [
        migrations.AlterField(
            model_name='messagequeuecache',
            name='data',
            field=models.JSONField(),
        ),
        migrations.AlterField(
            model_name='queueexception',
            name='message',
            field=models.JSONField(null=True),
        ),
    ]
