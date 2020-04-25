# Copyright (c) 2015-2022 Data King Ltd
# See LICENSE file for license details

from django import template
from django.utils.html import format_html, mark_safe

from datetime import timedelta

from .. import display

register = template.Library()

@register.filter
def currency(amount):
    return display.currency(amount)

def adjusted_balance(account, **kwargs):
    return account.balance(**kwargs) * account.sign()

@register.filter
def opening_balance(account, fy):
    return adjusted_balance(
        account, date=fy.start - timedelta(days=1), include_closing=True
    )

@register.filter
def closing_balance(account, fy):
    return adjusted_balance(account, date=fy.end)

@register.filter
def transactions(account, fy):
    return account.transactions().filter(fiscal_year=fy, closing=False)

@register.simple_tag
def account_chart(accounts, fy):
    levels = max((account.get_level() for account in accounts)) + 1
    res = ''
    for account in accounts:
        level = account.get_level()
        res += format_html(
            '<tr>{indent}<td colspan="{span}">{account}</td>{indent}<td class="currency">{balance}</td></tr>',
            account=account,
            balance=account.balance_display(date=fy.end),
            indent=mark_safe('<td class="indent"></td>' * level),
            span=levels - level
        )
    return format_html('<table>{}</table>', mark_safe(res))
