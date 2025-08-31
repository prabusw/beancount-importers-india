"""Beangulp based beancount importer for Indian Stock broker Zerodha
XML contract notes. This imports transactions from contract notes XML files
provided by the broker.
"""

import os
import xml.etree.ElementTree as ET
from decimal import Decimal
from enum import Enum
from datetime import datetime
from typing import Optional, Dict, List
from beancount.core import data, amount, account, position
from beancount.core.number import D
from beangulp import Importer


class TradeType(Enum):
    EQUITY_DELIVERY = "equity_delivery"
    EQUITY_INTRADAY = "equity_intraday"
    FO_FUTURES = "fo_futures"
    FO_OPTIONS = "fo_options"


class ChargePolicy:
    """Policy configuration for different trading charges based on instrument type."""

    POLICY = {
        TradeType.EQUITY_DELIVERY: {
            'brokerage': {'rate': D('0'), 'flat': D('0'), 'cap': None},
            'stt_buy': D('0.001'),
            'stt_sell': D('0.001'),
            'transaction_charges': {'NSE': D('0.0000297'), 'BSE': D('0.0000375')},
            'sebi_charges': D('0.000001'),
            'stamp_charges': D('0.00015'),
            'gst_rate': D('0.18')
        },
        TradeType.EQUITY_INTRADAY: {
            'brokerage': {'rate': D('0.0003'), 'flat': D('0'), 'cap': D('20')},
            'stt_buy': D('0'),
            'stt_sell': D('0.00025'),
            'transaction_charges': {'NSE': D('0.0000297'), 'BSE': D('0.0000375')},
            'sebi_charges': D('0.000001'),
            'stamp_charges': D('0.00003'),
            'gst_rate': D('0.18')
        },
        TradeType.FO_FUTURES: {
            'brokerage': {'rate': D('0.0003'), 'flat': D('0'), 'cap': D('20')},
            'stt_buy': D('0'),
            'stt_sell': D('0.0002'),
            'transaction_charges': {'NSE': D('0.0000173'), 'BSE': D('0')},
            'sebi_charges': D('0.000001'),
            'stamp_charges': D('0.00002'),
            'gst_rate': D('0.18')
        },
        TradeType.FO_OPTIONS: {
            'brokerage': {'rate': D('0'), 'flat': D('20'), 'cap': None},
            'stt_buy': D('0'),
            'stt_sell': D('0.001'),
            'transaction_charges': {'NSE': D('0.0003503'), 'BSE': D('0.000325')},
            'sebi_charges': D('0.000001'),
            'stamp_charges': D('0.00003'),
            'gst_rate': D('0.18')
        }
    }


