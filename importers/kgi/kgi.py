"""Importer for Thailand Stock broker KGI. The entries are to be manually created in csv format. Based on importer utrade_csv.py Martin Blais.
"""
__copyright__ = "Copyright (C) 2020-2025  Prabu Anand K"
__license__ = "GNU GPLv3"
__Version__ = "0.4"

import os
import re
from beancount.core import data, amount, account, position
from beangulp.importers.csvbase import Importer, Date, Amount, Column

class CleanAmount(Amount):
    """Amount column that handles empty values and commas gracefully."""
    def parse(self, value):
        if not value or str(value).strip() == '':
            return 0
        # Handle comma-separated numbers like "107,869.00"
        cleaned = str(value).replace(',', '')
        return super().parse(cleaned)

class KGIImporter(Importer):
    """An importer for KGI CSV files."""

    # Define columns based on the CSV structure
    symbol = Column("Symbol")
    date = Date("TransactionDate", frmt="%d/%m/%Y")
    transaction_type = Column("TransactionType")
    quantity = CleanAmount("Quantity")
    price = CleanAmount("Price")
    value = CleanAmount("Value")
    commission = CleanAmount("Commission")
    withholding_tax = CleanAmount("Tax")
    amount = CleanAmount("Amount")
    narration = Column("Description")

    def __init__(self, currency, account_root, account_cash, account_dividends,
                 account_gains, account_fees, account_withholdingtax, account_interest,
                 account_external, account_fxdividend):
        super().__init__(account_root, currency)
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
        match = re.match(r"kgi\d{6,8}\.csv", filename)
        return match

    def account(self, filepath):
        """Return account associated with this importer."""
        return self.account_root

    def read(self, filepath):
        """Override the read method to handle empty rows and validate data."""
        for row in super().read(filepath):
            # Skip empty rows or rows missing essential data
            if not hasattr(row, 'date') or not row.date:
                print(f"Skipped row {row_num}: Missing date")
                continue
            if not hasattr(row, 'transaction_type') or not row.transaction_type:
                print(f"Skipped row {row_num}: Missing transaction type")
                continue
            yield row

    def finalize(self, txn, row):
        """Customize transaction creation for different transaction types."""
        desc = f"({row.transaction_type}) ({row.symbol}) {row.narration}"  # Combine type and description
        txn = txn._replace(narration=desc)  # Update narration in the transaction
        postings = []

        # Helper for safe amounts

        account_withholdingtax = self.account_withholdingtax.format(row.symbol)

        if row.transaction_type == 'Dividend':
            account_dividends = self.account_dividends.format(row.symbol)
            withholding_tax = amount.Amount(row.withholding_tax, self.currency)
            dividend = amount.Amount(row.value, self.currency)
            f_amount = amount.Amount(row.amount, self.currency)

            postings = [
                data.Posting(account_dividends, -f_amount, None, None, None, None),
                data.Posting(account_withholdingtax, withholding_tax, None, None, None, None),
                # data.Posting(self.account_fees, fees, None, None, None, None), #currently no fees
                data.Posting(self.account_external, None, None, None, None, None),
            ]

        elif row.transaction_type == 'Interest':
            total_interest = amount.Amount(row.amount, self.currency)
            r_interest = amount.Amount(row.value, self.currency)
            withholding_tax = amount.Amount(row.withholding_tax, self.currency)

            postings = [
                data.Posting(self.account_interest, -total_interest, None, None, None, None),
                data.Posting(account_withholdingtax, withholding_tax, None, None, None, None),
                data.Posting(self.account_cash, r_interest, None, None, None, None),
            ]

        elif row.transaction_type == 'BUY':
            fees = amount.Amount(row.commission, self.currency)
            account_inst = account.join(self.account_root, row.symbol)
            units_inst = amount.Amount(row.quantity, row.symbol)
            # Cost object for buys: this locks in cost basis
            cost = position.Cost(row.price, self.currency, None, None)
            total_cost = amount.Amount(row.quantity * row.price + row.commission, self.currency)

            postings = [
                data.Posting(self.account_cash, -total_cost, None, None, None, None),
                data.Posting(self.account_fees, fees, None, None, None, None),
                data.Posting(account_inst, units_inst, cost, None, None, None),
            ]

        elif row.transaction_type == 'SELL':
            fees = amount.Amount(row.commission, self.currency)
            account_inst = account.join(self.account_root, row.symbol)
            units_inst = amount.Amount(row.quantity, row.symbol)
            net_proceeds = amount.Amount(row.quantity * row.price - row.commission, self.currency)
            price_amount = amount.Amount(row.price, self.currency)
            cost = position.Cost(None, None, None, None)
            account_gains = self.account_gains.format(row.symbol)

            postings = [
                data.Posting(self.account_cash, net_proceeds, None, None, None, None),
                data.Posting(self.account_fees, fees, None, None, None, None),
                data.Posting(account_inst, -units_inst, cost, price_amount, None, None),
                data.Posting(account_gains, None, None, None, None, None),
            ]

        else:
            print(f"Unknown transaction type {row.transaction_type} marked with FixMe appeared in {row}")
            postings = [
                data.Posting(self.account_cash, None, None, None, None, None),
                data.Posting("Expenses:FixMe", None, None, None, None, None),
            ]

        # Replace transaction postings
        txn = txn._replace(postings=postings)
        return txn
