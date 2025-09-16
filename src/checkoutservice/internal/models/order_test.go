package models

import (
	"testing"

	pb "github.com/GoogleCloudPlatform/microservices-demo/src/checkoutservice/genproto"
)

func TestNewOrderFromProto(t *testing.T) {
	orderResult := &pb.OrderResult{
		OrderId:            "test-order-123",
		ShippingTrackingId: "TRACK-456",
		ShippingAddress: &pb.Address{
			StreetAddress: "123 Main St",
			City:          "Anytown",
			State:         "CA",
			ZipCode:       12345,
			Country:       "USA",
		},
	}

	total := &pb.Money{
		CurrencyCode: "USD",
		Units:        100,
		Nanos:        500000000, // $100.50
	}

	email := "test@example.com"
	userID := "user-789"

	order := NewOrderFromProto(orderResult, email, userID, total)

	// Test basic fields
	if order.OrderID != orderResult.OrderId {
		t.Errorf("Expected OrderID %s, got %s", orderResult.OrderId, order.OrderID)
	}
	if order.UserID != userID {
		t.Errorf("Expected UserID %s, got %s", userID, order.UserID)
	}
	if order.Email != email {
		t.Errorf("Expected Email %s, got %s", email, order.Email)
	}
	if order.TotalAmountCurrency != total.CurrencyCode {
		t.Errorf("Expected Currency %s, got %s", total.CurrencyCode, order.TotalAmountCurrency)
	}
	if order.TotalAmountUnits != total.Units {
		t.Errorf("Expected Units %d, got %d", total.Units, order.TotalAmountUnits)
	}
	if order.TotalAmountNanos != total.Nanos {
		t.Errorf("Expected Nanos %d, got %d", total.Nanos, order.TotalAmountNanos)
	}
	if order.ShippingTrackingID != orderResult.ShippingTrackingId {
		t.Errorf("Expected Tracking ID %s, got %s", orderResult.ShippingTrackingId, order.ShippingTrackingID)
	}
	if order.Status != "completed" {
		t.Errorf("Expected Status 'completed', got %s", order.Status)
	}

	// Test shipping address formatting
	expectedAddress := "123 Main St, Anytown, CA 12345, USA"
	if order.ShippingAddress != expectedAddress {
		t.Errorf("Expected Address '%s', got '%s'", expectedAddress, order.ShippingAddress)
	}
}

