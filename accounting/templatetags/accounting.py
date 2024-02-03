# Copyright (c) 2015-2024 Data King Ltd
# See LICENSE file for license details

from django import template
from django.utils.formats import date_format
from django.utils.html import format_html, mark_safe
from django.utils.translation import gettext as _

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

def adjusted_balance(account, date, children):
    return account.get_balance(date=date, children=children) * account.sign

@register.filter
def opening_balance(account, fy, children=False):
    return 0 if account.is_pl_account else \
        adjusted_balance(account, fy.start - timedelta(days=1), children)

@register.filter
def closing_balance(account, fy, children=False):
    return adjusted_balance(account, fy.end, children)

@register.filter
def transactions(account, fy):
    return account.transactions.filter(fiscal_year=fy, closing=False)

@register.filter
def select_accounts(accounts, codes):
    return [accounts.get(code=int(c)) for c in codes.split(',')]

@register.filter
def total_balance(accounts, fy):
    total = 0
    for account in accounts if isinstance(accounts, Iterable) else (accounts,):
        total += account.get_balance(date=fy.end, children=True)
    return total


def format_table(header, body):
    return format_html(
        '<table><thead>{header}</thead><tbody>{body}</tbody></table>',
        header=header,
        body=body
    )

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
    top_level_totals = post_totals

    def append(account, total=False):
        nonlocal stack, show, max_show
        balances = [
            account.get_balance(date=fy.end, children=True) *
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

    for __, acct, next_acct in previous_current_next(accounts):
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
                top_level_totals = False

    empty_cols = ('',) * len(fyears)

    if max_show and top_level_totals:
        max_show -= 1

    def render_accounts(specs, level, right_cols):
        vlevel = max(0, level)
        indent = mark_safe('<td class="indent"></td>' * vlevel)

        def render_row(label, columns, cls):
            return format_html(
                '<tr{cls}>{indent}<td colspan="{span}">{label}</td>{columns}</tr>',
                cls=format_html(' class="{}"', cls) if cls else '',
                columns=columns,
                indent=indent,
                label=label,
                span=max_show - vlevel
            )

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

            columns = mark_safe(
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
            )

            if spec['total']:
                cls = 'total'
            else:
                cls = 'top' if level == -1 else None

            res += render_row(
                account.title,
                '' if post_totals and children else columns,
                cls
            )

            if children:
                if not post_totals:
                    child_rcols = right_cols[1:]
                elif level == -1:
                    child_rcols = ()
                else:
                    child_rcols = [
                        fy_rcols if last else empty_cols
                        for fy_rcols in right_cols
                    ]
                    if len(children) > 1 or children[0]['balances'] != balances:
                        child_rcols.insert(
                            0,
                            [display.currency(balance) for balance in balances]
                        )
                res += render_accounts(children, level + 1, child_rcols)

            if level == -1:
                res += render_row(_('Total'), columns, 'total')

        return mark_safe(res)

    def render_header(text):
        return format_html(
            '<th class="right"{span}>{text}</th>{pad}',
            pad='' if post_totals or max_show == 1 else
                format_html('<th colspan="{}"></th>', max_show - 1),
            text=text,
            span=format_html(' colspan="{}"', max_show) if post_totals else ''
        )

    return format_table(
        format_html(
            '<tr>{indent}{labels}<tr>',
            indent=render_header(''),
            labels=mark_safe(
                ''.join(
                    render_header(
                        fy_template.render(template.Context({'fy': fy}))
                        if fy_template else fy
                    ) for fy in fyears
                )
            )
        ) if multi_fy else '',
        render_accounts(
            stack[0]['children'],
            -1 if top_level_totals else 0,
            () if post_totals else (empty_cols,) * (max_show - 1)
        ),
    )

@register.simple_tag
def account_change_table(fy, accounts):
    header = [''] + [acct.name for acct in accounts]
    rows = []

    def render_dated_label(fmt, date):
        return fmt % {'date': date_format(date, 'SHORT_DATE_FORMAT')}

    def render_balance(balance):
        return display.currency(balance) if balance else ''

    def append_row(title, balances):
        rows.append([title] + [render_balance(balance) for balance in balances])

    def append_txn_row(txn, description):
        balances = [
            acct.get_balance(date=fy.end, children=True, transaction=txn)
            for acct in accounts
        ]
        if any(balances):
            append_row(description, balances)

    append_row(
        render_dated_label(_('Opening balance on %(date)s'), fy.start),
        [opening_balance(acct, fy, children=True) for acct in accounts]
    )

    for txn in fy.transactions.filter(closing=False):
        append_txn_row(txn, txn.description)

    append_txn_row('closing', _('Net earnings'))

    append_row(
        render_dated_label(_('Closing balance on %(date)s'), fy.end),
        [closing_balance(acct, fy, children=True) for acct in accounts]
    )

    i = 1
    while i < len(header):
        for row in rows:
            if row[i]:
                break
        else:
            del header[i]
            for row in rows:
                del row[i]
            continue
        i += 1

    def render_row(columns, tag):
        return format_html(
            '<tr>{}</tr>',
            mark_safe(
                ''.join(
                    format_html(
                        '<{tag}{cls}>{column}</{tag}>',
                        cls=mark_safe(' class="right"') if i else '',
                        column=column,
                        tag=mark_safe(tag)
                    ) for i, column in zip(count(), columns)
                )
            )
        )

    return format_table(
        render_row(header, 'th'),
        mark_safe(''.join(render_row(row, 'td') for row in rows))
    )
