"""Beangulp based beancount importer for Indian Stock broker Zerodha
XML contract notes. This imports transactions from contract notes XML files
provided by the broker.

This importer processes XML contract notes that contain detailed trading information
including trades, charges, taxes, and totals. Unlike CSV importers, this processes
structured XML data with nested elements.
"""

__copyright__ = "Copyright (C) 2025  Prabu Anand K"
__license__ = "GNU GPLv3"
__version__ = "0.1"

import os
import re
import xml.etree.ElementTree as ET
from decimal import Decimal
from datetime import datetime
from typing import Optional, Dict, List

from beancount.core import data, amount, account, position
from beancount.core.number import D
from beangulp import Importer


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
        """Extract beancount directives from the XML contract note."""
        entries = []
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            for contract in root.findall('.//contract'):
                entries.extend(self._process_contract(contract, filepath))
        except ET.ParseError as e:
            print(f"Error parsing XML file {filepath}: {e}")
        except Exception as e:
            print(f"Error processing file {filepath}: {e}")
        return entries

    def _process_contract(self, contract_elem: ET.Element, filepath: str):
        contract_id = self._get_text(contract_elem, 'id', 'Unknown')
        contract_date = self._parse_date(self._get_text(contract_elem, 'timestamp'))
        if not contract_date:
            print(f"Skipping contract {contract_id}: Invalid date")
            return []
        client_name = self._get_text(contract_elem, 'client/name', 'Unknown Client')
        contract_charges = self._extract_contract_charges(contract_elem)
        trades_by_instrument = self._group_trades_by_instrument(contract_elem)
        if not trades_by_instrument:
            print(f"Skipping contract {contract_id}: No trades found")
            return []
        entries = []
        for instrument_id, trades in trades_by_instrument.items():
            entries.extend(
                self._create_consolidated_transactions(
                    trades, contract_charges, contract_date, contract_id, client_name, filepath
                )
            )
        # print(f"DEBUG: processing contract {contract_id}, trades={len(trades_by_instrument)}")
        return entries

    def _group_trades_by_instrument(self, contract_elem: ET.Element) -> Dict[str, List[Dict]]:
        """Group trades by instrument and order ID for consolidation.

        Zerodha often splits large orders into multiple small trades.
        We group these to create cleaner beancount transactions.

        Args:
            contract_elem: Contract XML element containing trades

        Returns:
            Dictionary mapping instrument_id to list of trade dictionaries
        """
        trades_by_instrument = {}

        for trade_elem in contract_elem.findall('.//trade'):
            # Extract trade information
            trade_data = {
                'id': self._get_text(trade_elem, 'id'),
                'order_id': self._get_text(trade_elem, 'order_id'),
                'timestamp': self._get_text(trade_elem, 'timestamp'),
                'exchange': self._get_text(trade_elem, 'exchange'),
                'type': self._get_text(trade_elem, 'type'),  # 'B' for buy, 'S' for sell
                'quantity': self._parse_decimal(self._get_text(trade_elem, 'quantity')),
                'price': self._parse_decimal(self._get_text(trade_elem, 'average_price')),
                'value': self._parse_decimal(self._get_text(trade_elem, 'value')),
                'instrument_id': trade_elem.get('instrument_id', 'Unknown'),
                'segment_id': trade_elem.get('segment_id', 'Unknown')
            }

            # Skip invalid trades
            if not trade_data['quantity'] or not trade_data['price']:
                continue

            # Extract symbol from instrument_id (format: NSE:SYMBOL - EQ / ISIN)
            symbol = self._extract_symbol(trade_data['instrument_id'])
            trade_data['symbol'] = symbol

            # Group by instrument_id for consolidation
            if trade_data['instrument_id'] not in trades_by_instrument:
                trades_by_instrument[trade_data['instrument_id']] = []
            trades_by_instrument[trade_data['instrument_id']].append(trade_data)

        return trades_by_instrument


    def _extract_contract_charges(self, contract_elem: ET.Element) -> Dict[str, Decimal]:
        """Extract all charges from the contract for proportional allocation.

        Args:
        contract_elem: Contract XML element

        Returns:
        Dictionary mapping charge names to amounts
        """
        charges = {}

        # Extract all charges from grandtotals (these are the final amounts)
        for charge_elem in contract_elem.findall('.//grandtotal'):
            charge_name = self._get_text(charge_elem, 'name')  # Keep as 'name' - your original was correct
            charge_type = self._get_text(charge_elem, 'type')
            charge_value_str = self._get_text(charge_elem, 'value')

            # Skip if charge name is None or empty
            if not charge_name or charge_name.strip() == 'None':
                continue

            # Convert to Decimal - THIS IS THE KEY FIX
            charge_value = self._parse_decimal(charge_value_str)

            # Skip zero charges, None values, and the net settlement amount
            if charge_value == 0:
                continue
            if 'PAY IN / PAY OUT OBLIGATION' in charge_name:
                continue  # This is gross trade value, not a charge
            if 'Net amount Receivable' in charge_name:
                continue  # This is net settlement, handled separately
            # # Skip empty charge names
            # if not charge_name.strip():
            #     continue

            charges[charge_name] = charge_value

        return charges


    def _create_consolidated_transactions(self, trades: List[Dict], contract_charges: Dict[str, Decimal],
                                          contract_date: datetime.date, contract_id: str,
                                          client_name: str, filepath: str) -> List[data.Transaction]:
        """Create single consolidated transactions that include trades and all charges."""


        """Create single consolidated transactions that include trades and all charges.

        This creates one transaction per order that includes:
        - The stock purchase/sale
        - Proportional allocation of all charges and fees
        - Demat charges for sell transactions
        - Proper cost basis calculation including all costs

        Args:
            trades: List of trade dictionaries for the same instrument
            contract_charges: Dictionary of all contract charges
            contract_date: Date of the contract
            contract_id: Contract identifier
            client_name: Client name for reference

        Yields:
            Consolidated beancount transaction objects
        """
        if not trades:
            return []

        # Calculate total contract value for proportional charge allocation
        total_contract_value = sum(t['value'] for t in trades)

        # Group trades by order_id and type to further consolidate
        orders = {}
        for trade in trades:
            key = (trade['order_id'], trade['type'])
            if key not in orders:
                orders[key] = []
            orders[key].append(trade)

        txns = []

        # Create transaction for each order
        for (order_id, trade_type), order_trades in orders.items():
            # Calculate consolidated trade values
            total_quantity = sum(t['quantity'] for t in order_trades)
            total_value = sum(t['value'] for t in order_trades)
            avg_price = total_value / total_quantity if total_quantity else D('0')

            # Get representative trade data
            first_trade = order_trades[0]
            symbol = first_trade['symbol']
            exchange = first_trade['exchange']

            # Calculate proportional charges based on this order's value
            order_proportion = total_value / total_contract_value if total_contract_value else D('0')

            # Create transaction description
            trade_type_desc = 'Buy' if trade_type == 'B' else 'Sell'
            trade_ids = [t['id'] for t in order_trades]
            narration = f"{trade_type_desc} {total_quantity} {symbol} @ {avg_price:.2f}"

            # Create metadata for reference
            meta = {
                '__tolerances__': {},  # Required for beancount v3
                'lineno': 0,           # Needed by beancount for sorting
                'filename': filepath,  # required by beancount
                'order_id': order_id,
                'trade_ids': ','.join(trade_ids),
                'exchange': exchange,
                'contract_id': contract_id
            }

            # Create postings - single transaction with all charges included
            postings = []

            if trade_type == 'B':  # Buy transaction
                # Calculate total cost including charges
                proportional_charges = sum(charge * order_proportion for charge in contract_charges.values())
                total_cost_per_share = (total_value + proportional_charges) / total_quantity
                total_cash_outflow = total_value + proportional_charges

                # Stock account with total cost basis
                stock_account = account.join(self.account_root, symbol)
                stock_units = amount.Amount(total_quantity.quantize(D('0.0001')), symbol)
                cost = position.Cost(total_cost_per_share.quantize(D('0.01')), self.currency, None, None)

                # Cash outflow
                cash_amount = amount.Amount(total_cash_outflow.quantize(D('0.01')), self.currency)

                postings = [
                    data.Posting(stock_account, stock_units, cost, None, None, None),
                    data.Posting(self.account_cash, -cash_amount, None, None, None, None)
                ]

                # Add individual charge postings for detailed tracking
                for charge_name, charge_value in contract_charges.items():
                    proportional_charge = charge_value * order_proportion
                    if proportional_charge > 0:
                        charge_amount = amount.Amount(proportional_charge.quantize(D('0.01')), self.currency)
                        charge_account = self._map_charge_to_account(charge_name)
                        postings.append(
                            data.Posting(charge_account, charge_amount, None, None, None, None)
                        )

            elif trade_type == 'S':  # Sell transaction
                # Calculate charges including optional demat charge
                proportional_charges = sum(charge * order_proportion for charge in contract_charges.values())
                demat_charge = self.demat_charge_per_sell if self.demat_charge_per_sell else D('0')
                total_charges = proportional_charges + demat_charge

                # Net proceeds after all charges
                net_proceeds = total_value - total_charges

                # Stock account (what we sold) - use pure trade price for capital gains
                stock_account = account.join(self.account_root, symbol)
                stock_units = amount.Amount(total_quantity.quantize(D('0.0001')), symbol)
                price_amount = amount.Amount(avg_price.quantize(D('0.01')), self.currency)

                # Use empty cost for sells (let beancount handle cost basis)
                cost = position.Cost(None, None, None, None)

                # Cash proceeds
                cash_amount = amount.Amount(net_proceeds.quantize(D('0.01')), self.currency)

                # Capital gains account (auto-calculated by beancount)
                gains_account = self.account_gains.format(symbol) if '{}' in self.account_gains else self.account_gains

                postings = [
                    data.Posting(stock_account, -stock_units, cost, price_amount, None, None),
                    data.Posting(self.account_cash, cash_amount, None, None, None, None),
                    data.Posting(gains_account, None, None, None, None, None)  # Auto-calculated
                ]

                # Add individual charge postings for detailed tracking
                for charge_name, charge_value in contract_charges.items():
                    proportional_charge = charge_value * order_proportion
                    if proportional_charge > 0:
                        charge_amount = amount.Amount(proportional_charge.quantize(D('0.01')), self.currency)
                        charge_account = self._map_charge_to_account(charge_name)
                        postings.append(
                            data.Posting(charge_account, charge_amount, None, None, None, None)
                        )

                # Add demat charge if applicable
                if demat_charge > 0:
                    demat_amount = amount.Amount(demat_charge.quantize(D('0.01')), self.currency)
                    demat_account = account.join(self.account_fees, 'Demat')
                    postings.append(
                        data.Posting(demat_account, demat_amount, None, None, None, None)
                    )
                # print(f"DEBUG: created Sell txn for {symbol}, qty={total_quantity}, proceeds={net_proceeds}")
            # Create and yield transaction
            txn = data.Transaction(
                meta=meta,
                date=contract_date,
                flag='*',  # Cleared transaction
                payee=None,
                narration=narration,
                tags=frozenset({'zerodha', 'trade'}),
                links=frozenset(),
                postings=postings
            )
            txns.append(txn)

        return txns

    def _map_charge_to_account(self, charge_name: str) -> str:
        """Map charge name to appropriate account for detailed fee tracking.

        Args:
            charge_name: Name of the charge from XML

        Returns:
            Account name for the charge
        """
        charge_name_lower = charge_name.lower()

        if 'brokerage' in charge_name_lower:
            return account.join(self.account_fees, 'Brokerage')
        elif 'securities transaction tax' in charge_name_lower or charge_name_lower == 'stt':
            return account.join(self.account_fees, 'STT')  # Securities Transaction Tax
        elif 'stamp duty' in charge_name_lower:
            return account.join(self.account_fees, 'StampDuty')
        elif 'integrated gst' in charge_name_lower or 'igst' in charge_name_lower:
            return account.join(self.account_fees, 'IGST')  # Integrated GST
        elif 'central gst' in charge_name_lower or 'cgst' in charge_name_lower:
            return account.join(self.account_fees, 'CGST')  # Central GST
        elif 'state gst' in charge_name_lower or 'sgst' in charge_name_lower:
            return account.join(self.account_fees, 'SGST')  # State GST
        elif 'sebi' in charge_name_lower and 'turnover' in charge_name_lower:
            return account.join(self.account_fees, 'SEBI-Turnover')  # SEBI Turnover Fees
        elif 'exchange transaction charges' in charge_name_lower:
            return account.join(self.account_fees, 'Exchange-Transaction')
        elif 'clearing charges' in charge_name_lower:
            return account.join(self.account_fees, 'Exchange-Clearing')
        else:
            # For any unrecognized charges, use Other with warning
            print(f"Warning: Unrecognized charge type: {charge_name}")
            return account.join(self.account_fees, 'Other')

    # Utility methods for XML parsing and data conversion

    def _get_text(self, element: ET.Element, xpath: str, default: str = '') -> str:
        """Safely extract text from XML element using xpath.

        Args:
            element: XML element to search
            xpath: XPath expression to find target element
            default: Default value if element not found

        Returns:
            Text content of found element or default value
        """
        try:
            found = element.find(xpath)
            return found.text.strip() if found is not None and found.text else default
        except AttributeError:
            return default

    def _parse_date(self, date_str: str) -> Optional[datetime.date]:
        """Parse date string from XML into datetime.date object.

        Handles the format used in Zerodha XML files: YYYY-MM-DD

        Args:
            date_str: Date string to parse

        Returns:
            Parsed date object or None if parsing fails
        """
        if not date_str:
            return None

        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            print(f"Unable to parse date: {date_str}")
            return None


    def _parse_decimal(self, value_str: str) -> Decimal:
        """Parse string value into Decimal for precise financial calculations."""
        if not value_str or value_str.strip() in ['', 'None', 'null']:
            return D('0')

        try:
            return D(value_str.strip())
        except (ValueError, TypeError):
            print(f"Unable to parse decimal: {value_str}")
            return D('0')


    def _extract_symbol(self, instrument_id: str) -> str:
        """Extract trading symbol from instrument ID.

        Instrument IDs in Zerodha XML follow format: NSE:SYMBOL - EQ / ISIN
        This method extracts just the SYMBOL part.

        Args:
            instrument_id: Full instrument identifier

        Returns:
            Extracted symbol or 'UNKNOWN' if extraction fails
        """
        if not instrument_id:
            return 'UNKNOWN'

        try:
            # Split by colon and take the second part, then split by space
            parts = instrument_id.split(':')
            if len(parts) >= 2:
                symbol_part = parts[1].split(' - ')[0].strip()
                return symbol_part
            return 'UNKNOWN'
        except (IndexError, AttributeError):
            return 'UNKNOWN'
