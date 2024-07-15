"""Importer for US Stock broker Etrade. This can be used to import transactions from transactions log provided by the broker.
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


class ETradeImporter(importer.ImporterProtocol):
    """An importer for ETrade CSV files (an example investment bank)."""

    def __init__(self, currency,
                 account_root,
                 account_cash,
                 account_dividends,
                 account_gains,
                 account_fees,
                 account_withholdingtax,
                 account_external):
        self.currency = currency
        self.account_root = account_root
        self.account_cash = account_cash
        self.account_dividends = account_dividends
        self.account_gains = account_gains
        self.account_fees = account_fees
        self.account_withholdingtax = account_withholdingtax
        self.account_external = account_external

    def identify(self, file):
        # Match if the filename is as downloaded and the header has the unique
        # fields combination we're looking for.
        return (re.match(r"etrade\d\d\d\d\d\d\d\d\.csv", path.basename(file.name)) and
                re.match("TransactionDate,TransactionType,SecurityType", file.head()))

    def extract(self, file):
        # Open the CSV file and create directives.
        entries = []
        index = 0
        with open(file.name) as infile:
            for index, row in enumerate(csv.DictReader(infile)):
                meta = data.new_metadata(file.name, index)
                date = parse(row['TransactionDate']).date()
                rtype = row['TransactionType']
                link = "ut{0[SecurityType]}".format(row)
                desc = "({0[TransactionType]}) {0[Description]}".format(row)
                units = amount.Amount(D(row['Amount']), self.currency)
                fees = amount.Amount(D(row['Commission']), self.currency)
                other = amount.add(units, fees)
                instrument = row['Symbol']
                rate = D(row['Price'])

                if rtype == 'Dividend':
                    assert fees.number == ZERO

                    account_dividends = self.account_dividends.format(instrument)

                    txn = data.Transaction(
                        meta, date, self.FLAG, None, desc, data.EMPTY_SET, data.EMPTY_SET, [
                            data.Posting(self.account_cash, units, None, None, None, None),
                            data.Posting(account_dividends, -other, None, None, None, None),
                        ])
                    
                # elif rtype == 'Tax':
                elif rtype in ('Tax', 'MISC'):    
                    assert fees.number == ZERO

                    account_withholdingtax = self.account_withholdingtax.format(instrument)

                    txn = data.Transaction(
                        meta, date, self.FLAG, None, desc, data.EMPTY_SET, data.EMPTY_SET, [
                            data.Posting(self.account_cash, units, None, None, None, None),
                            data.Posting(account_withholdingtax, -other, None, None, None, None),
                        ])    

                elif rtype == 'Interest':
                    assert fees.number == ZERO
                    txn = data.Transaction(
                        meta, date, self.FLAG, None, desc, data.EMPTY_SET, data.EMPTY_SET, [
                            data.Posting(self.account_cash, units, None, None, None,
                                         None),
                            data.Posting(self.account_external, -other, None, None, None,
                                         None),
                        ])

                elif rtype in ('Wire', 'Fee'):
                    # assert fees.number == ZERO
                    txn = data.Transaction(
                        meta, date, self.FLAG, None, desc, data.EMPTY_SET, data.EMPTY_SET, [
                            data.Posting(self.account_cash, -units, None, None, None,
                                         None),
                            data.Posting("Expenses:FixMe", other, None, None, None,
                                         None),
                        ])


                elif rtype in ('Bought', 'Sold'):

                    account_inst = account.join(self.account_root, instrument)
                    units_inst = amount.Amount(D(row['Quantity']), instrument)
                    

                    if rtype == 'Bought':
                        cost = position.Cost(rate, self.currency, None, None)
                        txn = data.Transaction(
                            meta, date, self.FLAG, None, desc, data.EMPTY_SET, data.EMPTY_SET, [
                                data.Posting(self.account_cash, units, None, None, None,
                                             None),
                                data.Posting(self.account_fees, fees, None, None, None,
                                             None),
                                data.Posting(account_inst, units_inst, cost, None, None,
                                             None),
                            ])

                    elif rtype == 'Sold':
                        # Extract the lot. In practice this information not be there
                        # and you will have to identify the lots manually by editing
                        # the resulting output. You can leave the cost.number slot
                        # set to None if you like.
                        cost_number = None
                        cost = position.Cost(cost_number, self.currency, None, None)
                        price = amount.Amount(rate, self.currency)
                        account_gains = self.account_gains.format(instrument)
                        txn = data.Transaction(
                            meta, date, self.FLAG, None, desc, data.EMPTY_SET, data.EMPTY_SET, [
                                data.Posting(self.account_cash, units, None, None, None,
                                             None),
                                data.Posting(self.account_fees, fees, None, None, None,
                                             None),
                                data.Posting(account_inst, units_inst, cost, price, None,
                                             None),
                                data.Posting(account_gains, None, None, None, None,
                                             None),
                            ])

                else:
                    logging.error("Unknown row type: %s; skipping", rtype)
                    continue

                entries.append(txn)

        # Insert a final balance check.
       
        return entries
