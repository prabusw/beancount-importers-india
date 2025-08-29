
"""Beangulp based beancount importer for Indian Stock broker Zerodha
to be used to import transactions from Tradebook provided by the
broker.  This is based utrade_csv.py by Martin Blais.
"""

__copyright__ = "Copyright (C) 2020-2025  Prabu Anand K"
__license__ = "GNU GPLv3"
__Version__ = "0.5"

import os
import re
from beancount.core import data, amount, account, position
from beancount.core.number import D
from beangulp.importers.csvbase import Importer, Date, Amount, Column

class ZerodhaImporter(Importer):
    """An importer for Zerodha CSV files."""

    # Define columns based on the current CSV structure
    symbol = Column("symbol")
    date = Date("trade_date", frmt="%Y-%m-%d")
    exchange = Column("exchange")
    segment = Column("segment")
    transaction_type = Column("trade_type")
    quantity = Amount("quantity")
    price = Amount("price")
    amount = Amount("price")
    trade_id = Column("trade_id")
    order_id = Column("order_id")
    narration = Column("trade_id")
    # isin = Column("isin")
    # series = Column("series")
    # auction = Column("auction")
    # execution_time = Column("order_execution_time")

    def __init__(self, currency, account_root, account_cash, account_dividends,
                 account_gains, account_fees, account_external):
        super().__init__(account_root, currency)
        self.currency = currency
        self.account_root = account_root
        self.account_cash = account_cash
        self.account_dividends = account_dividends
        self.account_gains = account_gains
        self.account_fees = account_fees
        self.account_external = account_external

    # def identify(self, filepath):
    #     """Identify if this is a Zerodha CSV file."""
    #     if not filepath.endswith('.csv'):
    #         return False
    #     try:
    #         with open(filepath, 'r') as file:
    #             header = file.readline().strip()
    #             expected = "symbol,isin,trade_date,exchange,segment,series,trade_type,auction,quantity,price,trade_id,order_id,order_execution_time"
    #             return header == expected
    #     except Exception:
    #         return False

    def identify(self, filepath):
        """Identify if this is a Zerodha CSV file."""
        if not filepath.endswith('.csv'):
            return False
        filename = os.path.basename(filepath)
        match = re.match(r"zerodha\d{6,8}\.csv", filename)
        return match

    def account(self, filepath):
        """Return account associated with this importer."""
        return self.account_root

    def read(self, filepath):
        """Override the read method to handle empty rows and validate data."""
        for row in super().read(filepath):
            # print(f"processing row:{row}")
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
        # use quantize method to fix the number of decimals
        desc = f"{row.transaction_type} {row.symbol} with OrderID {row.order_id} and Trade Id {row.trade_id}"
        txn = txn._replace(narration=desc)  # Update narration in the transaction
        postings = []

        gross_cost = row.quantity * row.price
        fees = row.quantity * row.price * D(0.001)
        gross_cost = gross_cost.quantize(D('0.01'))
        fees = fees.quantize(D('0.01'))
        if row.transaction_type == 'buy':
            account_inst = account.join(self.account_root, row.symbol)
            # units_inst = amount.Amount(row.quantity, row.symbol)
            units_inst = amount.Amount(row.quantity.quantize(D('0.0001')), row.symbol)
            # Cost object for buys: this locks in cost basis
            cost = position.Cost(row.price.quantize(D('0.01')), self.currency, None, None)
            total_cost = amount.Amount(gross_cost + fees, self.currency)
            fees = amount.Amount(fees, self.currency)
            postings = [
                data.Posting(self.account_cash, -total_cost, None, None, None, None),
                data.Posting(self.account_fees, fees, None, None, None, None),
                data.Posting(account_inst, units_inst, cost, None, None, None),
            ]

        elif row.transaction_type == 'sell':
            account_inst = account.join(self.account_root, row.symbol)
            units_inst = amount.Amount(row.quantity.quantize(D('0.0001')), row.symbol)
            net_proceeds = amount.Amount(gross_cost - fees, self.currency)
            price_amount = amount.Amount(row.price.quantize(D('0.01')), self.currency)
            # Empty Cost object for sells
            cost = position.Cost(None, None, None, None)
            account_gains = self.account_gains.format(row.symbol)
            fees = amount.Amount(fees, self.currency)
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
