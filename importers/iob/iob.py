"""Importer for IOB, India.
This script is heavily based on the script importers-chase.py  by Matt Terwilliger.
Original script can be found here https://gist.github.com/mterwill/7fdcc573dc1aa158648aacd4e33786e8
v0.1 made changes to automatically recognize credit and Debit transactions by changing sign based on importers-schwab.py script
v0.2 beagulp version based on sbi importer for CleanAmount class
"""
__copyright__ = "Copyright (C) 2020-2025  Prabu Anand K"
__license__ = "GNU GPLv3"
__Version__ = "0.2"

import os
import re
from beangulp.importers.csvbase import Importer, Date, Amount, Column

class CleanAmount(Amount):
    def parse(self, value):
        if value:
            cleaned = value.replace(',', '')
            return super().parse(cleaned)
        return 0  # Or any other default handling for empty values

class IOBImporter(Importer):
    """An importer for IOB CSV files."""
    date = Date("Value Date", frmt="%d-%b-%Y")  # Note the updated date format
    narration = Column("Narration")
    withdrawal = CleanAmount("Debit")
    deposit = CleanAmount("Credit")

    def __init__(self, account_root, lastfour, currency="INR"):
        # Fix the typo in __init__ method name
        super().__init__(account_root, currency)
        self.account_root = account_root
        self.lastfour = lastfour

    def identify(self, filepath):
        """Identify if the file matches the expected IOB CSV format."""
        filename = os.path.basename(filepath)
        return re.match(r'iob{}.*\.csv'.format(self.lastfour), filename) is not None

    def account(self, filepath):
        return self.account_root

    def read(self, filepath):
        """Override the read method to compute the amount."""
        for row in super().read(filepath):
            # Skip empty rows or rows missing a transaction date
            if len(row) < 7 or not row[1]:  # assuming the 2nd column is the date
                continue
            # Compute the amount: negative for withdrawal, positive for deposit
            if row.withdrawal != 0:
                row.amount = -row.withdrawal  # Negative for withdrawals
            elif row.deposit != 0:
                row.amount = row.deposit  # Positive for deposits
            else:
                row.amount = 0  # Zero for zero-value transactions
            yield row
