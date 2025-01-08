"""Importer for Google sheets maintained by Aniruth
In v0.1 Based on icici Importer
"""
__copyright__ = "Copyright (C) 2025  Prabu Anand K"
__license__ = "GNU GPLv3"
__Version__ = "0.1"

import os
import re
from beangulp.importers.csvbase import Importer, Date, Amount, Column

class AniruthPurseImporter(Importer):
    """An importer for Aniruth Purse a google sheets based CSV file."""
    skiplines = 0  # Number of garbage lines before header
    names = True   # Ensure header is read for column mapping
    date = Date("Date", frmt="%Y-%m-%d")
    narration = Column("Description",default="Unknown Transaction")
    amount = Amount("(Income) / Expense")
    # balance = Amount("Balance (INR )")

    def __init__(self, account, currency="INR"):
        super().__init__(account, currency)
        self.account_root = account

    def identify(self, filepath):
        # Skip non-CSV files based on extension
        return filepath.lower().endswith('.csv')
        # if not filepath.lower().endswith('.csv'):
            # return False

    def account(self, filepath):
        return self.account_root

    def read(self, filepath):
        """Override the read method to skip rows with empty dates or amounts."""
        for row in super().read(filepath):
            # Check if the date field is empty
            if not row[0].strip():  # Assuming the date is in the first column
                print("Skipping row with empty date:", row)
                continue

            # Check if the amount field is empty
            if not row[2].strip():  # Assuming the amount is in the third column
                print("Skipping row with empty amount:", row)
                continue

            yield row

# if __name__ == '__main__':
#     importer = AniruthPurseImporter(
#         "Assets:Household:Cash:Aniruth")
#     main(Importer)
