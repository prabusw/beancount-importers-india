"""Importer for US Stock broker Etrade to import transactions.
This is based on the Example importer utrade_csv.py by Martin Blais.
"""
__copyright__ = "Copyright (C) 2020  Prabu Anand K"
__license__ = "GNU GPLv3"
__Version__ = "0.4"

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
        # print(f"Processing file: {filepath}")
        # with open(filepath, 'r') as file:
        #     for line_num, line in enumerate(file, start=1):
        #         # print(f"Line {line_num}: {line.strip()}")
        #         continue
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
            # print("Processed row at read method:", row)  # Debug print
            yield row

    def finalize(self, txn, row):
        """Customize transaction creation for different transaction types."""
        # print(f"Processing row: {row}")  # Debug row data
        if len(row) != 9:
            print(f"Error: Row length {len(row)} (expected 9): {row}")

        desc = f"({row.rtype}) {row.narration}"  # Combine type and description
        txn = txn._replace(narration=desc)  # Update narration in the transaction
        postings = []

        # Handle different transaction types

        if row.amount == 0:
            postings = [
                data.Posting(self.account_cash, None,None, None, None, None),
                data.Posting("Expenses:FixMe", None,None, None, None, None),
            ]

        elif row.rtype in ("Dividend","Qualified Dividend") and row.amount != 0:
            account_dividends = self.account_dividends.format(row.symbol)
            postings = [
                data.Posting(self.account_cash, amount.Amount(row.amount, self.currency), None, None, None, None),
                data.Posting(account_dividends, None, None, None, None, None),
            ]

        elif row.rtype in ("Tax","Tax Withholding"):
            account_withholdingtax = self.account_withholdingtax.format(row.symbol)
            postings = [
                data.Posting(self.account_cash, amount.Amount(row.amount, self.currency), None, None, None, None),
                data.Posting(account_withholdingtax, None, None, None, None, None),
            ]

        elif row.rtype in ("Interest","Interest Income"):
            postings = [
                data.Posting(self.account_cash, amount.Amount(row.amount, self.currency), None, None, None, None),
                data.Posting(self.account_external, None, None, None, None, None),
            ]

        elif row.rtype in ("Fee","MISC"):
            postings = [
                data.Posting(self.account_cash, -amount.Amount(row.amount, self.currency), None, None, None, None),
                data.Posting(self.account_fees, None, None, None, None, None),
            ]
        elif row.rtype in  ("Wire","Wire out","Wire In"):
            postings = [
                data.Posting(self.account_cash, -amount.Amount(row.amount, self.currency), None, None, None, None),
            ]

        elif row.rtype in ("Bought", "Sold"):
            account_inst = account.join(self.account_root, row.symbol)
            units_inst = amount.Amount(row.quantity, row.symbol)
            cost = position.Cost(row.price, self.currency, None, None)
            if row.rtype == "Bought":
                postings = [
                    data.Posting(self.account_cash, amount.Amount(row.amount, self.currency), None, None, None, None),
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
            print(f"Unknown transaction type {row.rtype} marked with FixMe appeared in {row}")
            postings = [
                data.Posting(self.account_cash, -amount.Amount(row.amount, self.currency), None, None, None, None),
                data.Posting("Expenses:FixMe", None, None, None, None, None),
            ]
            # return None

        # Replace transaction postings
        txn = txn._replace(postings=postings)
        return txn
