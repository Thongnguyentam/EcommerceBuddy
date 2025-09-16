package services

import (
	"fmt"
	"github.com/GoogleCloudPlatform/microservices-demo/src/checkoutservice/internal/database"
	"github.com/GoogleCloudPlatform/microservices-demo/src/checkoutservice/internal/models"
	pb "github.com/GoogleCloudPlatform/microservices-demo/src/checkoutservice/genproto"
	"github.com/sirupsen/logrus"
)

// OrderService handles order-related business logic
type OrderService struct {
	db  database.DatabaseInterface
	log *logrus.Logger
}

// NewOrderService creates a new OrderService
func NewOrderService(db database.DatabaseInterface, log *logrus.Logger) *OrderService {
	return &OrderService{
		db:  db,
		log: log,
	}
}

// SaveOrder saves an order to the database
func (os *OrderService) SaveOrder(orderResult *pb.OrderResult, email, userID string, total *pb.Money) error {
	// Convert protobuf to internal models
	order := models.NewOrderFromProto(orderResult, email, userID, total)
	items := models.NewOrderItemsFromProto(orderResult.OrderId, orderResult.Items)

	// Save to database
	if err := os.db.SaveOrder(order, items); err != nil {
		return fmt.Errorf("failed to save order to database: %v", err)
	}

	os.log.Infof("order %s saved to database successfully", order.OrderID)
	return nil
}

// GetUserOrderHistory retrieves order history for a user
func (os *OrderService) GetUserOrderHistory(userID string) ([]models.Order, error) {
	orders, err := os.db.GetOrdersByUser(userID)
	if err != nil {
		return nil, fmt.Errorf("failed to get user order history: %v", err)
	}

	return orders, nil
}

// GetOrderDetails retrieves full order details including items
func (os *OrderService) GetOrderDetails(orderID string) (*models.Order, []models.OrderItem, error) {
	// Get order items
	items, err := os.db.GetOrderItems(orderID)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to get order items: %v", err)
	}

	// In a real implementation, you'd also fetch the order details
	// For now, returning nil order but valid items
	return nil, items, nil
} 