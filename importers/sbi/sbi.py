"""Importer for SBI, India.
This script is heavily based on the script importers-chase.py  by Matt Terwilliger.
Original script can be found here https://gist.github.com/mterwill/7fdcc573dc1aa158648aacd4e33786e8
v0.2 - made changes to automatically recognize credit and Debit transactions by changing sign based on importers-schwab.py script
v0.3 - modified to support beangulp
v0.4 - Use the script tsv2csv.sh script to convert tsv(appears with extension xls when downloaded) to csv
"""
__copyright__ = "Copyright (C) 2025  Prabu Anand K"
__license__ = "GNU GPLv3"
__Version__ = "0.4"

import re
from beangulp.importers.csvbase import Importer, Date, Amount, Column

class CleanAmount(Amount):
    def parse(self, value):
        if value:
            cleaned = value.replace(',', '')
            return super().parse(cleaned)
        return 0  # Or any other default handling for empty values

class SBIImporter(Importer):
    """An importer for SBI Bank xls file downloaded and converted to csv by tsv2csv.sh script in tools folder"""
    skiplines = 20  # Skip the first 20 lines for savings, 18 for PPF before reading the header
    date = Date("Value Date", frmt="%d %b %Y")
    narration = Column("Description")
    withdrawal = CleanAmount("Debit")
    deposit = CleanAmount("Credit")

    def __init__(self, account, account_number, currency="INR"):
        super().__init__(account, currency)
        self.account_root = account
        self.account_number=account_number

    def identify(self, filepath):
        if not filepath.lower().endswith('.csv'):
            return False
        account_number_pattern = r'Account Number\s*:\s*,?\s*_?(\d+)'
        with open(filepath, 'r') as file:
        # Only check first 20 lines for account number
              for _ in range(18):
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
            if len(row) < 7 or not row[1]:  # assuming the 3rd column is the date
                continue
            # Compute the amount: negative for withdrawal, positive for deposit
            if row.withdrawal != 0:
                row.amount = -row.withdrawal  # Negative for withdrawals
            elif row.deposit != 0:
                row.amount = row.deposit  # Positive for deposits
            else:
                row.amount = 0  # Zero for zero-value transactions
            yield row