func TestNewOrderItemsFromProto(t *testing.T) {
	orderID := "test-order-456"
	protoItems := []*pb.OrderItem{
		{
			Item: &pb.CartItem{
				ProductId: "PRODUCT-1",
				Quantity:  2,
			},
			Cost: &pb.Money{
				CurrencyCode: "USD",
				Units:        15,
				Nanos:        990000000, // $15.99
			},
		},
		{
			Item: &pb.CartItem{
				ProductId: "PRODUCT-2",
				Quantity:  1,
			},
			Cost: &pb.Money{
				CurrencyCode: "EUR",
				Units:        25,
				Nanos:        500000000, // €25.50
			},
		},
	}

	items := NewOrderItemsFromProto(orderID, protoItems)

	if len(items) != len(protoItems) {
		t.Fatalf("Expected %d items, got %d", len(protoItems), len(items))
	}

	// Test first item
	item1 := items[0]
	if item1.OrderID != orderID {
		t.Errorf("Item 1: Expected OrderID %s, got %s", orderID, item1.OrderID)
	}
	if item1.ProductID != "PRODUCT-1" {
		t.Errorf("Item 1: Expected ProductID 'PRODUCT-1', got %s", item1.ProductID)
	}
	if item1.Quantity != 2 {
		t.Errorf("Item 1: Expected Quantity 2, got %d", item1.Quantity)
	}
	if item1.UnitPriceCurrency != "USD" {
		t.Errorf("Item 1: Expected Currency 'USD', got %s", item1.UnitPriceCurrency)
	}
	if item1.UnitPriceUnits != 15 {
		t.Errorf("Item 1: Expected Units 15, got %d", item1.UnitPriceUnits)
	}
	if item1.UnitPriceNanos != 990000000 {
		t.Errorf("Item 1: Expected Nanos 990000000, got %d", item1.UnitPriceNanos)
	}

	// Test total price calculation (2 * $15.99 = $31.98)
	expectedTotalUnits := int64(31)
	expectedTotalNanos := int32(980000000)
	if item1.TotalPriceUnits != expectedTotalUnits {
		t.Errorf("Item 1: Expected Total Units %d, got %d", expectedTotalUnits, item1.TotalPriceUnits)
	}
	if item1.TotalPriceNanos != expectedTotalNanos {
		t.Errorf("Item 1: Expected Total Nanos %d, got %d", expectedTotalNanos, item1.TotalPriceNanos)
	}

	// Test second item
	item2 := items[1]
	if item2.ProductID != "PRODUCT-2" {
		t.Errorf("Item 2: Expected ProductID 'PRODUCT-2', got %s", item2.ProductID)
	}
	if item2.Quantity != 1 {
		t.Errorf("Item 2: Expected Quantity 1, got %d", item2.Quantity)
	}
	if item2.UnitPriceCurrency != "EUR" {
		t.Errorf("Item 2: Expected Currency 'EUR', got %s", item2.UnitPriceCurrency)
	}

	// Test total price calculation (1 * €25.50 = €25.50)
	expectedTotalUnits2 := int64(25)
	expectedTotalNanos2 := int32(500000000)
	if item2.TotalPriceUnits != expectedTotalUnits2 {
		t.Errorf("Item 2: Expected Total Units %d, got %d", expectedTotalUnits2, item2.TotalPriceUnits)
	}
	if item2.TotalPriceNanos != expectedTotalNanos2 {
		t.Errorf("Item 2: Expected Total Nanos %d, got %d", expectedTotalNanos2, item2.TotalPriceNanos)
	}
}

func TestNewOrderItemsFromProto_NanoOverflow(t *testing.T) {
	orderID := "test-order-overflow"
	protoItems := []*pb.OrderItem{
		{
			Item: &pb.CartItem{
				ProductId: "PRODUCT-OVERFLOW",
				Quantity:  3,
			},
			Cost: &pb.Money{
				CurrencyCode: "USD",
				Units:        10,
				Nanos:        999999999, // $10.999999999
			},
		},
	}

	items := NewOrderItemsFromProto(orderID, protoItems)

	if len(items) != 1 {
		t.Fatalf("Expected 1 item, got %d", len(items))
	}

	item := items[0]

	// Test nano overflow handling (3 * $10.999999999 = $32.999999997)
	// Should be $32 + 999999997 nanos
	expectedTotalUnits := int64(32)
	expectedTotalNanos := int32(999999997)

	if item.TotalPriceUnits != expectedTotalUnits {
		t.Errorf("Expected Total Units %d, got %d", expectedTotalUnits, item.TotalPriceUnits)
	}
	if item.TotalPriceNanos != expectedTotalNanos {
		t.Errorf("Expected Total Nanos %d, got %d", expectedTotalNanos, item.TotalPriceNanos)
	}
}

func TestFormatShippingAddress_NilAddress(t *testing.T) {
	address := formatShippingAddress(nil)
	if address != "" {
		t.Errorf("Expected empty string for nil address, got '%s'", address)
	}
}

func TestFormatShippingAddress_CompleteAddress(t *testing.T) {
	address := &pb.Address{
		StreetAddress: "456 Oak Ave",
		City:          "Springfield",
		State:         "IL",
		ZipCode:       62701,
		Country:       "United States",
	}

	result := formatShippingAddress(address)
	expected := "456 Oak Ave, Springfield, IL 62701, United States"

	if result != expected {
		t.Errorf("Expected '%s', got '%s'", expected, result)
	}
} 