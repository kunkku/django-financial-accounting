# Copyright (c) 2015-2024 Data King Ltd
# See LICENSE file for license details

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext as _
from mptt.models import MPTTModel, TreeForeignKey

import collections
import datetime
from decimal import Decimal as D
import functools
import operator
import time

from . import display, managers


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

    def __lt__(self, rng):
        return self.end < rng.end


class FiscalYear(DateRange):
    closed = models.BooleanField(default=False, editable=False)
    properties = models.JSONField(blank=True, null=True)

    @classmethod
    def generate(cls, date):
        fyears = FiscalYear.objects.order_by('-end').all()
        latest = fyears[0] if fyears else FiscalYear(
            start=datetime.date(datetime.MINYEAR, 1, 1),
            end=datetime.date(date.year, 1, 1) - datetime.timedelta(days=1)
        )
        if date < latest.start:
            raise FiscalYear.DoesNotExist
        while latest.end < date:
            start = latest.end + datetime.timedelta(days=1)
            nm = start + datetime.timedelta(days=366)
            end = datetime.date(
                nm.year, nm.month, 1
            ) - datetime.timedelta(days=1)
            latest = FiscalYear.objects.create(start=start, end=end)
        return latest

    def __str__(self):
        i = FiscalYear.objects.filter(
            end__gte=datetime.date(self.end.year, 1, 1), end__lt=self.end
        ).count()
        return str(self.end.year) + (chr(64 + i) if i else '')
    __str__.short_description = 'Fiscal year'

    @property
    def transactions(self):
        return self.transaction_set.filter(state='C')

    def close(self):
        if self.closed:
            raise ValidationError(f'Fiscal year {self} already closed')

        txn = None
        profit = 0

        for account in Account.objects.all():
            if not account.is_pl_account:
                continue
            balance = account.get_balance(date=self.end)
            if not balance:
                continue
            if not txn:
                txn = Transaction.objects.create(
                    journal=Journal.get_closing(),
                    date=self.end,
                    description=_(
                        'Net earnings during fiscal year {}'
                    ).format(self),
                    closing=True
                )
            txn.items.create(account=account, amount=-balance)
            profit += balance

        if txn:
            if profit:
                txn.items.create(
                    account=Account.objects.get(type='NE'), amount=profit
                )
            txn.commit()

        self.closed = True
        self.save()


class FiscalPeriod(DateRange):
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.PROTECT)

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

    def __str__(self):
        return f'{self.start.month}/{self.start.year}'



