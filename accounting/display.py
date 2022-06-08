# Copyright (c) 2015-2022 Data King Ltd
# See LICENSE file for license details

from django.utils.formats import number_format

def currency(amount):
    return number_format(
        amount if amount else 0, decimal_pos=2, force_grouping=True
    )
