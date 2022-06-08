# Copyright (c) 2015-2022 Data King Ltd
# See LICENSE file for license details

def currency(amount):
    return f'{amount:0.2f}' if amount else '0.00'
