# Copyright (c) 2015-2022 Data King Ltd
# See LICENSE file for license details

from django import template
from django.utils.html import format_html, mark_safe

from collections.abc import Iterable
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


INDENT = '<td class="indent"></td>'

@register.simple_tag
def account_chart(accounts, fy, include_closing=False):
    max_level = max((account.get_level() for account in accounts))
    fyears = fy if isinstance(fy, Iterable) else (fy,)

    res = ''
    for account in accounts:
        level = account.get_level()
        rlevel = max_level - level

        left_pad = mark_safe(INDENT * level)
        right_pad = mark_safe(INDENT * rlevel)

        row = format_html(
            '{indent}<td colspan="{span}">{account}</td>',
            account=account,
            indent=left_pad,
            span=rlevel + 1
        )
        for fy in fyears:
            row += format_html('{left_pad}<td class="currency">{balance}</td>{right_pad}',
                balance=account.balance_display(
                    date=fy.end, include_closing=include_closing
                ),
                left_pad=left_pad,
                right_pad=right_pad
            )
        res += format_html('<tr>{}</tr>', mark_safe(row))

    return format_html('<table>{}</table>', mark_safe(res))
