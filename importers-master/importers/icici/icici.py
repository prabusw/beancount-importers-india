"""Importer for ICICI Bank, India.
This script is heavily based on the script importers-chase.py  by Matt Terwilliger.
Original script can be found here https://gist.github.com/mterwill/7fdcc573dc1aa158648aacd4e33786e8
In v0.2 made changes to automatically recognize credit and Debit transactions by changing sign based on importers-schwab.py script
In v0.3 made changes to accept the headings as found in icici statement downloads as it is.
In v0.4 in line 34, the argument existing_entries was added to def extract .Originally it was  def extract(self, f):
In v0.5 modified to support beangulp
In v0.6 modified to support downloaded file without changing date format or removing lines
In v0.7 used the functionality from csvbase class
"""
__copyright__ = "Copyright (C) 2020  Prabu Anand K"
__license__ = "GNU GPLv3"
__Version__ = "0.7"

import os
import re
from beangulp.importers.csvbase import Importer, Date, Amount, Column
from beancount.core import data

class IciciBankImporter(Importer):
    """An importer for ICICI Bank CSV files."""
    skiplines = 12  # Skip the first 12 lines before reading the header
    date = Date("Transaction Date", frmt="%d/%m/%Y")
    narration = Column("Transaction Remarks")
    withdrawal = Amount("Withdrawal Amount (INR )")
    deposit = Amount("Deposit Amount (INR )")
    # balance = Amount("Balance (INR )")

    # @property
    # def amount(self):
    #     """Computed column to combine withdrawal and deposit into a single amount."""
    #     return Column("Withdrawal Amount (INR )", "Deposit Amount (INR )", default=0)

    def __init__(self, account, lastfour, currency="INR"):
        super().__init__(account, currency)
        self.account_root = account
        self.lastfour = lastfour

    def identify(self, filepath):
        return re.match('icici{}.*\.csv'.format(self.lastfour), os.path.basename(filepath))

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

    # def finalize(self, txn, row):
    #     """Compute the amount from withdrawal and deposit and update the posting."""

    #     # Compute amount based on withdrawal or deposit
    #     if row.withdrawal != 0:
    #         amount_value = -row.withdrawal  # Negative for withdrawals
    #     elif row.deposit != 0:
    #         amount_value = row.deposit  # Positive for deposits
    #     else:
    #         return None  # Skip zero-value transactions

    #     # Create a new posting with the computed amount
    #     new_posting = data.Posting(
    #         account=txn.postings[0].account,
    #         units=data.Amount(amount_value, self.currency),
    #         cost=None,
    #         price=None,
    #         flag=None,
    #         meta=None
    #     )

    #     # Replace the existing posting with the new one
    #     txn = txn._replace(postings=[new_posting])

    #     return txn

if __name__ == '__main__':
    importer = IciciBankImporter(
        "Assets:IciciBank:Prabu","1585")
    main(Importer)