class Account(MPTTModel):
    name = models.CharField(max_length=64)
    code = models.CharField(max_length=8, blank=True)
    parent = TreeForeignKey(
        'self',
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name='children'
    )
    order = models.CharField(max_length=8, blank=True, editable=False)
    type = models.CharField(
        max_length=2,
        choices=(
            ('As', 'Asset'),
            ('Eq', 'Equity'),
            ('NE', 'Net earnings'),
            ('Li', 'Liability'),
            ('In', 'Income'),
            ('Ex', 'Expense')
        )
    )
    public = models.BooleanField()
    frozen = models.BooleanField()
    lot_tracking = models.BooleanField()

    TYPES_PL = ('In', 'Ex')

    objects = managers.AccountManager()
    balance_accounts = managers.AccountManager('As', 'Eq', 'NE', 'Li')
    pl_accounts = managers.AccountManager(*TYPES_PL)
    equity_accounts = managers.AccountManager('Eq', 'NE')

    def clean(self):
        try:
            if self.code and Account.objects.get(code=self.code) != self:
                raise ValidationError('Duplicate account code')
        except Account.DoesNotExist:
            pass

    def save(self, **kwargs):
        if self.is_pl_account:
            self.lot_tracking = False

        old_parent = None
        if self.pk:
            old_obj = Account.objects.get(pk=self.pk)
            old_parent = old_obj.parent

            if self.lot_tracking and not old_obj.lot_tracking:
                balance = self.get_balance()
                if balance:
                    fyears = FiscalYear.objects.filter(closed=False)
                    if fyears.exists():
                        fy = fyears.order_by('start')[0]
                        date = fy.transactions.aggregate(models.Max('date'))[
                            'date__max'
                        ]
                    else:
                        date = FiscalYear.objects.order_by('-end')[0].end + \
                            datetime.timedelta(days=1)
                        fy = FiscalYear.by_date(date)

                    txn = Transaction.objects.create(
                        journal=Journal.get_closing(),
                        date=date,
                        description=_('Initial lot allocation')
                    )
                    txn.items.create(account=self, amount=-balance)
                    txn.items.create(
                        account=self,
                        lot=Lot.objects.create(account=self, fiscal_year=fy),
                        amount=balance
                    )
                    txn.commit()

        if self.code:
            order = self.code
        else:
            children = self.children.all() if self.pk else ()
            order = functools.reduce(
                min, (child.order for child in children)
            ) if children else ''

        order_changed = order != self.order
        if order_changed:
            self.order = order

        super().save(**kwargs)

        def update(account):
            if account:
                Account.objects.get(pk=account.pk).save()

        parent_changed = self.parent != old_parent

        if order_changed or parent_changed:
            update(self.parent)

        if parent_changed:
            update(old_parent)

    @property
    def is_pl_account(self):
        return self.type in self.TYPES_PL

    @property
    def title(self):
        return ((self.code + ' ') if self.code else '') + self.name

    @property
    def sign(self):
        return -1 if self.type in ('As', 'Ex') else 1

    def get_balance(
        self,
        date=None,
        children=False,
        lot=None,
        transaction=None,
    ):
        if transaction == 'closing':
            balance = 0
        else:
            items = self.items
            if lot:
                items = items.filter(lot=lot)
            if transaction:
                items = items.filter(transaction=transaction)
            balance = TransactionItem.get_total_balance(items, date)

        if not children:
            return balance

        if self.type == 'NE' and transaction in (None, 'closing'):
            balance += TransactionItem.get_total_balance(
                TransactionItem.objects.filter(account__type__in=self.TYPES_PL),
                date
            )

        return functools.reduce(
            operator.add,
            (
                account.get_balance(
                    date=date, children=True, lot=lot, transaction=transaction
                )
                for account in self.children.all()
            ),
            balance
        )

    def get_balance_display(self):
        return display.currency(self.get_balance(children=True) * self.sign)
    get_balance_display.short_description = 'balance'

    @property
    def transactions(self):
        return Transaction.objects.filter(
            state='C', item__account=self
        ).distinct()

    @property
    def lots(self):
        return self.get_lots(True)

    def get_lots(self, active_only=False):
        return Lot.objects.filter(
            pk__in=[
                r['lot'] for r in self.items.filter(
                    transaction__state='C', lot__isnull=False
                ).values('lot').annotate(models.Sum('amount'))
                if not active_only or
                TransactionItem.correct_sum(r['amount__sum'])
            ]
        ).all()

    @property
    def period_totals(self):
        keys = {'debit': 'lt', 'credit': 'gt'}

        class PeriodDict(collections.defaultdict):
            def __missing__(self, period):
                pt = {'period': period}
                for key in keys:
                    pt[key] = 0

                self[period] = pt
                return pt

        totals = PeriodDict()

        def update(key, comparison):
            for period in FiscalPeriod.objects.filter(
                models.Q(transaction__state='C') &
                models.Q(transaction__item__account=self) &
                models.Q(
                    **{
                        (
                            'transaction__item__amount__' + comparison
                        ): 0
                    }
                )
            ).annotate(
                models.Sum('transaction__item__amount')
            ):
                totals[period][key] = abs(
                    TransactionItem.correct_sum(
                        period.transaction__item__amount__sum
                    )
                )

        for key, comparison in keys.items():
            update(key, comparison)

        for child in self.children.all():
            for cpt in child.period_totals:
                pt = totals[cpt['period']]
                for key in keys:
                    pt[key] += cpt[key]

        for pt in totals.values():
            pt['balance'] = (pt['credit'] - pt['debit']) * self.sign

        return list(totals.values())

    class MPTTMeta:
        order_insertion_by = ('order',)

    def __str__(self):
        return self.title


class Lot(models.Model):
    account = models.ForeignKey(
        Account, editable=False, on_delete=models.PROTECT
    )
    fiscal_year = models.ForeignKey(
        FiscalYear, editable=False, on_delete=models.PROTECT
    )
    number = models.IntegerField(editable=False)
    description = models.CharField(max_length=128, blank=True)

    @property
    def title(self):
        return self.description or str(self)

    @property
    def sign(self):
        return self.account.sign

    @property
    def balance(self):
        return self.get_balance()

    def save(self, **kwargs):
        if not self.number:
            self.number = (
                Lot.objects.filter(
                    account=self.account, fiscal_year=self.fiscal_year
                ).aggregate(models.Max('number'))['number__max'] or 0
            ) + 1
        super().save(**kwargs)

    def get_balance(self, date=None, children=False):
        return self.account.get_balance(date=date, lot=self)

    def get_balance_display(self):
        return display.currency(self.balance * self.account.sign)
    get_balance_display.short_description = 'balance'

    @property
    def transactions(self):
        return Transaction.objects.filter(state='C', item__lot=self)

    class Meta:
        ordering = ('account__order', 'fiscal_year__start', 'number')
        unique_together = ('account', 'fiscal_year', 'number')

    def __str__(self):
        return f'{self.fiscal_year}/{self.number}'
    __str__.short_description = 'lot'



