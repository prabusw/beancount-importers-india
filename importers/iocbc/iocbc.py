"""Beancount importer for Singapore stock broker iOCBC based on beangulp to import trades from transaction history of iocbc website.
Based on utrade_csv.py by Martin Blais.
"""
__copyright__ = "Copyright (C) 2020  Prabu Anand K"
__license__ = "GNU GPLv3"
__Version__ = "0.2"

import os
import re
from beancount.core import data, amount, account, position
from beangulp.importers.csvbase import Importer, Date, Amount, Column

class CleanAmount(Amount):
    """Amount column that handles empty values and commas gracefully."""
    def parse(self, value):
        if not value or str(value).strip() == '':
            return 0
        # Handle comma-separated numbers like "3,500" or "107,869.00"
        cleaned = str(value).replace(',', '')
        return super().parse(cleaned)

class IocbcImporter(Importer):
    """An importer for IOCBC transaction history file"""

    # Define columns based on the CSV structure
    skiplines = 1  # Skip the "Generated on..." line and header row
    date = Date("Date", frmt="%d/%m/%Y")
    account_col = Column("Account")
    symbol = Column("Code")
    name = Column("Name")
    action = Column("Action")
    quantity = CleanAmount("Quantity")
    price = CleanAmount("Price")
    amount = CleanAmount("Nett amount")  # csvbase expects 'amount' attribute
    narration = Column("Contract/Reference")

    def __init__(self, currency, account_root, account_cash, srs_account_gains, cpfis_account_gains, cdp_account_gains, account_fees):
        super().__init__(account_root, currency)
        self.account_root = account_root
        self.account_cash = account_cash
        # self.account_dividends = account_dividends
        self.srs_account_gains = srs_account_gains
        self.cpfis_account_gains = cpfis_account_gains
        self.cdp_account_gains = cdp_account_gains
        self.account_fees = account_fees

    def identify(self, filepath):
        """Identify if this is an IOCBC CSV file."""
        if not filepath.endswith('.csv'):
            return False
        filename = os.path.basename(filepath)
        match = re.match(r"iocbc\d{6,8}\.csv", filename)
        return match is not None

    def account(self, filepath):
        """Return account associated with this importer."""
        return self.account_root

    def read(self, filepath):
        """Override the read method to handle multi-line CSV records."""
        rows = list(super().read(filepath))

        # Process rows in pairs (transaction + metadata)
        for i in range(0, len(rows), 2):
            if i + 1 >= len(rows):
                break  # Skip if we don't have a complete pair

            main_row = rows[i]
            meta_row = rows[i + 1]

            # Skip if main row doesn't have essential data
            if len(main_row) < 8 or not main_row[0] or not main_row[4]:
                continue

            # Skip if not a buy/sell transaction
            if main_row[4].strip().lower() not in ['buy', 'sell']:
                continue

            # Store metadata as attributes on the main row object for later use
            # We'll access these in finalize method
            main_row._meta_account = meta_row[1] if len(meta_row) > 1 else ''
            main_row._meta_exchange = meta_row[2] if len(meta_row) > 2 else ''
            main_row._meta_security_type = meta_row[3] if len(meta_row) > 3 else ''
            main_row._meta_currency = meta_row[6] if len(meta_row) > 6 else ''

            yield main_row

    def finalize(self, txn, row):
        """Customize transaction creation for buy/sell transactions."""

        # Extract data from row - now these are already parsed by CleanAmount
        action = row.action.strip() if row.action else ""
        symbol = row.symbol.strip() if row.symbol else ""
        company_name = row.name.strip() if row.name else ""
        quantity_val = row.quantity
        price_val = row.price
        nett_amount_val = row.amount
        f_account = row.account_col

        # Extract additional metadata that we stored in the read method
        account_num = getattr(row, '_meta_account', '')
        exchange = getattr(row, '_meta_exchange', '')
        security_type = getattr(row, '_meta_security_type', '')
        transaction_currency = getattr(row, '_meta_currency', '') or self.currency

        if not action or not symbol:
            print(f"Missing essential data in row: {row}")
            return None

        desc = f"({row.action}) @{exchange} {security_type} {symbol} {company_name} Contract No:{row.narration}"  # Combine type and description
        txn = txn._replace(narration=desc)

        # Create amounts - use transaction currency if different from base currency
        units_inst = amount.Amount(quantity_val, symbol)
        # cost = position.Cost(row.price, transaction_currency, None, None)
        cost = position.Cost(row.price, self.currency, None, None)

        # Calculate fees (difference between quantity*price and nett amount)
        gross_amount = quantity_val * price_val
        fee_amount = abs(gross_amount - abs(nett_amount_val))

        # account_withholdingtax = self.account_withholdingtax.format(row.symbol)

        # Create accounts for the instrument and cash based on Account column

        if f_account == "SRS":
            # t_account_inst = self.srs_account
            srs_account_root = account.join(self.account_root,f_account)
            account_inst = account.join(srs_account_root, symbol)
            txn_account_cash = account.join(srs_account_root,"Cash")
            # srs_account_gains = account.join(self.account_gains,f_account)
            # txn_account_gains = srs_account_gains.format(row.symbol)
            txn_account_gains = self.srs_account_gains.format(row.symbol)

        elif f_account == "CPF":
            cpfis_account_root = account.join(self.account_root,"CPFIS")
            account_inst = account.join(cpfis_account_root, symbol)
            txn_account_cash = account.join(cpfis_account_root,"Cash")
            # cpfis_account_gains = account.join(self.account_gains,"CPFIS")
            txn_account_gains = self.cpfis_account_gains.format(row.symbol)
        else:
            # txn_account_cash = self.iocbc_account_cash
            iocbc_account_root = account.join(self.account_root,f_account)
            txn_account_cash = self.account_cash
            account_inst = account.join(iocbc_account_root, symbol)
            # iocbc_account_gains = account.join(self.account_gains,f_account)
            txn_account_gains = self.cdp_account_gains.format(row.symbol)


        postings = []

        trade_price = amount.Amount(row.price, self.currency)

        if action.lower() == "buy":
            # For buy transactions: cash decreases, holdings increase
            # Cost object for buys: this locks in cost basis
            cost = position.Cost(trade_price.number, self.currency, None, None)
            postings = [
                data.Posting(txn_account_cash, amount.Amount(-nett_amount_val, transaction_currency), None, None, None, None),
                data.Posting(self.account_fees, amount.Amount(fee_amount, transaction_currency), None, None, None, None),
                data.Posting(account_inst, units_inst, cost, None, None, None),
            ]

        elif action.lower() == "sell":
            # For sell transactions: cash increases, holdings decrease
            cost = position.Cost(None, None, None, None)
            postings = [
                data.Posting(txn_account_cash, amount.Amount(nett_amount_val, transaction_currency), None, None, None, None),
                data.Posting(self.account_fees, amount.Amount(fee_amount, transaction_currency), None, None, None, None),
                data.Posting(account_inst, -units_inst, cost, trade_price, None, None),
                data.Posting(txn_account_gains, None, None, None, None, None),
            ]

        else:
            print(f"Unknown action type: {action} marked with FixMe appeared in {row}")
            postings = [
                data.Posting(self.account_cash, None, None, None, None, None),
                data.Posting("Expenses:FixMe", None, None, None, None, None),
            ]

        # Replace transaction postings
        txn = txn._replace(postings=postings)
        return txn
