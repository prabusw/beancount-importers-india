"""Importer for KVB, India.
This script is based on the script importers-chase.py by Matt Terwilliger.
"""
__copyright__ = "Copyright (C) 2020-2025  Prabu Anand K"
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

class KVBImporter(Importer):
    """An importer for KVB files downloaded in csv format from internet banking."""
    skiplines = 13  # Skip the first 12 lines for savings before reading the header
    date = Date("Value Date", frmt="%d-%m-%Y")
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
        account_number_pattern = r'Account Number:,="(\d{16})"'
        with open(filepath, 'r') as file:
        # Only check first 20 lines for account number
              for _ in range(9):
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
