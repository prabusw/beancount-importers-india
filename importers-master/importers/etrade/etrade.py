"""Importer for US Stock broker Etrade. This can be used to import transactions from transactions log provided by the broker.
This is entirely based on the Example importer utrade_csv.py written for example broker UTrade by Beancount author Martin Blais.
v2.0 converted to beangulp format
"""
__copyright__ = "Copyright (C) 2020  Prabu Anand K"
__license__ = "GNU GPLv3"
__Version__ = "0.2"

import os
import re
from beancount.core import data, amount, account, position
from beangulp.importers.csvbase import Importer, Date, Amount, Column


class ETradeImporter(Importer):
    """An importer for ETrade CSV files."""

    # Define columns based on the CSV structure
    skiplines = 3
    date = Date("TransactionDate", frmt="%m/%d/%y")
    rtype = Column("TransactionType")
    security_type = Column("SecurityType")
    narration = Column("Description", default="None given")
    symbol = Column("Symbol", default="")
    amount = Amount("Amount")
    commission = Amount("Commission")
    quantity = Amount("Quantity")
    price = Amount("Price")

    def __init__(self, currency, account_root, account_cash, account_dividends,
                 account_gains, account_fees, account_withholdingtax, account_external):
        super().__init__(account_root, currency)
        self.account_root = account_root
        self.account_cash = account_cash
        self.account_dividends = account_dividends
        self.account_gains = account_gains
        self.account_fees = account_fees
        self.account_withholdingtax = account_withholdingtax
        self.account_external = account_external

    def identify(self, filepath):
        """Identify if the file matches the expected ETrade CSV format."""
        filename = os.path.basename(filepath)
        match = re.match(r"etrade\d{6,8}\.csv", filename)
        return match

    def account(self, filepath):
        return self.account_root

    def read(self, filepath):
        """Override the read method to compute the amount."""
        for row in super().read(filepath):
              # Skip empty rows or rows missing a transaction date
            if len(row) < 6 or not row[0]:  # assuming the 1st column is the date
                continue
            print("Processed row at read method:", row)  # Debug print
            yield row


    def finalize(self, txn, row):
        """Customize transaction creation for different transaction types."""
        print(f"Processing row: {row}")  # Debug row data

        desc = f"({row.rtype}) {row.narration}"  # Combine type and description
        txn = txn._replace(narration=desc)  # Update narration in the transaction
        postings = []

        # Handle different transaction types

        if row.rtype in ("Dividend","Qualified Dividend"):
            account_dividends = self.account_dividends.format(row.symbol)
            postings = [
                data.Posting(self.account_cash, amount.Amount(row.amount, self.currency), None, None, None, None),
                data.Posting(account_dividends, -amount.Amount(row.amount, self.currency), None, None, None, None),
            ]

        elif row.rtype in ("Tax","Tax Withholding","MISC"):
            account_withholdingtax = self.account_withholdingtax.format(row.symbol)
            postings = [
                data.Posting(self.account_cash, amount.Amount(row.amount, self.currency), None, None, None, None),
                data.Posting(account_withholdingtax, -amount.Amount(row.amount, self.currency), None, None, None, None),
            ]

        elif row.rtype == "Interest":
            postings = [
                data.Posting(self.account_cash, amount.Amount(row.amount, self.currency), None, None, None, None),
                data.Posting(self.account_external, -amount.Amount(row.amount, self.currency), None, None, None, None),
            ]

        elif row.rtype in ("Wire", "Fee"):
            postings = [
                data.Posting(self.account_cash, -amount.Amount(row.amount, self.currency), None, None, None, None),
                data.Posting("Expenses:FixMe", amount.Amount(row.amount, self.currency), None, None, None, None),
            ]

        elif row.rtype in ("Bought", "Sold"):
            account_inst = account.join(self.account_root, row.symbol)
            units_inst = amount.Amount(row.quantity, row.symbol)
            cost = position.Cost(row.price, self.currency, None, None)
            if row.rtype == "Bought":
                postings = [
                    data.Posting(self.account_cash, -amount.Amount(row.amount, self.currency), None, None, None, None),
                    data.Posting(self.account_fees, amount.Amount(row.commission, self.currency), None, None, None, None),
                    data.Posting(account_inst, units_inst, cost, None, None, None),
                ]
            elif row.rtype == "Sold":
                postings = [
                    data.Posting(self.account_cash, amount.Amount(row.amount, self.currency), None, None, None, None),
                    data.Posting(self.account_fees, amount.Amount(row.commission, self.currency), None, None, None, None),
                    data.Posting(account_inst, -units_inst, cost, None, None, None),
                ]

        else:
            print(f"Skipping unknown transaction type: {row.rtype}")
            return None

        # Replace transaction postings
        txn = txn._replace(postings=postings)
        return txn


        # print(f"Processing row: {row}")  # Debug row data
        # desc = f"({row.rtype}) {row.description}"
        # units = amount.Amount(row.amount, self.currency)
        # fees = amount.Amount(row.commission, self.currency)
        # other = amount.add(units, fees)
        # instrument = row.symbol
        # rate = row.price

        # # Handle different transaction types
        # postings = []
        # if row.rtype == "Dividend":
        #     account_dividends = self.account_dividends.format(instrument)
        #     postings = [
        #         data.Posting(self.account_cash, units, None, None, None, None),
        #         data.Posting(account_dividends, -other, None, None, None, None),
        #     ]

        # elif row.rtype in ("Tax", "MISC"):
        #     account_withholdingtax = self.account_withholdingtax.format(instrument)
        #     postings = [
        #         data.Posting(self.account_cash, units, None, None, None, None),
        #         data.Posting(account_withholdingtax, -other, None, None, None, None),
        #     ]

        # elif row.rtype == "Interest":
        #     postings = [
        #         data.Posting(self.account_cash, units, None, None, None, None),
        #         data.Posting(self.account_external, -other, None, None, None, None),
        #     ]

        # elif row.rtype in ("Wire", "Fee"):
        #     postings = [
        #         data.Posting(self.account_cash, -units, None, None, None, None),
        #         data.Posting("Expenses:FixMe", other, None, None, None, None),
        #     ]

        # elif row.rtype in ("Bought", "Sold"):
        #     account_inst = account.join(self.account_root, instrument)
        #     units_inst = amount.Amount(row.quantity, instrument)
        #     if row.rtype == "Bought":
        #         cost = position.Cost(rate, self.currency, None, None)
        #         postings = [
        #             data.Posting(self.account_cash, units, None, None, None, None),
        #             data.Posting(self.account_fees, fees, None, None, None, None),
        #             data.Posting(account_inst, units_inst, cost, None, None, None),
        #         ]
        #     elif row.rtype == "Sold":
        #         cost_number = None
        #         cost = position.Cost(cost_number, self.currency, None, None)
        #         price = amount.Amount(rate, self.currency)
        #         account_gains = self.account_gains.format(instrument)
        #         postings = [
        #             data.Posting(self.account_cash, units, None, None, None, None),
        #             data.Posting(self.account_fees, fees, None, None, None, None),
        #             data.Posting(account_inst, units_inst, cost, price, None, None),
        #             data.Posting(account_gains, None, None, None, None, None),
        #         ]

        # else:
        #     # Skip unknown row types
        #     print(f"Skipping unknown row type: {row.rtype}")
        #     return None

        # # Replace the transaction with updated postings and description
        # txn = txn._replace(narration=desc, postings=postings)
        # return txn
