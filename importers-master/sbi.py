"""Importer for SBI, India.
This script is heavily based on the script importers-chase.py  by Matt Terwilliger. 
Original script can be found here https://gist.github.com/mterwill/7fdcc573dc1aa158648aacd4e33786e8
"""
__copyright__ = "Copyright (C) 2020  Prabu Anand K"
__license__ = "GNU GPLv3"
__Version__ = "0.1"

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


class SBIImporter(importer.ImporterProtocol):
    def __init__(self, account, lastfour):
        self.account = account
        self.lastfour = lastfour
    def identify(self, f):
        return re.match('sbi{}.*\.csv'.format(self.lastfour), os.path.basename(f.name))
    
    def extract(self, f):
        entries = []

        with open(f.name) as f:
            for index, row in enumerate(csv.DictReader(f)):
                trans_date = parse(row['Posting Date']).date()
                trans_desc = titlecase(row['Description'])
                trans_amt  = row['Amount']
                meta = data.new_metadata(f.name, index)

                txn = data.Transaction(
                    meta=meta,
                    date=trans_date,
                    flag=flags.FLAG_OKAY,
                    payee=trans_desc,
                    narration="",
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
