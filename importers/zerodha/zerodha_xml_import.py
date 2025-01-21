# Zerodha contract note processing:
# Contract note downaloded from here: https://console.zerodha.com/reports/downloads
# Very first version, need improvement

import sys
import decimal
import xml.etree.ElementTree as et

if len(sys.argv) < 1:
    print('zerodha-import <xml-file>')
    sys.exit(-1)

zerodha_file = sys.argv[-1]
if not zerodha_file.endswith('.xml'):
    print('zerodha-import <xml-file>')
    sys.exit(-1)


tree = et.parse(zerodha_file)
root = tree.getroot()

trxs = []
for contract in root.findall("contracts/contract"):
    date = contract.find('timestamp').text

    trades = []
    for trade in contract.findall('trades/trade'):
        instrument = trade.attrib['instrument_id']
        type = trade.find('type').text
        quantity = trade.find('quantity').text
        price = decimal.Decimal(trade.find('average_price').text)
        total_price = trade.find('value').text
        trades += [(instrument, type, quantity, price)]

    nettotal = 0
    for total in contract.findall('totals/grandtotals/grandtotal'):
        type = total.find('type')
        if type is not None and type.text == 'Net':
            value = total.find('value').text
            nettotal = decimal.Decimal(value)

    trxs += [(date, trades, nettotal)]

cash_account = 'Assets:Zerodha:Cash'
asset_account_prefix = 'Assets:Zerodha:EQ'
fees_acount = 'Expenses:Zerodha:Fees'

for trx in trxs:
    date, trades, nettotal = trx
    comment = "Trading "
    tradelines = ""
    for trade in trades:
        instrument, type, quantity, price = trade
        instrument = instrument.split(':')[-1]
        comment += instrument + ", "
        tradelines += "\n  %s:%s\t\t%s %s { %s INR }" % \
                     (asset_account_prefix, instrument, quantity, instrument, price)
    comment = comment[:-2]

    result = """%s * "Zerodha" "%s"\n  %s\t\t\t%s INR%s\n  %s\n""" % \
             (date, comment, cash_account, str(-nettotal), tradelines, fees_acount)
    print result