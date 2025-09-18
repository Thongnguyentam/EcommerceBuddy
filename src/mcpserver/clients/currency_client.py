import grpc
import os
from typing import List, Dict, Optional, Any

from genproto import demo_pb2, demo_pb2_grpc


class CurrencyServiceClient:
    """Client for Currency Service gRPC operations."""
    
    def __init__(self, address: Optional[str] = None):
        self.address = address or os.getenv("CURRENCY_SERVICE_ADDR", "localhost:7000")
        self.channel = None
        self.stub = None
    
    def connect(self):
        """Establish gRPC connection to Currency Service."""
        if self.channel is None:
            self.channel = grpc.insecure_channel(self.address)
            self.stub = demo_pb2_grpc.CurrencyServiceStub(self.channel)
    
    def close(self):
        """Close the gRPC connection."""
        if self.channel:
            self.channel.close()
            self.channel = None
            self.stub = None
    
    def get_supported_currencies(self) -> List[str]:
        """Get list of supported currency codes."""
        self.connect()
        try:
            request = demo_pb2.Empty()
            response = self.stub.GetSupportedCurrencies(request)
            return list(response.currency_codes)
        except grpc.RpcError as e:
            raise Exception(f"Failed to get supported currencies: {e.details()}")
    
    def convert_currency(self, from_currency: str, to_currency: str, 
                        units: int, nanos: int = 0) -> Dict[str, Any]:
        """Convert currency from one type to another."""
        self.connect()
        try:
            from_money = demo_pb2.Money(
                currency_code=from_currency,
                units=units,
                nanos=nanos
            )
            
            request = demo_pb2.CurrencyConversionRequest()
            getattr(request, 'from').CopyFrom(from_money)
            request.to_code = to_currency
            
            response = self.stub.Convert(request)
            
            return {
                "currency_code": response.currency_code,
                "units": response.units,
                "nanos": response.nanos
            }
        except grpc.RpcError as e:
            raise Exception(f"Failed to convert currency: {e.details()}")
    
    def get_exchange_rates(self) -> Dict[str, float]:
        """Get exchange rates for all supported currencies (relative to EUR)."""
        # Note: This is a convenience method that uses the conversion logic
        # to get rates by converting 1 EUR to each supported currency
        self.connect()
        try:
            currencies = self.get_supported_currencies()
            rates = {}
            
            for currency in currencies:
                if currency == "EUR":
                    rates[currency] = 1.0
                else:
                    try:
                        result = self.convert_currency("EUR", currency, 1, 0)
                        # Convert to float: units + nanos/1000000000
                        rate = float(result["units"]) + float(result["nanos"]) / 1000000000.0
                        rates[currency] = rate
                    except Exception as e:
                        # If conversion fails, skip this currency
                        print(f"Warning: Could not get rate for {currency}: {e}")
                        continue
            
            return rates
        except Exception as e:
            raise Exception(f"Failed to get exchange rates: {e}") 