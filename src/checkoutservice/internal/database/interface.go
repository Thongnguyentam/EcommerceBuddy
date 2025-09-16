package database

import (
	"github.com/GoogleCloudPlatform/microservices-demo/src/checkoutservice/internal/models"
)

// DatabaseInterface defines the contract for database operations
type DatabaseInterface interface {
	SaveOrder(order *models.Order, items []models.OrderItem) error
	GetOrdersByUser(userID string) ([]models.Order, error)
	GetOrderItems(orderID string) ([]models.OrderItem, error)
	Close() error
}

// Ensure our implementations satisfy the interface
var _ DatabaseInterface = (*Connection)(nil)
var _ DatabaseInterface = (*MockConnection)(nil) 