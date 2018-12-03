from django.db import migrations, models
import mptt.fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=64)),
                ('code', models.CharField(max_length=8, blank=True)),
                ('order', models.CharField(max_length=8, editable=False, blank=True)),
                ('type', models.CharField(max_length=2, choices=[(b'As', b'Asset'), (b'Eq', b'Equity'), (b'Li', b'Liability'), (b'In', b'Income'), (b'Ex', b'Expense')])),
                ('frozen', models.BooleanField()),
                ('lot_tracking', models.BooleanField()),
                ('lft', models.PositiveIntegerField(editable=False, db_index=True)),
                ('rght', models.PositiveIntegerField(editable=False, db_index=True)),
                ('tree_id', models.PositiveIntegerField(editable=False, db_index=True)),
                ('level', models.PositiveIntegerField(editable=False, db_index=True)),
                ('parent', mptt.fields.TreeForeignKey(related_name='children', blank=True, to='accounting.Account', null=True, on_delete=models.PROTECT)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='FiscalPeriod',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start', models.DateField()),
                ('end', models.DateField()),
            ],
            options={
                'ordering': ('start',),
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='FiscalYear',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start', models.DateField()),
                ('end', models.DateField()),
                ('closed', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ('start',),
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Journal',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(max_length=8)),
            ],
            options={
                'ordering': ('code',),
            },
        ),
        migrations.CreateModel(
            name='Lot',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('number', models.IntegerField(editable=False)),
                ('account', models.ForeignKey(editable=False, to='accounting.Account', on_delete=models.PROTECT)),
                ('fiscal_year', models.ForeignKey(editable=False, to='accounting.FiscalYear', on_delete=models.PROTECT)),
            ],
            options={
                'ordering': ('account__order', 'fiscal_year__start', 'number'),
            },
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('number', models.IntegerField(null=True, blank=True)),
                ('date', models.DateField(null=True, blank=True)),
                ('description', models.CharField(max_length=128, blank=True)),
                ('state', models.CharField(default=b'D', max_length=1, editable=False, choices=[(b'D', b'Draft'), (b'C', b'Committed')])),
                ('fiscal_year', models.ForeignKey(blank=True, editable=False, to='accounting.FiscalYear', null=True, on_delete=models.PROTECT)),
                ('journal', models.ForeignKey(to='accounting.Journal', on_delete=models.PROTECT)),
                ('period', models.ForeignKey(blank=True, editable=False, to='accounting.FiscalPeriod', null=True, on_delete=models.PROTECT)),
            ],
            options={
                'ordering': ('date', 'journal__code', 'number', 'id'),
            },
        ),
        migrations.CreateModel(
            name='TransactionItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('amount', models.DecimalField(max_digits=16, decimal_places=2)),
                ('description', models.CharField(max_length=64, blank=True)),
                ('account', models.ForeignKey(to='accounting.Account', on_delete=models.PROTECT)),
                ('lot', models.ForeignKey(blank=True, to='accounting.Lot', null=True, on_delete=models.PROTECT)),
                ('transaction', models.ForeignKey(to='accounting.Transaction', on_delete=models.PROTECT)),
            ],
        ),
        migrations.AddField(
            model_name='fiscalperiod',
            name='fiscal_year',
            field=models.ForeignKey(to='accounting.FiscalYear', on_delete=models.PROTECT),
        ),
        migrations.AlterUniqueTogether(
            name='transaction',
            unique_together=set([('fiscal_year', 'journal', 'number')]),
        ),
        migrations.AlterUniqueTogether(
            name='lot',
            unique_together=set([('account', 'fiscal_year', 'number')]),
        ),
    ]
