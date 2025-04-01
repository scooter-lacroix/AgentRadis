from dataclasses import dataclass
from typing import Dict, Optional, Any
import time
import asyncio


@dataclass
class CryptoPrice:
    symbol: str
    price_usd: float
    timestamp: float


class CryptoError(Exception):
    """Base exception for cryptocurrency operations"""
    pass


class CryptoTool:
    def __init__(self):
        """Initialize the CryptoTool with mock price data for common cryptocurrencies"""
        self._mock_prices = {
            "BTC": 30000.00,
            "ETH": 2000.00,
            "USDT": 1.00,
            "BNB": 300.00,
            "XRP": 0.50,
        }
        
    @property
    def name(self) -> str:
        """The name of the tool."""
        return "crypto_tool"
        
    @property
    def description(self) -> str:
        """A human-readable description of what the tool does."""
        return "Get cryptocurrency prices and perform conversions between different cryptocurrencies"
        
    @property
    def parameters(self) -> Dict[str, Any]:
        """JSON schema describing the tool's parameters."""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["get_price", "convert", "list_supported"],
                    "description": "The action to perform (get_price, convert, or list_supported)"
                },
                "symbol": {
                    "type": "string",
                    "description": "The cryptocurrency symbol (e.g., 'BTC', 'ETH') for price lookup"
                },
                "amount": {
                    "type": "number",
                    "description": "The amount to convert from one cryptocurrency to another"
                },
                "from_symbol": {
                    "type": "string",
                    "description": "Source cryptocurrency symbol for conversion"
                },
                "to_symbol": {
                    "type": "string",
                    "description": "Target cryptocurrency symbol for conversion"
                }
            },
            "required": ["action"]
        }

    def get_price(self, symbol: str) -> CryptoPrice:
        """
        Get the current price of a cryptocurrency in USD

        Args:
            symbol: The cryptocurrency symbol (e.g., 'BTC', 'ETH')

        Returns:
            CryptoPrice object containing symbol, price and timestamp

        Raises:
            CryptoError: If the cryptocurrency is not found
        """
        symbol = symbol.upper()
        if symbol not in self._mock_prices:
            raise CryptoError(f"Cryptocurrency {symbol} not found")

        return CryptoPrice(
            symbol=symbol, price_usd=self._mock_prices[symbol], timestamp=time.time()
        )

    def convert(self, amount: float, from_symbol: str, to_symbol: str) -> float:
        """
        Convert an amount from one cryptocurrency to another

        Args:
            amount: The amount to convert
            from_symbol: Source cryptocurrency symbol
            to_symbol: Target cryptocurrency symbol

        Returns:
            Converted amount in target cryptocurrency

        Raises:
            CryptoError: If either cryptocurrency is not found
        """
        from_symbol = from_symbol.upper()
        to_symbol = to_symbol.upper()

        if from_symbol not in self._mock_prices:
            raise CryptoError(f"Source cryptocurrency {from_symbol} not found")
        if to_symbol not in self._mock_prices:
            raise CryptoError(f"Target cryptocurrency {to_symbol} not found")

        # Convert through USD
        usd_value = amount * self._mock_prices[from_symbol]
        return usd_value / self._mock_prices[to_symbol]

    def get_supported_currencies(self) -> Dict[str, float]:
        """
        Get a list of supported cryptocurrencies and their current prices

        Returns:
            Dictionary mapping currency symbols to their USD prices
        """
        return self._mock_prices.copy()

    def format_price(self, price: CryptoPrice) -> str:
        """
        Format a cryptocurrency price for display

        Args:
            price: CryptoPrice object to format

        Returns:
            Formatted price string
        """
        return f"{price.symbol}: ${price.price_usd:,.2f} (as of {time.ctime(price.timestamp)})"
        
    async def run(self, **kwargs) -> Any:
        """
        Execute the cryptocurrency tool functionality.
        
        Args:
            action: The action to perform (get_price, convert, list_supported)
            symbol: For get_price action, the cryptocurrency symbol
            amount: For convert action, the amount to convert
            from_symbol: For convert action, the source cryptocurrency
            to_symbol: For convert action, the target cryptocurrency
            
        Returns:
            Results of the requested action
        """
        try:
            action = kwargs.get("action")
            
            if action == "get_price":
                symbol = kwargs.get("symbol")
                if not symbol:
                    return "Error: Symbol is required for get_price action"
                    
                price = self.get_price(symbol)
                return self.format_price(price)
                
            elif action == "convert":
                amount = kwargs.get("amount")
                from_symbol = kwargs.get("from_symbol")
                to_symbol = kwargs.get("to_symbol")
                
                if None in (amount, from_symbol, to_symbol):
                    return "Error: amount, from_symbol, and to_symbol are required for convert action"
                    
                result = self.convert(amount, from_symbol, to_symbol)
                return f"{amount} {from_symbol} = {result:.6f} {to_symbol}"
                
            elif action == "list_supported":
                currencies = self.get_supported_currencies()
                return "\n".join([f"{symbol}: ${price:,.2f}" for symbol, price in currencies.items()])
                
            else:
                return f"Error: Unknown action '{action}'. Supported actions are: get_price, convert, list_supported"
                
        except CryptoError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"
            
    def as_function(self) -> Dict[str, Any]:
        """Get the tool's schema in LLM function format."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }
        
    async def cleanup(self) -> None:
        """Clean up any resources used by the tool."""
        # No resources to clean up for this tool
        pass
        
    async def reset(self) -> None:
        """Reset the tool to its initial state."""
        # No state to reset for this tool
        pass
