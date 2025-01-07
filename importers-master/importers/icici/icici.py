"""Importer for ICICI Bank, India.
This script is heavily based on the script importers-chase.py  by Matt Terwilliger.
Original script can be found here https://gist.github.com/mterwill/7fdcc573dc1aa158648aacd4e33786e8
In v0.2 made changes to automatically recognize credit and Debit transactions by changing sign based on importers-schwab.py script
In v0.3 made changes to accept the headings as found in icici statement downloads as it is.
In v0.4 in line 34, the argument existing_entries was added to def extract .Originally it was  def extract(self, f):
In v0.5 modified to support beangulp
In v0.6 modified to support downloaded file without changing date format or removing lines
"""
__copyright__ = "Copyright (C) 2020  Prabu Anand K"
__license__ = "GNU GPLv3"
__Version__ = "0.6"

import os
import csv
import re

# from titlecase import titlecase
from datetime import datetime


from beancount.core import amount
from beancount.core import data
from beancount.core import flags
from beancount.core.number import D
import beangulp

class IciciBankImporter(beangulp.Importer):
    """An importer for IciciBank CSV files (a leading Indian bank)."""

    def __init__(self, account,lastfour):
        self.account_root = account
        self.lastfour = lastfour

    def identify(self, filepath):
        return re.match('icici{}.*\.csv'.format(self.lastfour), os.path.basename(filepath))

    def account(self, filepath):
        return self.account_root

    def extract(self, filepath, existing_entries=None):
        entries = []
        with open(filepath, newline='') as f:
            reader = csv.reader(f)

            # Skip the first 12 lines
            for _ in range(12):
                next(reader)

            # Read the header
            header = next(reader)
            col_index = {name: index for index, name in enumerate(header)}

            # Process each transaction row
            for row in reader:
                # Skip empty rows
                if not row:
                    continue

                # # Skip empty or invalid rows
                # if not row or row[col_index["S No."]].strip() == "":
                #     continue

                # Ensure the row has at least the required number of columns
                if len(row) <= max(col_index.values()):
                    continue  # Skip rows with insufficient columns

                # Skip empty rows or rows missing a transaction date
                transaction_date_str = row[col_index["Value Date"]].strip()
                if not row or not transaction_date_str:
                    continue  # Skip non-transactional or empty rows
                try:
                    # Parse transaction date
                    txn_date = datetime.strptime(transaction_date_str, "%d/%m/%Y").date()
                except ValueError:
                    continue  # Skip rows with invalid date formats

                # Determine narration and amount
                narration = row[col_index["Transaction Remarks"]]

                # Determine transaction amount (debit/credit)
                withdrawal = row[col_index["Withdrawal Amount (INR )"]].strip()
                deposit = row[col_index["Deposit Amount (INR )"]].strip()

                if withdrawal and float(withdrawal) != 0.0:
                    trans_amt = float(withdrawal) * -1.0  # Negative for withdrawals
                elif deposit and float(deposit) != 0.0:
                    trans_amt = float(deposit)  # Positive for deposits
                else:
                    continue  # Skip zero-value transactions

                # Format the amount to two decimal places
                trans_amt = '{:.2f}'.format(trans_amt)
                txn_amount = amount.Amount(D(trans_amt), "INR")

                # Create a Beancount transaction
                meta = data.new_metadata(filepath, len(entries) + 1)
                txn = data.Transaction(
                    meta=meta,
                    date=txn_date,
                    flag=flags.FLAG_OKAY,
                    payee="",
                    narration=narration,
                    tags=data.EMPTY_SET,
                    links=data.EMPTY_SET,
                    postings=[
                        data.Posting(
                            account=self.account_root,
                            units=txn_amount,
                            cost=None,
                            price=None,
                            flag=None,
                            meta={}
                        )
                    ],
                )
                entries.append(txn)

        return entries

if __name__ == '__main__':
    importer = IciciBankImporter(
        "Assets:IciciBank:Prabu","1585")
    main(Importer)
