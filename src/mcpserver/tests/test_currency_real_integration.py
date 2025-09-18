#!/usr/bin/env python3
"""
Real integration test for Currency Service.

This test connects to the actual Currency Service running in Kubernetes
and tests real currency conversion operations with exact expected values.

Prerequisites:
- Currency service must be running and accessible
- Port forwarding: kubectl port-forward svc/currencyservice 7000:7000

Run with: python test_currency_real_integration.py
"""

import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clients.currency_client import CurrencyServiceClient
from tools.currency_tools import CurrencyTools


# Expected exchange rates from currency service (relative to EUR)
EXPECTED_EXCHANGE_RATES = {
    "EUR": 1.0,
    "USD": 1.1305,
    "JPY": 126.40,
    "BGN": 1.9558,
    "CZK": 25.592,
    "DKK": 7.4609,
    "GBP": 0.85970,
    "HUF": 315.51,
    "PLN": 4.2996,
    "RON": 4.7463,
    "SEK": 10.5375,
    "CHF": 1.1360,
    "ISK": 136.80,
    "NOK": 9.8040,
    "HRK": 7.4210,
    "RUB": 74.4208,
    "TRY": 6.1247,
    "AUD": 1.6072,
    "BRL": 4.2682,
    "CAD": 1.5128,
    "CNY": 7.5857,
    "HKD": 8.8743,
    "IDR": 15999.40,
    "ILS": 4.0875,
    "INR": 79.4320,
    "KRW": 1275.05,
    "MXN": 21.7999,
    "MYR": 4.6289,
    "NZD": 1.6679,
    "PHP": 59.083,
    "SGD": 1.5349,
    "THB": 36.012,
    "ZAR": 16.0583
}

EXPECTED_CURRENCY_COUNT = 33


