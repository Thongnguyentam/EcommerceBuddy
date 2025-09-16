package database

import (
	"fmt"
	"github.com/GoogleCloudPlatform/microservices-demo/src/checkoutservice/internal/models"
	"github.com/sirupsen/logrus"
)

// MockConnection implements a mock database for testing
type MockConnection struct {
	orders      map[string]*models.Order
	orderItems  map[string][]models.OrderItem
	userOrders  map[string][]string // userID -> orderIDs
	log         *logrus.Logger
	shouldError bool
}

// NewMockConnection creates a new mock database connection
func NewMockConnection(log *logrus.Logger) *MockConnection {
	return &MockConnection{
		orders:     make(map[string]*models.Order),
		orderItems: make(map[string][]models.OrderItem),
		userOrders: make(map[string][]string),
		log:        log,
	}
}

// SetShouldError configures the mock to return errors for testing error scenarios
func (mc *MockConnection) SetShouldError(shouldError bool) {
	mc.shouldError = shouldError
}

// SaveOrder saves an order to the mock database
func (mc *MockConnection) SaveOrder(order *models.Order, items []models.OrderItem) error {
	if mc.shouldError {
		return fmt.Errorf("mock database error")
	}

	// Store order
	mc.orders[order.OrderID] = order

	// Store order items
	mc.orderItems[order.OrderID] = items

	// Update user orders index
	mc.userOrders[order.UserID] = append(mc.userOrders[order.UserID], order.OrderID)

	mc.log.Infof("Mock: Saved order %s for user %s with %d items", 
		order.OrderID, order.UserID, len(items))

	return nil
}

// GetOrdersByUser retrieves all orders for a specific user from mock database
func (mc *MockConnection) GetOrdersByUser(userID string) ([]models.Order, error) {
	if mc.shouldError {
		return nil, fmt.Errorf("mock database error")
	}

	orderIDs, exists := mc.userOrders[userID]
	if !exists {
		return []models.Order{}, nil
	}

	var orders []models.Order
	for _, orderID := range orderIDs {
		if order, exists := mc.orders[orderID]; exists {
			orders = append(orders, *order)
		}
	}

	mc.log.Infof("Mock: Retrieved %d orders for user %s", len(orders), userID)
	return orders, nil
}

// GetOrderItems retrieves all items for a specific order from mock database
func (mc *MockConnection) GetOrderItems(orderID string) ([]models.OrderItem, error) {
	if mc.shouldError {
		return nil, fmt.Errorf("mock database error")
	}

	items, exists := mc.orderItems[orderID]
	if !exists {
		return []models.OrderItem{}, nil
	}

	mc.log.Infof("Mock: Retrieved %d items for order %s", len(items), orderID)
	return items, nil
}

// Close is a no-op for the mock database
func (mc *MockConnection) Close() error {
	mc.log.Info("Mock: Database connection closed")
	return nil
}

// ClearData clears all data from the mock database (useful for test cleanup)
func (mc *MockConnection) ClearData() {
	mc.orders = make(map[string]*models.Order)
	mc.orderItems = make(map[string][]models.OrderItem)
	mc.userOrders = make(map[string][]string)
	mc.log.Info("Mock: Database data cleared")
} 