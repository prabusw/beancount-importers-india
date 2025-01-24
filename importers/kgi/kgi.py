"""Importer for Thailand Stock broker KGI. The entries are to be manually created in csv format.
This is entirely based on the Example importer utrade_csv.py written for example broker UTrade by Beancount author Martin Blais.
v0.2, changes made to account for dividend cheque handling
v0.3, added beangulp support
"""
__copyright__ = "Copyright (C) 2020-2025  Prabu Anand K"
__license__ = "GNU GPLv3"
__Version__ = "0.3"

import os
import re
from beancount.core import data, amount, account, position
from beancount.core.number import D
from beangulp.importers.csvbase import Importer, Date, Amount, Column

class KGIImporter(Importer):
    """An importer for KGI CSV files."""

    FLAG = '*'

    symbol = Column("Symbol")
    date = Date("TransactionDate", frmt="%Y-%m-%d")
    transaction_type = Column("TransactionType")
    quantity = Amount("Quantity")
    price = Amount("Price")
    value = Amount("Value")
    commission = Amount("Commission")
    withholding_tax = Amount("Tax")
    amount = Amount("Amount")

    def __init__(self, currency, account_root, account_cash, account_dividends,
                 account_gains, account_fees, account_withholdingtax, account_interest, account_external, account_fxdividend):
        super().__init__(account_root, currency)
        self.currency = currency
        self.account_root = account_root
        self.account_cash = account_cash
        self.account_dividends = account_dividends
        self.account_gains = account_gains
        self.account_fees = account_fees
        self.account_external = account_external
        self.account_fxdividend = account_fxdividend
        self.account_withholdingtax = account_withholdingtax
        self.account_interest = account_interest


    def identify(self, filepath):
        """Identify if this is a KGI CSV file."""
        if not filepath.endswith('.csv'):
            return False
        filename = os.path.basename(filepath)
        match = re.match(r"1kgi\d{6,8}\.csv", filename)
        return match

    def extract(self, filepath, existing):
        entries = []

        for index, row in enumerate(self.read(filepath)):
            meta = data.new_metadata(filepath, index)

            try:
                desc = f"{row.transaction_type} {row.symbol}"
                fees = amount.Amount(D(str(row.commission)), self.currency)
                account_withholdingtax = self.account_withholdingtax.format(row.symbol)


                if row.transaction_type == 'Dividend':

                    account_dividends = self.account_dividends.format(row.symbol)
                    withholding_tax = amount.Amount(D(str(row.withholding_tax)), self.currency)
                    dividend = amount.Amount(D(str(row.value)), self.currency)
                    f_amount = amount.Amount(D(str(row.amount)), self.currency)

                    txn = data.Transaction(
                        meta=meta,
                        date=row.date,
                        flag=self.FLAG,
                        payee=None,
                        narration=desc,
                        tags=data.EMPTY_SET,
                        links=data.EMPTY_SET,
                        postings=[
                            data.Posting(account_dividends, -dividend, None, None, None, None),
                            data.Posting(account_withholdingtax, withholding_tax, None, None, None, None),
                            data.Posting(self.account_fees, fees, None, None, None, None),
                            data.Posting(self.account_external, f_amount, None, None, None, None),
                        ])
                    entries.append(txn)

                elif row.transaction_type == 'Interest':
                    dividend = amount.Amount(D(str(row.value)), self.currency)
                    f_amount = amount.Amount(D(str(row.amount)), self.currency)
                    withholding_tax = amount.Amount(D(str(row.withholding_tax)), self.currency)
                    txn = data.Transaction(
                        meta=meta,
                        date=row.date,
                        flag=self.FLAG,
                        payee=None,
                        narration=desc,
                        tags=data.EMPTY_SET,
                        links=data.EMPTY_SET,
                        postings=[
                            data.Posting(self.account_interest, -dividend, None, None, None, None),
                            data.Posting(account_withholdingtax, withholding_tax, None, None, None, None),
                            data.Posting(self.account_cash, f_amount, None, None, None, None),
                        ])
                    entries.append(txn)

                elif row.transaction_type in ('BUY', 'SELL'):
                    total_amount = D(str(row.quantity)) * D(str(row.price))
                    account_inst = account.join(self.account_root, row.symbol)
                    units_inst = amount.Amount(D(str(row.quantity)), row.symbol)

                    if row.transaction_type == 'BUY':
                        cost = position.Cost(D(str(row.price)), self.currency, None, None)
                        b_value = amount.Amount(total_amount + D(str(row.commission)), self.currency)

                        txn = data.Transaction(
                            meta=meta,
                            date=row.date,
                            flag=self.FLAG,
                            payee=None,
                            narration=desc,
                            tags=data.EMPTY_SET,
                            links=data.EMPTY_SET,
                            postings=[
                                data.Posting(self.account_cash, -b_value, None, None, None, None),
                                data.Posting(self.account_fees, fees, None, None, None, None),
                                data.Posting(account_inst, units_inst, cost, None, None, None),
                            ])

                    elif row.transaction_type == 'SELL':
                        s_value = amount.Amount(total_amount - D(str(row.commission)), self.currency)
                        price = amount.Amount(D(str(row.price)), self.currency)
                        account_gains = self.account_gains.format(row.symbol)

                        txn = data.Transaction(
                            meta=meta,
                            date=row.date,
                            flag=self.FLAG,
                            payee=None,
                            narration=desc,
                            tags=data.EMPTY_SET,
                            links=data.EMPTY_SET,
                            postings=[
                                data.Posting(self.account_cash, s_value, None, None, None, None),
                                data.Posting(self.account_fees, fees, None, None, None, None),
                                data.Posting(account_inst, -units_inst, None, price, None, None),
                                data.Posting(account_gains, None, None, None, None, None),
                            ])

                    entries.append(txn)

            except (AttributeError, ValueError) as e:
                print(f"Error processing row {index}: {e}")
                continue

        return entries

    def account(self, filepath):
        """Return account associated with this importer."""
        return self.account_root
