# Copyright (c) 2015 Data King Ltd
# See LICENSE file for license details

from django.core.exceptions import ValidationError
from django.db import models
from mptt.models import MPTTModel, TreeForeignKey

import datetime
import operator
import time


def currency_display(amount):
    return '{:0.2f}'.format(amount) if amount else '0.00'


class DateRange(models.Model):
    start = models.DateField()
    end = models.DateField()

    @classmethod
    def by_date(cls, date):
        ranges = cls.objects.filter(start__lte=date, end__gte=date).all()
        if not ranges:
            return cls.generate(date)
        if len(ranges) > 1:
            raise cls.MultipleObjectsReturned
        return ranges[0]

    class Meta:
        abstract = True
        ordering = ('start',)


class FiscalYear(DateRange):
    closed = models.BooleanField(default=False)

    @classmethod
    def generate(cls, date):
        fyears = FiscalYear.objects.order_by('-end').all()
        latest = fyears[0] if fyears else FiscalYear(
            start=datetime.date(datetime.MINYEAR, 1, 1),
            end=datetime.date(date.year, 1, 1) - datetime.timedelta(days=1)
        )
        while latest.end < date:
            start = latest.end + datetime.timedelta(days=1)
            nm = start + datetime.timedelta(days=366)
            end = datetime.date(
                nm.year, nm.month, 1
            ) - datetime.timedelta(days=1)
            latest = FiscalYear.objects.create(start=start, end=end)
        return latest

    def __unicode__(self):
        return unicode(self.end.year)


class FiscalPeriod(DateRange):
    fiscal_year = models.ForeignKey(FiscalYear)

    @classmethod
    def generate(cls, date):
        start = datetime.date(date.year, date.month, 1)
        nm = start + datetime.timedelta(days=31)
        end = datetime.date(nm.year, nm.month, 1) - datetime.timedelta(days=1)

        period = FiscalPeriod(start=start, end=end)
        period.clean()
        period.save()
        return period

    def clean(self):
        self.fiscal_year = FiscalYear.by_date(self.start)
        if FiscalYear.by_date(self.end) != self.fiscal_year:
            raise ValidationError(
                'Fiscal period cannot span multiple fiscal years'
            )

    def __unicode__(self):
        return u'{}/{}'.format(self.start.month, self.start.year)



class Account(MPTTModel):
    name = models.CharField(max_length=64)
    code = models.CharField(max_length=8, blank=True)
    parent = TreeForeignKey(
        'self', blank=True, null=True, related_name='children'
    )
    order = models.CharField(max_length=8, blank=True, editable=False)
    type = models.CharField(
        max_length=2,
        choices=(
            ('As', 'Asset'),
            ('Eq', 'Equity'),
            ('Li', 'Liability'),
            ('In', 'Income'),
            ('Ex', 'Expense')
        )
    )
    frozen = models.BooleanField()
    lot_tracking = models.BooleanField()

    def clean(self):
        try:
            if self.code and Account.objects.get(code=self.code) != self:
                raise ValidationError('Duplicate account code')
        except Account.DoesNotExist:
            pass

    def save(self, **kwargs):
        if self.code:
            order = self.code
        else:
            children = self.children.all()
            order = reduce(
                min, (child.order for child in children)
            ) if children else ''

        changed = order != self.order
        if changed:
            self.order = order

        super(Account, self).save(**kwargs)

        if changed and self.parent:
            self.parent.save()

    def sign(self):
        return -1 if self.type in ('As', 'Ex') else 1

    def balance(self, date=None, lot=None):
        txnsum = 0

        params = {'transaction__state': 'C'}
        if date:
            params['transaction__date__lte'] = date
        if lot:
            params['lot'] = lot
        txnsum = TransactionItem.sum_amount(
            self.transactionitem_set.filter(**params)
        )

        return reduce(
            operator.add,
            (account.balance(date, lot) for account in self.children.all()),
            txnsum
        )

    def balance_display(self):
        return currency_display(self.balance() * self.sign())
    balance_display.short_description = 'balance'

    def transactions(self):
        return Transaction.objects.filter(
            state='C', transactionitem__account=self
        )

    def lots(self):
        return Lot.objects.filter(
            pk__in=[
                r['lot'] for r in self.transactionitem_set.filter(
                    transaction__state='C', lot__isnull=False
                ).values('lot').annotate(
                    models.Sum('amount')
                ) if r['amount__sum']
            ]
        ).all()

    def period_totals(self):
        totals = {}
        keys = {'debit': 'lt', 'credit': 'gt'}

        def update(key, comparison):
            for period in FiscalPeriod.objects.filter(
                models.Q(transaction__state='C') &
                models.Q(transaction__transactionitem__account=self) &
                models.Q(
                    **{
                        (
                            'transaction__transactionitem__amount__' +
                            comparison
                        ): 0
                    }
                )
            ).annotate(
                models.Sum('transaction__transactionitem__amount')
            ):
                totals.setdefault(period, {})[key] = abs(
                    period.transaction__transactionitem__amount__sum
                )

        for key, comparison in keys.items():
            update(key, comparison)

        for child in self.children.all():
            for period, pt in child.period_totals().items():
                for key in keys:
                    totals[period][key] = totals.setdefault(
                        period, {}
                    ).get(key, 0) + pt.get(key, 0)

        for pt in totals.values():
            for key in keys:
                pt.setdefault(key, 0)
            pt['balance'] = (pt['credit'] - pt['debit']) * self.sign()

        return totals

    class MPTTMeta:
        order_insertion_by = ('order',)

    def __unicode__(self):
        return ((self.code + ' ') if self.code else u'') + self.name


