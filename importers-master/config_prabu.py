"""Import configuration file for Zerodha, an Indian stock broker and  ICICI Bank, a bank in India .

This script is heavily based on the script config.py  by Matt Terwilliger. 

Original script can be found here https://gist.github.com/mterwill/7fdcc573dc1aa158648aacd4e33786e8

Added SBI, RKSV and ETrade in V0.2

Added KGI in V0.3

Made further changes to KGI in V0.4 to handle dividends

Added iOCBC handling in V0.5

Added IOB in V0.6

Made changes to reflect the change in account name convention from
*:Dividend:stock to *:stock:Dividend and removed the word Investment
and replaced it by broker name wherever applicable in V0.7

Added smart_importer and related hook for icici and kvb importer in V0.8

"""
__copyright__ = "Copyright (C) 2020  Prabu Anand K"
__license__ = "GNU GPLv3"
__Version__ = "0.8"

import os,sys,logging

# beancount doesn't run from this directory
sys.path.append(os.path.dirname(__file__))

# importers located in the importers directory
from importers.icici import icici
from importers.sbi import sbi
from importers.zerodha import zerodha
from importers.rksv import rksv
from importers.etrade import etrade
from importers.kgi import kgi
from importers.iocbc import iocbc
from importers.iob import iob
from importers.kvb import kvb
from smart_importer import apply_hooks, PredictPayees, PredictPostings
logging.getLogger('smart_importer').setLevel(logging.DEBUG)

# The 7875 can be the last four character of your ICICI savings account. By suitably changing you can import from any ICICI account.
# All the six accounts i.e Assets:IN:Investment:ILFSSS etc must be declared already in your my.beancount file, to make use of this.
#
icici_importer = icici.IciciBankImporter('Assets:IN:ICICIBank:Savings', '1585')
apply_hooks(icici_importer, [PredictPostings(), PredictPayees()])

kvb_importer = kvb.KVBImporter('Assets:IN:KVB:Savings', '0880')
apply_hooks(kvb_importer, [PredictPostings(), PredictPayees()])

# sbi_importer = sbi.SBIImporter('Assets:IN:SBI:Savings', '8819')
# apply_hooks(sbi_importer, [PredictPostings(), PredictPayees()])


CONFIG = [
    # icici.IciciBankImporter('Assets:IN:ICICIBank:Savings', '1585'),
    icici_importer,
    sbi.SBIImporter('Assets:IN:SBI:Savings', '8819'),
    # sbi_importer,
    iob.IOBImporter('Assets:IN:IOB:Savings:Aniruth', '3319'),
    iob.IOBImporter('Assets:IN:IOB:Savings:Aadhirai', '3320'),
    iob.IOBImporter('Assets:IN:IOB:Savings:Prabu', '3286'),
    #kvb.KVBImporter('Assets:IN:KVB:Savings', '0880'),
    kvb_importer,

    
    zerodha.ZerodhaImporter("INR",
                        "Assets:IN:Zerodha",
                        "Assets:IN:Zerodha:Cash",
                        "Income:IN:Zerodha:{}:Dividend",
                        "Income:IN:Zerodha:{}:PnL",
                        "Expenses:Financial:Fees:Zerodha",
                        "Assets:IN:ICICIBank:Savings"),

    rksv.RKSVImporter("INR",
                        "Assets:IN:RKSV",
                        "Assets:IN:RKSV:Cash",
                        "Income:IN:RKSV:{}:Dividend",
                        "Income:IN:RKSV:{}:PnL",
                        "Expenses:Financial:Fees:RKSV",
                        "Assets:IN:ICICIBank:Savings"),

    etrade.ETradeImporter("USD",
                        "Assets:US:ETrade",
                        "Assets:US:ETrade:Cash",
                        "Income:US:ETrade:{}:Dividend",
                        "Income:US:ETrade:{}:PnL",
                        "Expenses:Financial:Fees:ETrade",
                        "Income:US:Interest:ETrade"),

    kgi.KGIImporter("THB",
                        "Assets:TH:Investment:KGI",
                        "Assets:TH:Investment:KGI:Cash",
                        "Income:TH:Investment:{}:Dividend",
                        "Income:TH:Investment:{}:PnL",
                        "Expenses:Financial:Fees:KGI",
                        "Income:TH:Interest:KGI",
                        "Expenses:Financial:Fees:TSD",
                        "Assets:SG:Investment:DBS:Savings:Prabu",
                        "Expenses:TH:WithholdingTax:{}"),
    
    iocbc.IocbcImporter("SGD",
                        "Assets:SG:IOCBC",
#Assets:SG:IOCBC:Cash
#Assets:SG:CPF:CPFIS:Cash
#Assets:SG:SRS:Cash                             
                        "Assets:SG:IOCBC:Cash",
                        "Income:SG:IOCBC:CPFIS:{}:Dividend",
                        "Income:SG:IOCBC:PnL:{}",
                        "Expenses:Financial:Fees:IOCBC",
                        "Income:SG:Interest:IOCBC",
                        "Assets:SG:Investment:CPF:CPFIS:Cash"),
#Assets:SG:CPF:CPFIS:Cash
#Assets:SG:SRS:Cash
#Assets:SG:DBS:Savings:Prabu    
]

