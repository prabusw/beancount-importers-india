"""Zerodha XML Contract Note importer for Beancount v3 using beangulp."""
# import decimal
import xml.etree.ElementTree as et
from beancount.core import data, amount, account,position
from beancount.core.number import D
from beangulp.importers.base import Importer


class ZerodhaXMLImporter(Importer):
    """An importer for Zerodha XML contract notes."""

    def __init__(self, currency, account_root, account_cash, account_dividends, account_gains, account_fees, account_bank):
        super().__init__(account_root, currency)
        self.account_cash = account_cash
        self.account_dividends = account_dividends
        self.account_gains = account_gains
        self.account_fees = account_fees
        self.account_bank = account_bank

    def identify(self, filepath):
        """Identify if the file is a Zerodha XML file."""
        return filepath.endswith('.xml') and "RP0289" in filepath

    def extract(self, filepath, existing_entries=None):
        """Extract entries from Zerodha XML contract notes."""
        entries = []

        tree = et.parse(filepath)
        root = tree.getroot()

        # Parse trades and transactions
        for contract in root.findall("contracts/contract"):
            date = contract.find('timestamp').text

            trades = []
            for trade in contract.findall('trades/trade'):
                instrument = trade.attrib['instrument_id']
                trade_type = trade.find('type').text
                quantity = D(trade.find('quantity').text)
                price = D(trade.find('average_price').text)
                trades.append((instrument, trade_type, quantity, price))

            # Find net total for the contract
            net_total = D(0)
            for total in contract.findall('totals/grandtotals/grandtotal'):
                total_type = total.find('type')
                if total_type is not None and total_type.text == 'Net':
                    net_total = D(total.find('value').text)

            # Generate Beancount entries
            meta = data.new_metadata(filepath, 0)
            postings = []
            description = "Zerodha Contract Note"

            # Cash posting
            postings.append(data.Posting(self.account_cash, amount.Amount(-net_total, self.currency), None, None, None, None))

            # Asset postings for trades
            for instrument, trade_type, quantity, price in trades:
                symbol = instrument.split(":")[-1]
                account_name = account.join(self.account_root, symbol)
                cost = None if trade_type == "sell" else position.Cost(price, self.currency, None, None)
                postings.append(
                    data.Posting(
                        account_name,
                        amount.Amount(quantity if trade_type == "buy" else -quantity, symbol),
                        cost,
                        None,
                        None,
                        None,
                    )
                )

            # Fees (not itemized in this example)
            postings.append(data.Posting(self.account_fees, None, None, None, None, None))

            txn = data.Transaction(meta, date, "*", None, description, data.EMPTY_SET, data.EMPTY_SET, postings)
            entries.append(txn)

        return entries