class Lot(models.Model):
    account = models.ForeignKey(Account, editable=False)
    fiscal_year = models.ForeignKey(FiscalYear, editable=False)
    number = models.IntegerField(editable=False)

    def balance(self):
        return self.account.balance(lot=self)

    def balance_display(self):
        return currency_display(self.balance() * self.account.sign())
    balance_display.short_description = 'balance'

    def transactions(self):
        return Transaction.objects.filter(state='C', transactionitem__lot=self)

    class Meta:
        ordering = ('account', 'fiscal_year', 'number')
        unique_together = ('account', 'fiscal_year', 'number')

    def __unicode__(self):
        return u'{}/{}'.format(self.fiscal_year, self.number)
    __unicode__.short_description = 'lot'



class Journal(models.Model):
    code = models.CharField(max_length=8)

    def issue_number(self, txn):
        return (
            self.transaction_set.filter(
                fiscal_year=txn.fiscal_year
            ).aggregate(models.Max('number'))['number__max'] or 0
        ) + 1

    def transactions(self):
        return self.transaction_set.filter(state='C')

    class Meta:
        ordering = ('code',)

    def __unicode__(self):
        return self.code


class Transaction(models.Model):
    fiscal_year = models.ForeignKey(
        FiscalYear, blank=True, null=True, editable=False
    )
    period = models.ForeignKey(
        FiscalPeriod, blank=True, null=True, editable=False
    )
    journal = models.ForeignKey(Journal)
    number = models.IntegerField(blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    description = models.CharField(max_length=64, blank=True)
    state = models.CharField(
        max_length=1,
        choices=(('D', 'Draft'), ('C', 'Committed')),
        default='D',
        editable=False
    )

    def balance(self):
        return TransactionItem.sum_amount(self.transactionitem_set)

    def balance_display(self):
        return currency_display(self.balance())
    balance_display.short_description = 'balance'

    def commit(self):
        if self.state != 'D':
            raise ValidationError('Transaction {} already closed'.format(self))

        if not self.transactionitem_set.all():
            raise ValidationError('Cannot commit an empty transaction')

        if self.balance():
            raise ValidationError('Imbalanced transaction')

        if not self.date:
            self.date = datetime.date.fromtimestamp(time.time())
        self.period = FiscalPeriod.by_date(self.date)
        self.fiscal_year = self.period.fiscal_year
        if self.fiscal_year.closed:
            raise ValidationError(
                'Fiscal year {} already closed'.format(self.fiscal_year)
            )

        for item in self.transactionitem_set.all():
            if item.account.lot_tracking and not item.lot:
                params = {
                    'fiscal_year': self.fiscal_year, 'account': item.account
                }
                params['number'] = (
                    Lot.objects.filter(**params).aggregate(
                        models.Max('number')
                    )['number__max'] or 0
                ) + 1
                item.lot = Lot.objects.create(**params)
            item.clean()
            item.save()

        if self.number:
            if Transaction.objects.filter(
                    fiscal_year=self.fiscal_year,
                    journal=self.journal,
                    number=self.number
            ):
                raise ValidationError('Duplicate transaction number')
        else:
            self.number = self.journal.issue_number(self)

        self.state = 'C'
        self.save()

    class Meta:
        ordering = ('date', 'journal', 'number', 'id')
        unique_together = ('fiscal_year', 'journal', 'number')

    def __unicode__(self):
        if self.state == 'C':
            return u'{}/{}{}'.format(
                self.fiscal_year, self.journal, self.number
            )
        return u'#{}{}'.format(
            self.id,
            u' ({})'.format(self.date) if self.date else ''
        )
    __unicode__.short_description = 'transaction'


class TransactionItem(models.Model):
    transaction = models.ForeignKey(Transaction)
    account = models.ForeignKey(Account, limit_choices_to={'frozen': False})
    lot = models.ForeignKey(Lot, blank=True, null=True)
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    description = models.CharField(max_length=64, blank=True)

    @staticmethod
    def sum_amount(items):
        res = items.aggregate(models.Sum('amount'))['amount__sum']        
        return res if res else 0

    def debit(self):
        return currency_display(-self.amount) if self.amount < 0 else ''

    def credit(self):
        return currency_display(self.amount) if self.amount > 0 else ''

    def clean(self):
        try:
            if self.account.frozen:
                raise ValidationError(
                    u'Account frozen: ' + unicode(self.account)
                )
        except Account.DoesNotExist:
            return

        if self.lot and self.lot.account != self.account:
            raise ValidationError('Lot does not match the account')

    def __unicode__(self):
        return u''
