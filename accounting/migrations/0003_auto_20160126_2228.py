from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0002_journal_description'),
    ]

    operations = [
        migrations.AddField(
            model_name='journal',
            name='closing',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='transaction',
            name='closing',
            field=models.BooleanField(default=False, editable=False),
        ),
        migrations.AlterField(
            model_name='account',
            name='type',
            field=models.CharField(max_length=2, choices=[(b'As', b'Asset'), (b'Eq', b'Equity'), (b'NE', b'Net earnings'), (b'Li', b'Liability'), (b'In', b'Income'), (b'Ex', b'Expense')]),
        ),
    ]