class Journal(models.Model):
    code = models.CharField(max_length=8)
    description = models.CharField(max_length=64, blank=True, null=True)
    closing = models.BooleanField(default=False)

    @staticmethod
    def get_closing():
        return Journal.objects.get(closing=True)

    def issue_number(self, txn):
        return (
            self.transaction_set.filter(
                fiscal_year=txn.fiscal_year
            ).aggregate(models.Max('number'))['number__max'] or 0
        ) + 1

    @property
    def transactions(self):
        return self.transaction_set.filter(state='C')

    class Meta:
        ordering = ('code',)

    def __str__(self):
        return self.code


class Transaction(models.Model):
    fiscal_year = models.ForeignKey(
        FiscalYear,
        blank=True,
        null=True,
        editable=False,
        on_delete=models.PROTECT
    )
    period = models.ForeignKey(
        FiscalPeriod,
        blank=True,
        null=True,
        editable=False,
        on_delete=models.PROTECT
    )
    journal = models.ForeignKey(Journal, on_delete=models.PROTECT)
    number = models.IntegerField(blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    description = models.CharField(max_length=128, blank=True)
    state = models.CharField(
        max_length=1,
        choices=(('D', 'Draft'), ('C', 'Committed')),
        default='D',
        editable=False
    )
    closing = models.BooleanField(default=False, editable=False)

    @property
    def balance(self):
        return TransactionItem.sum_amount(self.items)

    def get_balance_display(self):
        return display.currency(self.balance)
    get_balance_display.short_description = 'balance'

    def commit(self):
        if self.state != 'D':
            raise ValidationError(f'Transaction {self} already closed')

        if not self.items.all():
            raise ValidationError('Cannot commit an empty transaction')

        if self.balance:
            raise ValidationError('Imbalanced transaction')

        if not self.date:
            self.date = datetime.date.fromtimestamp(time.time())
        self.period = FiscalPeriod.by_date(self.date)
        self.fiscal_year = self.period.fiscal_year
        if self.fiscal_year.closed:
            raise ValidationError(
                f'Fiscal year {self.fiscal_year} already closed'
            )

        if self.number:
            if Transaction.objects.filter(
                    fiscal_year=self.fiscal_year,
                    journal=self.journal,
                    number=self.number
            ).exclude(pk=self.pk):
                raise ValidationError('Duplicate transaction number')
        else:
            self.number = self.journal.issue_number(self)

        for item in self.items.all():
            if item.account.lot_tracking and not item.lot:
                item.lot = Lot.objects.create(
                    account=item.account, fiscal_year=self.fiscal_year
                )
            item.clean()
            item.save()

        self.state = 'C'
        self.save()

    class Meta:
        ordering = ('date', 'journal__code', 'number', 'id')
        unique_together = ('fiscal_year', 'journal', 'number')

    def __str__(self):
        if self.state == 'C':
            return f'{self.fiscal_year}/{self.journal}{self.number}'
        return '#{}{}'.format(self.id, f' ({self.date})' if self.date else '')
    __str__.short_description = 'transaction'


class TransactionItem(models.Model):
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.PROTECT,
        related_name='items',
        related_query_name='item'
    )
    account = models.ForeignKey(
        Account,
        limit_choices_to={'frozen': False},
        on_delete=models.PROTECT,
        related_name='items',
        related_query_name='item'
    )
    lot = models.ForeignKey(
        Lot,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name='items',
        related_query_name='item'
    )
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    description = models.CharField(max_length=64, blank=True)

    @staticmethod
    def correct_sum(amount):
        if not amount:
            return amount

        res = amount.quantize(D('0.01'))

        if settings.DATABASES[TransactionItem.objects.db]['ENGINE'] != \
            'django.db.backends.sqlite3':

            assert(res == amount)

        return res

    @staticmethod
    def sum_amount(items):
        res = TransactionItem.correct_sum(
            items.aggregate(models.Sum('amount'))['amount__sum']
        )
        return res if res else 0

    @staticmethod
    def get_total_balance(items, date=None):
        items = items.filter(transaction__state='C')
        if date:
            items = items.filter(
                models.Q(transaction__date__lt=date) | (
                    models.Q(transaction__date=date) &
                    models.Q(transaction__closing=False)
                )
            )
        return TransactionItem.sum_amount(items)

    @property
    def debit(self):
        return display.currency(-self.amount) if self.amount < 0 else ''

    @property
    def credit(self):
        return display.currency(self.amount) if self.amount > 0 else ''

    def clean(self):
        try:
            if self.account.frozen:
                raise ValidationError(
                    'Account frozen: ' + str(self.account)
                )
        except Account.DoesNotExist:
            return

        if self.lot and self.lot.account != self.account:
            raise ValidationError('Lot does not match the account')

    def __str__(self):
        return ''
