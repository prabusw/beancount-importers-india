
"""Importer for ICICI Bank, India to be used with Beancount v3 using
beangulp csvbase class

Based on importer-chase.py from https://gist.github.com/mterwill

This script supports xls formatted statement with the headings as it
is. The identification relies on the account number found inside the
file. Only external tool required is xls2csv from catdoc package.

"""
__copyright__ = "Copyright (C) 2025  Prabu Anand K"
__license__ = "GNU GPLv3"
__Version__ = "0.9"

import re
from beangulp.importers.csvbase import Importer, Date, Amount, Column

class CleanColumn(Column):
    def parse(self, value):
        # Strip whitespace first
        v = value.strip()
        # Replace "-" with empty string
        if v == "-":
            return " " #Can be None
        return v

class IciciBankImporter(Importer):
    """An importer for ICICI Bank CSV files."""
    skiplines = 12  # Skip the first 12 lines before reading the header
    date = Date("Value Date", frmt="%d/%m/%Y")
    # payee = CleanColumn('Cheque Number')
    narration = Column("Transaction Remarks")
    withdrawal = Amount("Withdrawal Amount(INR)")
    deposit = Amount("Deposit Amount(INR)")
    # balance = Amount("Balance (INR )")

    def __init__(self, account, account_number, currency="INR", flag='*'):
        super().__init__(account, currency)
        self.account_root = account
        self.account_number = account_number
    def identify(self, filepath):
        if not filepath.lower().endswith('.csv'):
            return False
        account_number_pattern = r'(\d{12})\s*\(.*\)\s*-.*'

        with open(filepath, 'r') as file:
        # Only check first 12 lines for account number
              for _ in range(12):
                try:
                    row = next(file)
                    match = re.search(account_number_pattern, row)
                    if match and int(match.group(1)) == int(self.account_number):
                        return True
                except StopIteration:
                    break
        return False

    def account(self, filepath):
        return self.account_root

    def read(self, filepath):
        """Override the read method to compute the amount."""
        for row in super().read(filepath):
            # Skip empty rows or rows missing a transaction date
            if len(row) < 10 or not row[2]:  # assuming the 3rd column is the date
                continue
            # Compute the amount: negative for withdrawal, positive for deposit
            if row.withdrawal != 0:
                row.amount = -row.withdrawal  # Negative for withdrawals
            elif row.deposit != 0:
                row.amount = row.deposit  # Positive for deposits
            else:
                row.amount = 0  # Zero for zero-value transactions
            # print("Processed row:", row)  # Debug print
            yield row

# if __name__ == '__main__':
#     importer = IciciBankImporter(
#         "Assets:IciciBank:Prabu","1585")
#     main(Importer)
