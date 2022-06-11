# Copyright (c) 2015-2023 Data King Ltd
# See LICENSE file for license details

from django import template
from django.utils.html import format_html, mark_safe

from mptt.utils import previous_current_next

from collections.abc import Iterable
from datetime import timedelta
from itertools import count

from .. import display

register = template.Library()

@register.filter
def reverse(iterable):
    return reversed(iterable)

@register.filter
def currency(amount):
    return display.currency(amount)

def adjusted_balance(account, **kwargs):
    return account.get_balance(**kwargs) * account.sign

@register.filter
def opening_balance(account, fy):
    return 0 if account.is_pl_account else \
        adjusted_balance(account, date=fy.start - timedelta(days=1))

@register.filter
def closing_balance(account, fy):
    return adjusted_balance(account, date=fy.end)

@register.filter
def transactions(account, fy):
    return account.transactions.filter(fiscal_year=fy, closing=False)


@register.simple_tag
def account_chart(
    accounts,
    fy,
    fy_template=None,
    lots=False,
    post_totals=False,
    signed=False,
    zero_rows=True
):
    multi_fy = isinstance(fy, Iterable)
    fyears = tuple(fy) if multi_fy else (fy,)

    if fy_template:
        fy_template = template.Template(fy_template)

    stack = [{'children': []}]
    show = 0
    max_show = 1
    first = None

    def append(account, total=False):
        nonlocal stack, show, max_show
        balances = [
            account.get_total_balance(date=fy.end) *
            (1 if signed else account.sign) for fy in fyears
        ]
        if zero_rows or any(balances):
            show = len(stack)
            max_show = max(max_show, show)
        stack.append(
            {
                'account': account,
                'balances': balances,
                'children': [],
                'total': total
            }
        )

    def flush():
        nonlocal stack, show
        spec = stack.pop()
        if len(stack) == show:
            stack[-1]['children'].append(spec)
            show -= 1
        return spec['account']

    for _, acct, next_acct in previous_current_next(accounts):
        if not first:
            first = acct

        append(acct)
        if lots:
            for lot in acct.get_lots():
                append(lot)
                flush()

        ancs = list((next_acct or first).get_ancestors())
        if not next_acct:
            for anc in acct.get_ancestors(ascending=True):
                if anc in ancs:
                    ancs.remove(anc)
                    break

        while stack[-1]['account'] not in ancs:
            acc = flush()
            if len(stack) == 1:
                parent = acc.parent
                if not parent or parent in ancs:
                    break
                append(parent, True)

    empty_cols = ('',) * len(fyears)

    def render_accounts(specs, level, right_cols):
        indent = mark_safe('<td class="indent"></td>' * level)

        left_span = max_show - len(right_cols) - 1
        left_col = mark_safe(
            format_html('<td colspan="{}">', left_span) if left_span else ''
        )

        res = ''

        for i, spec in zip(count(), specs):
            account = spec['account']
            balances = spec['balances']
            children = spec['children']

            last = i == len(specs) - 1

            res += format_html(
                '<tr{total}>{indent}<td colspan="{span}">{account}</td>{balances}</tr>',
                account=account.title,
                balances='' if post_totals and children else mark_safe(
                    ''.join(
                        format_html(
                            '{left_col}<td class="right">{balance}</td>{right_cols}',
                            balance=display.currency(balance),
                            left_col=left_col,
                            right_cols=mark_safe(
                                ''.join(
                                    format_html(
                                        '<td class="right">{}</td>',
                                        fy_rcols[j] if last else ''
                                    ) for fy_rcols in right_cols
                                )
                            )
                        ) for j, balance in zip(count(), balances)
                    )
                ),
                indent=indent,
                span=max_show - level,
                total=mark_safe(' class="total"') if spec['total'] else ''
            )

            if children:
                if post_totals:
                    child_rcols = [
                        fy_rcols if last else empty_cols
                        for fy_rcols in right_cols
                    ]
                    if len(children) > 1 or children[0]['balances'] != balances:
                        child_rcols.insert(
                            0,
                            [display.currency(balance) for balance in balances]
                        )
                else:
                    child_rcols = right_cols[1:]
                res += render_accounts(children, level + 1, child_rcols)

        return mark_safe(res)

    def render_header(text):
        return format_html(
            '<th class="right"{span}>{text}</th>{pad}',
            pad='' if post_totals or max_show == 1 else
                format_html('<th colspan="{}"></th>', max_show - 1),
            text=text,
            span=format_html(' colspan="{}"', max_show) if post_totals else ''
        )

    return format_html(
        '<table>{header}<tbody>{body}</tbody></table>',
        body=render_accounts(
            stack[0]['children'],
            0,
            () if post_totals else (empty_cols,) * (max_show - 1)
        ),
        header=format_html(
            '<thead><tr>{indent}{labels}</tr></thead>',
            indent=render_header(''),
            labels=mark_safe(
                ''.join(
                    render_header(
                        fy_template.render(template.Context({'fy': fy}))
                        if fy_template else fy
                    ) for fy in fyears
                )
            )
        ) if multi_fy else ''
    )
