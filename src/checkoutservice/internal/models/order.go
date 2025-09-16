package models

import (
	"fmt"
	"time"
	pb "github.com/GoogleCloudPlatform/microservices-demo/src/checkoutservice/genproto"
)

// Order represents an order in the database
type Order struct {
	OrderID              string    `db:"order_id" json:"order_id"`
	UserID               string    `db:"user_id" json:"user_id"`
	Email                string    `db:"email" json:"email"`
	TotalAmountCurrency  string    `db:"total_amount_currency" json:"total_amount_currency"`
	TotalAmountUnits     int64     `db:"total_amount_units" json:"total_amount_units"`
	TotalAmountNanos     int32     `db:"total_amount_nanos" json:"total_amount_nanos"`
	ShippingTrackingID   string    `db:"shipping_tracking_id" json:"shipping_tracking_id"`
	ShippingAddress      string    `db:"shipping_address" json:"shipping_address"`
	OrderDate            time.Time `db:"order_date" json:"order_date"`
	Status               string    `db:"status" json:"status"`
}

// OrderItem represents an item in an order
type OrderItem struct {
	ID                   int    `db:"id" json:"id"`
	OrderID              string `db:"order_id" json:"order_id"`
	ProductID            string `db:"product_id" json:"product_id"`
	Quantity             int32  `db:"quantity" json:"quantity"`
	UnitPriceCurrency    string `db:"unit_price_currency" json:"unit_price_currency"`
	UnitPriceUnits       int64  `db:"unit_price_units" json:"unit_price_units"`
	UnitPriceNanos       int32  `db:"unit_price_nanos" json:"unit_price_nanos"`
	TotalPriceCurrency   string `db:"total_price_currency" json:"total_price_currency"`
	TotalPriceUnits      int64  `db:"total_price_units" json:"total_price_units"`
	TotalPriceNanos      int32  `db:"total_price_nanos" json:"total_price_nanos"`
}

// NewOrderFromProto creates an Order from protobuf OrderResult
func NewOrderFromProto(orderResult *pb.OrderResult, email, userID string, total *pb.Money) *Order {
	shippingAddressStr := formatShippingAddress(orderResult.ShippingAddress)
	
	return &Order{
		OrderID:              orderResult.OrderId,
		UserID:               userID,
		Email:                email,
		TotalAmountCurrency:  total.CurrencyCode,
		TotalAmountUnits:     total.Units,
		TotalAmountNanos:     total.Nanos,
		ShippingTrackingID:   orderResult.ShippingTrackingId,
		ShippingAddress:      shippingAddressStr,
		Status:               "completed",
	}
}

// NewOrderItemsFromProto creates OrderItems from protobuf OrderItems
func NewOrderItemsFromProto(orderID string, protoItems []*pb.OrderItem) []OrderItem {
	items := make([]OrderItem, len(protoItems))
	
	for i, item := range protoItems {
		// Calculate total price for this item
		totalUnits := item.Cost.Units * int64(item.GetItem().GetQuantity())
		totalNanos := int64(item.Cost.Nanos) * int64(item.GetItem().GetQuantity())
		
		// Handle nano overflow (1 billion nanos = 1 unit)
		if totalNanos >= 1000000000 {
			extraUnits := totalNanos / 1000000000
			totalUnits += extraUnits
			totalNanos = totalNanos % 1000000000
		}
		
		items[i] = OrderItem{
			OrderID:              orderID,
			ProductID:            item.GetItem().GetProductId(),
			Quantity:             item.GetItem().GetQuantity(),
			UnitPriceCurrency:    item.Cost.CurrencyCode,
			UnitPriceUnits:       item.Cost.Units,
			UnitPriceNanos:       item.Cost.Nanos,
			TotalPriceCurrency:   item.Cost.CurrencyCode,
			TotalPriceUnits:      totalUnits,
			TotalPriceNanos:      int32(totalNanos),
		}
	}
	
	return items
}

// formatShippingAddress formats the shipping address as a string
func formatShippingAddress(address *pb.Address) string {
	if address == nil {
		return ""
	}
	
	return fmt.Sprintf("%s, %s, %s %d, %s",
		address.StreetAddress,
		address.City,
		address.State,
		address.ZipCode,
		address.Country)
} 