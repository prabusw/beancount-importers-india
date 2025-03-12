#!/usr/bin/env python3
"""
v0.1 Based on https://raw.githubusercontent.com/beancount/beangulp/refs/heads/master/examples/import.py
v0.2 updated all the importers to beangulp format
"""
__copyright__ = "Copyright (C) 2025  Prabu Anand K"
__license__ = "GNU GPLv3"
__Version__ = "0.2"


# importers located in the importers directory
from importers.icici import icici
from importers.sbi import sbi
from importers.iob import iob
from importers.etrade import etrade
from importers.zerodha import zerodha
from importers.kgi import kgi
from importers.kvb import kvb
from beancount.core import data
# from hoostus.beangulp.hooks import predict_posting
from smart_importer import apply_hooks, PredictPayees, PredictPostings
import beangulp

smart_icici = icici.IciciBankImporter("Assets:IN:ICICIBank:Prabu","XXXXXXXXXXX")
apply_hooks(smart_icici, [PredictPostings(), PredictPayees()])

importers = [
    smart_icici,
    # icici.IciciBankImporter("Assets:IN:ICICIBank:Prabu","XXXXXXXXXXX"),
    sbi.SBIImporter("Assets:IN:SBI:Savings","XXXXXXXXXXX"),
    kvb.KVBImporter("Assets:IN:KVB:Savings","XXXXXXXXXXXXXXX"),
    iob.IOBImporter("Assets:IN:IOB:Savings:Prabu","3286"),
    etrade.ETradeImporter("USD",
                        "Assets:US:ETrade",
                        "Assets:US:ETrade:Cash",
                        "Income:US:ETrade:{}:Dividend",
                        "Income:US:ETrade:{}:PnL",
                        "Expenses:Financial:Fees:ETrade",
                        "Expenses:US:WithholdingTax:{}",
                        "Income:US:Interest:ETrade"),
    zerodha.ZerodhaImporter("INR",
                            "Assets:IN:Zerodha",
                            "Assets:IN:Zerodha:Cash",
                            "Income:IN:Zerodha:{}:Dividend",
                            "Income:IN:Zerodha:{}:PnL",
                            "Expenses:Financial:Fees:Zerodha",
                            "Assets:IN:ICICIBank:Savings"),
    kgi.KGIImporter("THB",
                    "Assets:TH:Investment:KGI",
                    "Assets:TH:Investment:KGI:Cash",
                    "Income:TH:Investment:{}:Dividend",
                    "Income:TH:Investment:{}:PnL",
                    "Expenses:Financial:Fees:KGI",
                    "Expenses:TH:WithholdingTax:{}",
                    "Income:TH:Interest:KGI",
                    "Assets:TH:Investment:KGI:Cash",
                    "Assets:SG:Investment:DBS:Savings:Prabu",
                    ),
]

def clean_up_descriptions(extracted_entries):
    """Example filter function; clean up cruft from narrations.

    Args:
      extracted_entries: A list of directives.
    Returns:
      A new list of directives with possibly modified payees and narration
      fields.
    """
    clean_entries = []
    for entry in extracted_entries:
        if isinstance(entry, data.Transaction):
            if entry.narration and " / " in entry.narration:
                left_part, _ = entry.narration.split(" / ")
                entry = entry._replace(narration=left_part)
            if entry.payee and " / " in entry.payee:
                left_part, _ = entry.payee.split(" / ")
                entry = entry._replace(payee=left_part)
        clean_entries.append(entry)
    return clean_entries


def process_extracted_entries(extracted_entries_list, ledger_entries):
    """Example filter function; clean up cruft from narrations.

    Args:
      extracted_entries_list: A list of (filename, entries) pairs, where
        'entries' are the directives extract from 'filename'.
      ledger_entries: If provided, a list of directives from the existing
        ledger of the user. This is non-None if the user provided their
        ledger file as an option.
    Returns:
      A possibly different version of extracted_entries_list, a list of
      (filename, entries), to be printed.
    """
    return [(filename, clean_up_descriptions(entries), account, importer)
            for filename, entries, account, importer in extracted_entries_list]

# hooks = [predict_posting.simple_hook]
hooks = [process_extracted_entries,]
if __name__ == '__main__':
    ingest = beangulp.Ingest(importers, hooks)
    ingest()
