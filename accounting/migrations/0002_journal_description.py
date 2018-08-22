from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='journal',
            name='description',
            field=models.CharField(max_length=64, null=True, blank=True),
        ),
    ]
