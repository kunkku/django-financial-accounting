from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0003_auto_20160126_2228'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fiscalyear',
            name='closed',
            field=models.BooleanField(default=False, editable=False),
        ),
    ]