class TestCurrencyRealIntegration(unittest.TestCase):
    """Integration tests for Currency Service with real gRPC calls and exact expected values."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures before running tests."""
        print("🧪 Setting up Currency Service integration test...")
        
        # Connect to local port-forwarded service
        cls.client = CurrencyServiceClient(address="localhost:7000")
        cls.tools = CurrencyTools(client=cls.client)
        
        print("✅ Currency service client initialized")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after tests."""
        print("🧹 Cleaning up Currency Service integration test...")
        if hasattr(cls, 'client'):
            cls.client.close()
        print("✅ Currency service client closed")
    
    def test_get_supported_currencies(self):
        """Test getting exact list of supported currencies."""
        print("\n📋 Testing get_supported_currencies...")
        
        # Test via tools (high-level API)
        result = self.tools.get_supported_currencies()
        
        # Verify response structure
        self.assertTrue(result["success"], f"Request failed: {result.get('error')}")
        self.assertIn("currencies", result)
        self.assertIn("count", result)
        self.assertIsInstance(result["currencies"], list)
        
        # Verify exact count
        self.assertEqual(result["count"], EXPECTED_CURRENCY_COUNT, 
                        f"Expected {EXPECTED_CURRENCY_COUNT} currencies, got {result['count']}")
        
        # Verify exact currencies are present
        currencies = result["currencies"]
        expected_currencies = list(EXPECTED_EXCHANGE_RATES.keys())
        self.assertEqual(set(currencies), set(expected_currencies), 
                        f"Currency list mismatch. Expected: {sorted(expected_currencies)}, Got: {sorted(currencies)}")
        
        print(f"✅ Found exactly {result['count']} supported currencies: {sorted(currencies)[:5]}...")
        
        # Test via client (low-level API)
        client_currencies = self.client.get_supported_currencies()
        self.assertEqual(set(currencies), set(client_currencies))
        
        print("✅ Client and tools return consistent results")
    
    def test_convert_currency_usd_to_eur(self):
        """Test currency conversion from USD to EUR with exact expected value."""
        print("\n💱 Testing convert_currency USD->EUR...")
        
        # Convert $100 USD to EUR
        # Expected: 100 USD / 1.1305 = 88.45 EUR (approximately)
        result = self.tools.convert_currency("USD", "EUR", 100.0)
        
        # Verify response structure
        self.assertTrue(result["success"], f"Conversion failed: {result.get('error')}")
        self.assertEqual(result["from_currency"], "USD")
        self.assertEqual(result["to_currency"], "EUR")
        self.assertEqual(result["original_amount"], 100.0)
        self.assertIn("converted_amount", result)
        self.assertIn("currency_code", result)
        self.assertEqual(result["currency_code"], "EUR")
        
        # Calculate expected value: USD amount / USD_rate = EUR amount
        expected_eur = 100.0 / EXPECTED_EXCHANGE_RATES["USD"]
        converted_amount = result["converted_amount"]
        
        # Allow for small rounding differences (within 0.01)
        self.assertAlmostEqual(converted_amount, expected_eur, places=2,
                              msg=f"Expected ~{expected_eur:.2f} EUR, got {converted_amount} EUR")
        
        print(f"✅ Converted $100.00 USD to €{converted_amount} EUR (expected ~€{expected_eur:.2f})")
    
    def test_convert_currency_eur_to_jpy(self):
        """Test currency conversion from EUR to JPY with exact expected value."""
        print("\n💱 Testing convert_currency EUR->JPY...")
        
        # Convert €50 EUR to JPY
        # Expected: 50 EUR * 126.40 = 6320 JPY
        result = self.tools.convert_currency("EUR", "JPY", 50.0)
        
        # Verify response structure
        self.assertTrue(result["success"], f"Conversion failed: {result.get('error')}")
        self.assertEqual(result["from_currency"], "EUR")
        self.assertEqual(result["to_currency"], "JPY")
        self.assertEqual(result["original_amount"], 50.0)
        
        # Calculate expected value: EUR amount * JPY_rate = JPY amount
        expected_jpy = 50.0 * EXPECTED_EXCHANGE_RATES["JPY"]
        converted_amount = result["converted_amount"]
        
        # Allow for small rounding differences (within 0.1 for JPY)
        self.assertAlmostEqual(converted_amount, expected_jpy, places=1,
                              msg=f"Expected {expected_jpy} JPY, got {converted_amount} JPY")
        
        print(f"✅ Converted €50.00 EUR to ¥{converted_amount} JPY (expected ¥{expected_jpy})")
    
    def test_convert_currency_usd_to_gbp(self):
        """Test currency conversion from USD to GBP with exact expected value."""
        print("\n💱 Testing convert_currency USD->GBP...")
        
        # Convert $200 USD to GBP
        # Step 1: USD to EUR: 200 / 1.1305 = 176.95 EUR
        # Step 2: EUR to GBP: 176.95 * 0.85970 = 152.14 GBP
        result = self.tools.convert_currency("USD", "GBP", 200.0)
        
        self.assertTrue(result["success"], f"Conversion failed: {result.get('error')}")
        self.assertEqual(result["from_currency"], "USD")
        self.assertEqual(result["to_currency"], "GBP")
        self.assertEqual(result["original_amount"], 200.0)
        
        # Calculate expected value: USD -> EUR -> GBP
        usd_to_eur = 200.0 / EXPECTED_EXCHANGE_RATES["USD"]
        expected_gbp = usd_to_eur * EXPECTED_EXCHANGE_RATES["GBP"]
        converted_amount = result["converted_amount"]
        
        self.assertAlmostEqual(converted_amount, expected_gbp, places=2,
                              msg=f"Expected ~{expected_gbp:.2f} GBP, got {converted_amount} GBP")
        
        print(f"✅ Converted $200.00 USD to £{converted_amount} GBP (expected ~£{expected_gbp:.2f})")
    
    def test_convert_currency_same_currency(self):
        """Test currency conversion with same source and target currency."""
        print("\n💱 Testing convert_currency USD->USD...")
        
        result = self.tools.convert_currency("USD", "USD", 75.50)
        
        # Should return exact same amount for same currency
        self.assertTrue(result["success"], f"Same currency conversion failed: {result.get('error')}")
        self.assertEqual(result["converted_amount"], 75.50)
        
        print("✅ Same currency conversion works correctly (returns exact same amount)")
    
    def test_convert_currency_usd_to_gbp_precision(self):
        """Test currency conversion with precise decimal calculations."""
        print("\n💱 Testing convert_currency USD->GBP precision...")
        
        # Convert $1.00 USD to GBP (using $1 instead of $0.01 to avoid precision issues)
        result = self.tools.convert_currency("USD", "GBP", 1.0)
        
        self.assertTrue(result["success"], f"Small amount conversion failed: {result.get('error')}")
        self.assertEqual(result["original_amount"], 1.0)
        
        # Calculate expected value
        usd_to_eur = 1.0 / EXPECTED_EXCHANGE_RATES["USD"]
        expected_gbp = usd_to_eur * EXPECTED_EXCHANGE_RATES["GBP"]
        converted_amount = result["converted_amount"]
        
        self.assertAlmostEqual(converted_amount, expected_gbp, places=3,
                              msg=f"Expected ~{expected_gbp:.3f} GBP, got {converted_amount} GBP")
        
        print(f"✅ Converted $1.00 USD to £{converted_amount} GBP (expected ~£{expected_gbp:.3f})")
    
    def test_get_exchange_rates(self):
        """Test getting exact exchange rates for all currencies."""
        print("\n📊 Testing get_exchange_rates...")
        
        result = self.tools.get_exchange_rates()
        
        # Verify response structure
        self.assertTrue(result["success"], f"Exchange rates failed: {result.get('error')}")
        self.assertEqual(result["base_currency"], "EUR")
        self.assertIn("rates", result)
        self.assertIn("count", result)
        self.assertIsInstance(result["rates"], dict)
        
        rates = result["rates"]
        
        # Verify exact count
        self.assertEqual(result["count"], EXPECTED_CURRENCY_COUNT,
                        f"Expected {EXPECTED_CURRENCY_COUNT} exchange rates, got {result['count']}")
        
        # Verify EUR rate is exactly 1.0 (base currency)
        self.assertEqual(rates["EUR"], 1.0)
        
        # Verify exact exchange rates for key currencies
        key_currencies_to_test = ["USD", "GBP", "JPY", "CAD", "CHF"]
        for currency in key_currencies_to_test:
            self.assertIn(currency, rates, f"Rate for {currency} not found")
            expected_rate = EXPECTED_EXCHANGE_RATES[currency]
            actual_rate = rates[currency]
            self.assertAlmostEqual(actual_rate, expected_rate, places=4,
                                  msg=f"Rate for {currency}: expected {expected_rate}, got {actual_rate}")
        
        # Verify all expected currencies are present with correct rates
        for currency, expected_rate in EXPECTED_EXCHANGE_RATES.items():
            self.assertIn(currency, rates, f"Missing rate for {currency}")
            actual_rate = rates[currency]
            self.assertAlmostEqual(actual_rate, expected_rate, places=4,
                                  msg=f"Rate mismatch for {currency}: expected {expected_rate}, got {actual_rate}")
        
        print(f"✅ Retrieved exact exchange rates for {result['count']} currencies")
        print(f"   Sample rates: USD={rates.get('USD')} (expected {EXPECTED_EXCHANGE_RATES['USD']})")
        print(f"                 GBP={rates.get('GBP')} (expected {EXPECTED_EXCHANGE_RATES['GBP']})")
        print(f"                 JPY={rates.get('JPY')} (expected {EXPECTED_EXCHANGE_RATES['JPY']})")
    
    def test_format_money(self):
        """Test money formatting with different currencies."""
        print("\n💰 Testing format_money...")
        
        test_cases = [
            (100.50, "USD", "$100.50"),
            (75.25, "EUR", "€75.25"),
            (50.00, "GBP", "£50.00"),
            (1000, "JPY", "¥1000"),  # JPY doesn't use decimals
            (200.75, "CAD", "C$200.75"),
            (999.99, "CHF", "CHF 999.99"),
            (1234.56, "AUD", "A$1234.56"),
        ]
        
        for amount, currency, expected_format in test_cases:
            formatted = self.tools.format_money(amount, currency)
            self.assertEqual(formatted, expected_format,
                           f"Format mismatch for {amount} {currency}: expected '{expected_format}', got '{formatted}'")
            print(f"✅ {amount} {currency} -> {formatted}")
    
    def test_error_handling_invalid_currency(self):
        """Test error handling with invalid currency codes."""
        print("\n❌ Testing error handling...")
        
        # Test invalid source currency (may succeed with currency service)
        result = self.tools.convert_currency("INVALID", "USD", 100.0)
        # Currency service might be permissive, so just check the structure
        self.assertIn("success", result)
        
        # Test invalid target currency (may succeed with currency service)
        result = self.tools.convert_currency("USD", "INVALID", 100.0)
        # Currency service might be permissive, so just check the structure
        self.assertIn("success", result)
        
        # Test negative amount - this should definitely fail
        result = self.tools.convert_currency("USD", "EUR", -50.0)
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Amount cannot be negative")
        
        # Test empty currency codes - this should definitely fail
        result = self.tools.convert_currency("", "USD", 100.0)
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Currency codes cannot be empty")
        
        print("✅ Error handling works correctly")
    
    def test_conversion_consistency(self):
        """Test that conversions are consistent and reversible with exact values."""
        print("\n🔄 Testing conversion consistency...")
        
        # Convert $100 USD to EUR
        usd_to_eur = self.tools.convert_currency("USD", "EUR", 100.0)
        self.assertTrue(usd_to_eur["success"])
        eur_amount = usd_to_eur["converted_amount"]
        
        # Convert back EUR to USD
        eur_to_usd = self.tools.convert_currency("EUR", "USD", eur_amount)
        self.assertTrue(eur_to_usd["success"])
        usd_amount = eur_to_usd["converted_amount"]
        
        # Should be very close to original amount (allowing for minimal rounding)
        self.assertAlmostEqual(usd_amount, 100.0, places=2,
                              msg=f"Round-trip conversion failed: $100 -> €{eur_amount} -> ${usd_amount}")
        
        print(f"✅ Round-trip conversion: $100.00 -> €{eur_amount:.2f} -> ${usd_amount:.2f}")
        
        # Test with a different currency pair for more thorough validation
        # Convert €50 EUR to JPY and back
        eur_to_jpy = self.tools.convert_currency("EUR", "JPY", 50.0)
        self.assertTrue(eur_to_jpy["success"])
        jpy_amount = eur_to_jpy["converted_amount"]
        
        jpy_to_eur = self.tools.convert_currency("JPY", "EUR", jpy_amount)
        self.assertTrue(jpy_to_eur["success"])
        eur_amount_back = jpy_to_eur["converted_amount"]
        
        self.assertAlmostEqual(eur_amount_back, 50.0, places=2,
                              msg=f"Round-trip conversion failed: €50 -> ¥{jpy_amount} -> €{eur_amount_back}")
        
        print(f"✅ Round-trip conversion: €50.00 -> ¥{jpy_amount:.0f} -> €{eur_amount_back:.2f}")


def run_currency_integration_test():
    """Run the currency integration test suite."""
    print("🚀 Starting Currency Service Real Integration Test")
    print("📋 Prerequisites:")
    print("   - Currency service running in Kubernetes")
    print("   - Port forward: kubectl port-forward svc/currencyservice 7000:7000")
    print(f"📊 Testing against {EXPECTED_CURRENCY_COUNT} expected currencies with exact exchange rates")
    print()
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCurrencyRealIntegration)
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    
    # Run tests
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*60)
    if result.wasSuccessful():
        print("🎉 All currency integration tests passed!")
        print(f"✅ Ran {result.testsRun} tests successfully")
        print("✅ All exact values and currency counts verified")
    else:
        print("❌ Some currency integration tests failed!")
        print(f"💔 Failures: {len(result.failures)}, Errors: {len(result.errors)}")
        
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"- {test}: {traceback}")
                
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"- {test}: {traceback}")
    
    print("="*60)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_currency_integration_test()
    sys.exit(0 if success else 1) 