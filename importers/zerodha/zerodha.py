
"""Importer for leading Indian Stock broker Zerodha. This can be used to import transactions from Tradebook provided by the broker.
This is entirely based on the Example importer utrade_csv.py written for example broker UTrade by Beancount author Martin Blais.
v0.2 removes the {link} from transaction postings. link = "{0[order_id]}".format(row). It is now data.EMPTY_SET
v0.3 involves changes to reflect changes aligned to actual download of Zerodha Tradebook
v0.4 converted to beangulp format"""

__copyright__ = "Copyright (C) 2020-2025  Prabu Anand K"
__license__ = "GNU GPLv3"
__Version__ = "0.4"
import os
import re
from beancount.core import data, amount, account, position
from beancount.core.number import D
from beangulp.importers.csvbase import Importer, Date, Amount, Column

class ZerodhaImporter(Importer):
    """An importer for Zerodha CSV files."""

    # Define the FLAG attribute
    FLAG = '*'

    # Define columns based on the current CSV structure
    symbol = Column("symbol")
    date = Date("trade_date", frmt="%Y-%m-%d")
    exchange = Column("exchange")
    segment = Column("segment")
    trade_type = Column("trade_type")
    quantity = Amount("quantity")
    price = Amount("price")
    trade_id = Column("trade_id")
    order_id = Column("order_id")
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

    def extract(self, filepath, existing):
        entries = []

        for index, row in enumerate(self.read(filepath)):
            meta = data.new_metadata(filepath, index)
            # meta['trade_id'] = row.trade_id
            # meta['order_id'] = row.order_id
            # meta['exchange'] = row.exchange
            # meta['segment'] = row.segment
            # meta['execution_time'] = row.execution_time

            try:
                # Calculate amount and fees from quantity and price
                total_amount = D(str(row.quantity)) * D(str(row.price))
                fees = total_amount * D('0.001')  # 0.1% fee

                # Create the amounts needed for postings
                fee_amount = amount.Amount(fees, self.currency)
                b_value = amount.Amount(total_amount + fees, self.currency)
                s_value = amount.Amount(total_amount - fees, self.currency)

                desc = f"{row.trade_type} {row.symbol} with OrderID {row.order_id} and Trade Id {row.trade_id}"

                if row.trade_type.lower() in ('buy', 'sell'):
                    account_inst = account.join(self.account_root, row.symbol)
                    units_inst = amount.Amount(D(str(row.quantity)), row.symbol)

                    if row.trade_type.lower() == 'buy':
                        cost = position.Cost(D(str(row.price)), self.currency, None, None)
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
                                data.Posting(self.account_fees, fee_amount, None, None, None, None),
                                data.Posting(account_inst, units_inst, cost, None, None, None),
                            ])

                    elif row.trade_type.lower() == 'sell':
                        cost_number = None
                        cost = position.Cost(cost_number, self.currency, None, None)
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
                                data.Posting(self.account_fees, fee_amount, None, None, None, None),
                                data.Posting(account_inst, -units_inst, cost, price, None, None),
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