class ZerodhaXMLImporter(Importer):
    """An importer for Zerodha XML contract note files."""

    def __init__(self, currency: str, account_root: str, account_cash: str,
                 account_dividends: str, account_gains: str, account_fees: str,
                 account_external: str):
        self.currency = currency
        self.account_root = account_root
        self.account_cash = account_cash
        self.account_dividends = account_dividends
        self.account_gains = account_gains
        self.account_fees = account_fees
        self.account_external = account_external
        self.demat_charge_per_sell = D("13.50")
        self.charge_policy = ChargePolicy()

    def identify(self, filepath: str) -> bool:
        if not filepath.endswith('.xml'):
            return False
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            if root.tag != 'contract_note':
                return False
            issuer_name = root.find('.//issuer/name')
            if issuer_name is not None and 'Zerodha' in issuer_name.text:
                return True
            return False
        except (ET.ParseError, FileNotFoundError, PermissionError):
            return False

    def account(self, filepath: str) -> str:
        return self.account_root

    def extract(self, filepath: str, existing_entries=None):
        entries = []
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            for contract in root.findall('.//contract'):
                entries.extend(self._process_contract(contract, filepath))
        except ET.ParseError as e:
            print(f"Error parsing XML file {filepath}: {e}")
        return entries

    # -------------------
    # Helpers
    # -------------------

    def _parse_decimal(self, val: Optional[str]) -> Decimal:
        try:
            return D(val)
        except Exception:
            return D('0')

    def _parse_date(self, val: Optional[str]):
        try:
            return datetime.strptime(val, "%Y-%m-%d").date()
        except Exception:
            return None

    def _get_text(self, elem: ET.Element, tag: str, default: str = "") -> str:
        child = elem.find(tag)
        return child.text.strip() if child is not None and child.text else default

    def _extract_symbol(self, instrument_id: str) -> str:
        if not instrument_id:
            return "UNKNOWN"
        return instrument_id.split(":")[1].split(" - ")[0]

    # -------------------
    # Charges
    # -------------------

    def _extract_contract_charges(self, contract_elem: ET.Element) -> Dict[str, Decimal]:
        """Extract charges from XML subtotals."""
        charges = {}
        for charge_elem in contract_elem.findall('.//subtotals/charges/charge'):
            name = self._get_text(charge_elem, 'name')
            val = self._parse_decimal(self._get_text(charge_elem, 'value'))
            if not name or val == 0:
                continue
            if 'PAY IN / PAY OUT OBLIGATION' in name or 'Net amount Receivable' in name:
                continue
            charges[name] = val
        return charges

    def _get_total_contract_value(self, contract_elem: ET.Element) -> Decimal:
        total = D('0')
        for trade_elem in contract_elem.findall('.//trade'):
            value = self._parse_decimal(self._get_text(trade_elem, 'value'))
            total += abs(value)
        return total

    def _allocate_contract_charges(self, contract_elem: ET.Element,
                                   order_value: Decimal) -> Dict[str, Decimal]:
        """Allocate contract-level charges proportionally to order value."""
        xml_charges = self._extract_contract_charges(contract_elem)
        total_value = self._get_total_contract_value(contract_elem)
        if total_value == 0:
            return {}
        ratio = abs(order_value) / total_value
        allocated = {name: (val * ratio).quantize(D("0.001")) for name, val in xml_charges.items()}
        return allocated


    def _calculate_charges(self, order_trades: List[Dict], trade_type: TradeType) -> Dict[str, Decimal]:
        """Policy calculation (for validation only)."""
        """Calculate charges based on policy configuration."""

        if not order_trades:
            return {}

        total_value = sum(abs(t['value']) for t in order_trades)  # Use absolute values
        total_quantity = sum(abs(t['quantity']) for t in order_trades)  # Use absolute values
        first_trade = order_trades[0]
        exchange = first_trade['exchange']
        is_buy = first_trade['type'] == 'B'

        policy = self.charge_policy.POLICY[trade_type]
        charges = {}

        # 1. Calculate Brokerage
        brokerage_config = policy['brokerage']
        if brokerage_config['flat'] > 0:
            brokerage = brokerage_config['flat']
        else:
            brokerage = total_value * brokerage_config['rate']
            if brokerage_config['cap'] and brokerage > brokerage_config['cap']:
                brokerage = brokerage_config['cap']

        charges['Brokerage'] = brokerage

        # 2. Calculate STT
        if is_buy:
            stt = total_value * policy['stt_buy']
        else:
            stt = total_value * policy['stt_sell']
        charges['Securities Transaction Tax'] = stt

        # 3. Calculate Transaction Charges
        tx_rate = policy['transaction_charges'].get(exchange, D('0'))
        tx_charges = total_value * tx_rate
        charges['Exchange Transaction Charges'] = tx_charges

        # 4. Calculate SEBI Charges
        sebi_charges = total_value * policy['sebi_charges']
        charges['SEBI Turnover Fees'] = sebi_charges

        # 5. Calculate Stamp Duty (only on buy side)
        if is_buy:
            stamp_duty = total_value * policy['stamp_charges']
            charges['Stamp Duty'] = stamp_duty

        # 6. Calculate GST (on brokerage + SEBI + transaction charges)
        gst_base = brokerage + sebi_charges + tx_charges
        gst = gst_base * policy['gst_rate']

        # For now, put all GST in IGST (you can split into CGST/SGST based on state)
        charges['Integrated GST'] = gst
        charges['Central GST'] = D('0')
        charges['State GST'] = D('0')

        # 7. Clearing Charges (usually zero for most cases)
        charges['Clearing Charges'] = D('0')


        return {}

    # -------------------
    # Processing
    # -------------------

    def _group_trades_by_order(self, contract_elem: ET.Element) -> Dict[tuple, List[Dict]]:
        orders = {}
        for trade_elem in contract_elem.findall('.//trade'):
            tr = {
                'id': self._get_text(trade_elem, 'id'),
                'order_id': self._get_text(trade_elem, 'order_id'),
                'timestamp': self._get_text(trade_elem, 'timestamp'),
                'exchange': self._get_text(trade_elem, 'exchange'),
                'type': self._get_text(trade_elem, 'type'),
                'quantity': self._parse_decimal(self._get_text(trade_elem, 'quantity')),
                'price': self._parse_decimal(self._get_text(trade_elem, 'average_price')),
                'value': self._parse_decimal(self._get_text(trade_elem, 'value')),
                'instrument_id': trade_elem.get('instrument_id', 'Unknown'),
                'segment_id': trade_elem.get('segment_id', 'Unknown'),
            }
            if not tr['quantity'] or not tr['price']:
                continue
            tr['symbol'] = self._extract_symbol(tr['instrument_id'])
            key = (tr['order_id'], tr['type'])
            orders.setdefault(key, []).append(tr)
        return orders

    def _process_contract(self, contract_elem: ET.Element, filepath: str):
        contract_id = self._get_text(contract_elem, 'id', 'Unknown')
        contract_date = self._parse_date(self._get_text(contract_elem, 'timestamp'))
        if not contract_date:
            return []
        client_name = self._get_text(contract_elem, 'client/name', 'Unknown Client')

        orders = self._group_trades_by_order(contract_elem)

        if not orders:
            return []

        entries = []
        for (order_id, ttype), order_trades in orders.items():
            txn = self._create_order_transaction(order_trades, contract_elem,
                                                 contract_date, contract_id,
                                                 client_name, filepath)
            entries.append(txn)
        return entries

    # -------------------
    # Transaction builder
    # -------------------

    # def _create_order_transaction(self, order_trades: List[Dict],
    #                               contract_elem: ET.Element,
    #                               contract_date: datetime.date,
    #                               contract_id: str,
    #                               client_name: str,
    #                               filepath: str) -> data.Transaction:

    #     total_qty = sum(abs(t['quantity']) for t in order_trades)
    #     total_val = sum(abs(t['value']) for t in order_trades)
    #     avg_price = total_val / total_qty if total_qty else D('0')

    #     first_trade = order_trades[0]
    #     symbol = first_trade['symbol']
    #     trade_type_char = first_trade['type']
    #     order_id = first_trade['order_id']
    #     instrument_id = first_trade['instrument_id']
    #     segment_id = first_trade['segment_id']

    #     # Allocate XML charges
    #     allocated_charges = self._allocate_contract_charges(contract_elem, total_val)

    #     # Validate using policy
    #     trade_type = self._detect_trade_type(instrument_id, segment_id, order_trades)
    #     policy_charges = self._calculate_charges(order_trades, trade_type)
    #     for cname, cval in allocated_charges.items():
    #         if cname in policy_charges:
    #             if abs(cval - policy_charges[cname]) > D("0.05"):
    #                 print(f"[WARN] Charge mismatch {cname} order {order_id}: XML={cval} Policy={policy_charges[cname]}")

    #     narration = f"{'Buy' if trade_type_char == 'B' else 'Sell'} {total_qty} {symbol} @ {avg_price:.2f} {contract_id}"
    #     meta = {'filename': filepath, 'lineno': 0}

    #     postings = []

    #     if trade_type_char == 'B':
    #         stock_account = account.join(self.account_root, symbol)
    #         stock_units = amount.Amount(total_qty, symbol)
    #         cost = position.Cost(avg_price, self.currency, None, None)
    #         total_cash_outflow = (total_val + sum(allocated_charges.values())).quantize(D("0.01"))
    #         postings.append(data.Posting(stock_account, stock_units, cost, None, None, None))
    #         postings.append(data.Posting(self.account_cash, -amount.Amount(total_cash_outflow, self.currency), None, None, None, None))

    #     elif trade_type_char == 'S':
    #         stock_account = account.join(self.account_root, symbol)
    #         stock_units = amount.Amount(total_qty, symbol)
    #         price_amount = amount.Amount(avg_price, self.currency)
    #         cost = position.Cost(None, None, None, None)
    #         all_charges = sum(allocated_charges.values()) + self.demat_charge_per_sell
    #         net_cash_inflow = (total_val - all_charges).quantize(D("0.01"))
    #         postings.append(data.Posting(stock_account, -stock_units, cost, price_amount, None, None))
    #         postings.append(data.Posting(self.account_cash, amount.Amount(net_cash_inflow, self.currency), None, None, None, None))
    #         # Add PnL posting
    #         gains_account = self.account_gains.format(symbol) if '{}' in self.account_gains else self.account_gains
    #         postings.append(data.Posting(gains_account, None, None, None, None, None))
    #         # Demat
    #         if self.demat_charge_per_sell:
    #             postings.append(data.Posting(account.join(self.account_fees, 'Demat'),
    #                                          amount.Amount(self.demat_charge_per_sell, self.currency), None, None, None, None))

    #     # Charge postings
    #     for cname, cval in allocated_charges.items():
    #         if cval > 0:
    #             postings.append(data.Posting(self._map_charge_to_account(cname),
    #                                          amount.Amount(cval, self.currency), None, None, None, None))

    #     return data.Transaction(meta=meta, date=contract_date, flag='*',
    #                             payee=None, narration=narration,
    #                             tags=frozenset(), links=frozenset(),
    #                             postings=postings)

    def _create_order_transaction(self, order_trades: List[Dict],
                              contract_elem: ET.Element,
                              contract_date: datetime.date,
                              contract_id: str,
                              client_name: str,
                              filepath: str) -> data.Transaction:

        total_qty = sum(abs(t['quantity']) for t in order_trades)
        total_val = sum(abs(t['value']) for t in order_trades)
        avg_price = total_val / total_qty if total_qty else D('0')

        first_trade = order_trades[0]
        symbol = first_trade['symbol']
        trade_type_char = first_trade['type']
        order_id = first_trade['order_id']
        instrument_id = first_trade['instrument_id']
        segment_id = first_trade['segment_id']

        # Allocate XML charges
        allocated_charges = self._allocate_contract_charges(contract_elem, total_val)

        # Validate using policy
        trade_type = self._detect_trade_type(instrument_id, segment_id, order_trades)
        policy_charges = self._calculate_charges(order_trades, trade_type)
        for cname, cval in allocated_charges.items():
            if cname in policy_charges:
                if abs(cval - policy_charges[cname]) > D("0.05"):
                    print(f"[WARN] Charge mismatch {cname} order {order_id}: XML={cval} Policy={policy_charges[cname]}")

        narration = f"{'Buy' if trade_type_char == 'B' else 'Sell'} {total_qty} {symbol} @ {avg_price:.2f} {contract_id}"
        # meta = {'filename': filepath, 'lineno': 0}
        meta = data.new_metadata(filepath, 0)
        postings = []

        # Common proceeds and charges
        proceeds = total_val.quantize(D("0.001"))
        charges_total = sum(allocated_charges.values())
        if trade_type_char == 'S':
            charges_total += self.demat_charge_per_sell

        if trade_type_char == 'B':
            stock_account = account.join(self.account_root, symbol)
            stock_units = amount.Amount(total_qty, symbol)
            cost = position.Cost(avg_price, self.currency, None, None)
            cash_flow = (proceeds + charges_total).quantize(D("0.001"))  # outflow
            postings.append(data.Posting(stock_account, stock_units, cost, None, None, None))
            postings.append(data.Posting(self.account_cash,
                                         -amount.Amount(cash_flow, self.currency),
                                         None, None, None, None))

        elif trade_type_char == 'S':
            stock_account = account.join(self.account_root, symbol)
            stock_units = amount.Amount(total_qty, symbol)
            price_amount = amount.Amount(avg_price, self.currency)
            cost = position.Cost(None, None, None, None)
            cash_flow = (proceeds - charges_total).quantize(D("0.001"))  # inflow
            postings.append(data.Posting(stock_account, -stock_units, cost, price_amount, None, None))
            postings.append(data.Posting(self.account_cash,
                                         amount.Amount(cash_flow, self.currency),
                                         None, None, None, None))
            # PnL autoposting
            gains_account = self.account_gains.format(symbol) if '{}' in self.account_gains else self.account_gains
            postings.append(data.Posting(gains_account, None, None, None, None, None))
            # Demat (only as expense, not baked into cash again)
            if self.demat_charge_per_sell:
                postings.append(data.Posting(account.join(self.account_fees, 'Demat'),
                                             amount.Amount(self.demat_charge_per_sell, self.currency),
                                             None, None, None, None))

        # Charge postings (only once!)
        for cname, cval in allocated_charges.items():
                if cval > 0:
                    postings.append(data.Posting(self._map_charge_to_account(cname),
                                                 amount.Amount(cval, self.currency),
                                                 None, None, None, None))

        return data.Transaction(meta=meta, date=contract_date, flag='*',
                                    payee=None, narration=narration,
                                    tags=frozenset(), links=frozenset(),
                                    postings=postings)

    # -------------------
    # Charge mapping
    # -------------------

    def _map_charge_to_account(self, charge_name: str) -> str:
        cname = charge_name.lower()
        if 'brokerage' in cname:
            return account.join(self.account_fees, 'Brokerage')
        elif 'exchange transaction' in cname:
            return account.join(self.account_fees, 'Exchange')
        elif 'stt' in cname or 'securities transaction tax' in cname:
            return account.join(self.account_fees, 'STT')
        elif 'stamp' in cname:
            return account.join(self.account_fees, 'StampDuty')
        elif 'igst' in cname or 'integrated gst' in cname:
            return account.join(self.account_fees, 'IGST')
        elif 'cgst' in cname:
            return account.join(self.account_fees, 'CGST')
        elif 'sgst' in cname:
            return account.join(self.account_fees, 'SGST')
        elif 'sebi' in cname:
            return account.join(self.account_fees, 'SEBI')
        else:
            return account.join(self.account_fees, 'Other')

    # -------------------
    # Trade type detection
    # -------------------

    def _detect_trade_type(self, instrument_id: str, segment_id: str, trades: List[Dict]) -> TradeType:
        if 'NFO' in segment_id or 'BFO' in segment_id or 'DERIVATIVES' in segment_id.upper():
            if 'FUT' in instrument_id or any('FUT' in t.get('symbol', '') for t in trades):
                return TradeType.FO_FUTURES
            else:
                return TradeType.FO_OPTIONS
        trade_types = set(t['type'] for t in trades)
        return TradeType.EQUITY_INTRADAY if len(trade_types) > 1 else TradeType.EQUITY_DELIVERY
