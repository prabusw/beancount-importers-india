"""Importer for ICICI Bank, India.
This script is heavily based on the script importers-chase.py  by Matt Terwilliger. 
Original script can be found here https://gist.github.com/mterwill/7fdcc573dc1aa158648aacd4e33786e8
In V0.2 made changes to automatically recognize credit and Debit transactions by changing sign based on importers-schwab.py script
In V0.3 made changes to accept the headings as found in icici statement downloads as it is. 
"""
__copyright__ = "Copyright (C) 2020  Prabu Anand K"
__license__ = "GNU GPLv3"
__Version__ = "0.3"

from beancount.core.number import D
from beancount.ingest import importer
from beancount.core import account
from beancount.core import amount
from beancount.core import flags
from beancount.core import data
from beancount.core.position import Cost
from dateutil.parser import parse

from titlecase import titlecase

import csv
import os
import re


class IciciBankImporter(importer.ImporterProtocol):
    def __init__(self, account, lastfour):
        self.account = account
        self.lastfour = lastfour
    def identify(self, f):
        return re.match('icici{}.*\.csv'.format(self.lastfour), os.path.basename(f.name))
    
    def extract(self, f):
        entries = []

        with open(f.name) as f:
            for index, row in enumerate(csv.DictReader(f)):
                trans_date = parse(row['Value Date']).date()
                trans_desc = titlecase(row['Transaction Remarks'])
                #trans_amt  = row['Amount']
                
                if row['Withdrawal Amount (INR )'] != "0" :    # this is needed for ICICI. 
                    trans_amt = float(row['Withdrawal Amount (INR )']) * -1.
                elif row['Deposit Amount (INR )']:
                    #trans_amt = float(row['Credit'].strip('$'))
                    #left the above line to know about strip option 
                    trans_amt = float(row['Deposit Amount (INR )'])
                else:
                    continue # 0 value transaction

                trans_amt = '{:.2f}'.format(trans_amt)




                meta = data.new_metadata(f.name, index)

                txn = data.Transaction(
                    meta=meta,
                    date=trans_date,
                    flag=flags.FLAG_OKAY,
                    payee="",
                    narration=trans_desc,
                    tags=set(),
                    links=set(),
                    postings=[],
                )

                txn.postings.append(
                    data.Posting(self.account, amount.Amount(D(trans_amt),
                        'INR'), None, None, None, None)
                )

                entries.append(txn)

        return entries
