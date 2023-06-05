"""Importer for Indian Stock broker rksv. This can be used to import transactions from Tradebook provided by the broker.
This is entirely based on the Example importer utrade_csv.py written for example broker UTrade by Beancount author Martin Blais.    
"""
__copyright__ = "Copyright (C) 2020  Prabu Anand K"
__license__ = "GNU GPLv3"
__Version__ = "0.1"

import csv
import datetime
import re
import logging
from os import path

from dateutil.parser import parse

from beancount.core.number import D
from beancount.core.number import ZERO
from beancount.core import data
from beancount.core import account
from beancount.core import amount
from beancount.core import position
from beancount.ingest import importer


class RKSVImporter(importer.ImporterProtocol):
    """An importer for RKSV CSV files (an Indian stock broker)."""

    def __init__(self, currency,
                 account_root,
                 account_cash,
                 account_dividends,
                 account_gains,
                 account_fees,
                 account_external):
        self.currency = currency
        self.account_root = account_root
        self.account_cash = account_cash
        self.account_dividends = account_dividends
        self.account_gains = account_gains
        self.account_fees = account_fees
        self.account_external = account_external

    def identify(self, file):
        # Match if the filename is as downloaded and the header has the unique
        # fields combination we're looking for.
        return (re.match(r"rksv\d\d\d\d\d\d\d\d\.csv", path.basename(file.name)) and
                re.match("trade_date,tradingsymbol,", file.head()))

    def extract(self, file):
        # Open the CSV file and create directives.
        entries = []
        index = 0
        with open(file.name) as infile:
            for index, row in enumerate(csv.DictReader(infile)):
                meta = data.new_metadata(file.name, index)
                date = parse(row['trade_date']).date()
                rtype = row['trade_type']
#               link = "{0[order_id]}".format(row)
                desc = "{0[trade_type]} {0[tradingsymbol]} with TradeRef {0[order_id]}".format(row)
                units = amount.Amount(D(row['amount']), self.currency)
                fees = amount.Amount(D(row['fees']), self.currency)
                b_value = amount.add(units, fees)
                s_value = amount.add(units, -fees)
                instrument = row['tradingsymbol']
                rate = D(row['price'])

                if rtype in ('buy', 'sell'):

                    account_inst = account.join(self.account_root, instrument)
                    units_inst = amount.Amount(D(row['quantity']), instrument)
                    account_gains_inst = account.join(self.account_gains, instrument) 

                    if rtype == 'buy':
                        cost = position.Cost(rate, self.currency, None, None)
                        txn = data.Transaction(
                            meta, date, self.FLAG, None, desc, data.EMPTY_SET,data.EMPTY_SET, [
                                data.Posting(account_inst, units_inst, cost, None, None,
                                             None),
                                data.Posting(self.account_fees, fees, None, None, None,
                                             None),
                                data.Posting(self.account_cash, None, None, None, None,
                                             None),
                                
                            ])

                    elif rtype == 'sell':
                        # here the profit or loss goes to PnL account as configured in config.py
                        cost_number = None
                        cost = position.Cost(cost_number, self.currency, None, None)
                        price = amount.Amount(rate, self.currency)
                        account_gains = self.account_gains.format(instrument)
                        txn = data.Transaction(
                            meta, date, self.FLAG, None, desc, data.EMPTY_SET,data.EMPTY_SET, [
                                data.Posting(account_inst, -units_inst, cost, price, None,
                                             None),
                                data.Posting(self.account_fees, fees, None, None, None,
                                             None),                                
                                data.Posting(self.account_cash, s_value, None, None, None,
                                             None),
                                data.Posting(account_gains_inst, None, None, None, None,
                                             None),                     
                                ])

                else:
                    logging.error("Unknown row type: %s; skipping", rtype)
                    continue

                entries.append(txn)

        # Insert a final balance check.
        
        return entries
