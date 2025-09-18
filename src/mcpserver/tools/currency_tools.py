from typing import List, Dict, Any, Optional
import logging

from clients.currency_client import CurrencyServiceClient

logger = logging.getLogger(__name__)


class CurrencyTools:
    """High-level currency operations for MCP server."""
    
    def __init__(self, client: CurrencyServiceClient):
        self.client = client
    
    def get_supported_currencies(self) -> Dict[str, Any]:
        """Get list of all supported currency codes.
        
        Returns:
            dict: Response with list of currency codes
        """
        try:
            currencies = self.client.get_supported_currencies()
            return {
                "success": True,
                "currencies": currencies,
                "count": len(currencies),
                "message": f"Retrieved {len(currencies)} supported currencies"
            }
        except Exception as e:
            logger.error(f"Error getting supported currencies: {e}")
            return {
                "success": False,
                "error": str(e),
                "currencies": [],
                "count": 0
            }
    
    def convert_currency(self, from_currency: str, to_currency: str, 
                        amount: float) -> Dict[str, Any]:
        """Convert currency from one type to another.
        
        Args:
            from_currency: Source currency code (e.g., 'USD')
            to_currency: Target currency code (e.g., 'EUR') 
            amount: Amount to convert as decimal (e.g., 12.34)
            
        Returns:
            dict: Conversion result with converted amount
        """
        try:
            # Validate inputs
            if not from_currency or not to_currency:
                return {
                    "success": False,
                    "error": "Currency codes cannot be empty"
                }
            
            if amount < 0:
                return {
                    "success": False,
                    "error": "Amount cannot be negative"
                }
            
            # Convert float to units and nanos
            units = int(amount)
            nanos = int((amount - units) * 1_000_000_000)
            
            result = self.client.convert_currency(
                from_currency.upper(), 
                to_currency.upper(), 
                units, 
                nanos
            )
            
            # Convert back to decimal
            converted_amount = float(result["units"]) + float(result["nanos"]) / 1_000_000_000
            
            return {
                "success": True,
                "from_currency": from_currency.upper(),
                "to_currency": to_currency.upper(),
                "original_amount": amount,
                "converted_amount": round(converted_amount, 2),
                "currency_code": result["currency_code"],
                "units": result["units"],
                "nanos": result["nanos"],
                "message": f"Converted {amount} {from_currency.upper()} to {converted_amount:.2f} {to_currency.upper()}"
            }
        except Exception as e:
            logger.error(f"Error converting currency: {e}")
            return {
                "success": False,
                "error": str(e),
                "from_currency": from_currency,
                "to_currency": to_currency,
                "original_amount": amount
            }
    
    def get_exchange_rates(self) -> Dict[str, Any]:
        """Get current exchange rates for all supported currencies.
        
        Returns:
            dict: Exchange rates relative to EUR
        """
        try:
            rates = self.client.get_exchange_rates()
            return {
                "success": True,
                "base_currency": "EUR",
                "rates": rates,
                "count": len(rates),
                "message": f"Retrieved exchange rates for {len(rates)} currencies"
            }
        except Exception as e:
            logger.error(f"Error getting exchange rates: {e}")
            return {
                "success": False,
                "error": str(e),
                "base_currency": "EUR",
                "rates": {}
            }
    
    def format_money(self, amount: float, currency_code: str) -> str:
        """Format money amount with currency symbol.
        
        Args:
            amount: Amount to format
            currency_code: Currency code (e.g., 'USD')
            
        Returns:
            str: Formatted money string (e.g., '$12.34')
        """
        currency_symbols = {
            'USD': '$',
            'EUR': '€', 
            'GBP': '£',
            'JPY': '¥',
            'CNY': '¥',
            'INR': '₹',
            'KRW': '₩',
            'RUB': '₽',
            'CHF': 'CHF ',
            'CAD': 'C$',
            'AUD': 'A$',
            'NZD': 'NZ$',
            'HKD': 'HK$',
            'SGD': 'S$',
        }
        
        symbol = currency_symbols.get(currency_code, f"{currency_code} ")
        
        # For currencies like JPY that don't use decimals
        if currency_code in ['JPY', 'KRW']:
            return f"{symbol}{int(amount)}"
        else:
            return f"{symbol}{amount:.2f}" 