package services

import (
	"testing"
	"time"

	"github.com/GoogleCloudPlatform/microservices-demo/src/checkoutservice/internal/database"
	pb "github.com/GoogleCloudPlatform/microservices-demo/src/checkoutservice/genproto"
	"github.com/google/uuid"
	"github.com/sirupsen/logrus"
)

func setupTestOrderService() (*OrderService, *database.MockConnection) {
	logger := logrus.New()
	logger.SetLevel(logrus.ErrorLevel) // Reduce noise in tests
	
	mockDB := database.NewMockConnection(logger)
	orderService := NewOrderService(mockDB, logger)
	
	return orderService, mockDB
}

func createTestOrderResult() (*pb.OrderResult, *pb.Money, string, string) {
	orderID, _ := uuid.NewUUID()
	
	orderResult := &pb.OrderResult{
		OrderId:            orderID.String(),
		ShippingTrackingId: "TEST-TRACKING-12345",
		ShippingCost: &pb.Money{
			CurrencyCode: "USD",
			Units:        9,
			Nanos:        990000000, // $9.99
		},
		ShippingAddress: &pb.Address{
			StreetAddress: "123 Test Street",
			City:          "Test City",
			State:         "CA",
			ZipCode:       90210,
			Country:       "USA",
		},
		Items: []*pb.OrderItem{
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
					CurrencyCode: "USD",
					Units:        29,
					Nanos:        990000000, // $29.99
				},
			},
		},
	}

	total := &pb.Money{
		CurrencyCode: "USD",
		Units:        71,
		Nanos:        970000000, // $71.97 (2*15.99 + 29.99 + 9.99)
	}

	email := "test@example.com"
	userID := "test-user-123"

	return orderResult, total, email, userID
}

func TestOrderService_SaveOrder_Success(t *testing.T) {
	orderService, mockDB := setupTestOrderService()
	defer mockDB.Close()

	orderResult, total, email, userID := createTestOrderResult()

	// Test successful order save
	err := orderService.SaveOrder(orderResult, email, userID, total)
	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}

	// Verify order was saved by retrieving it
	orders, err := orderService.GetUserOrderHistory(userID)
	if err != nil {
		t.Fatalf("Failed to retrieve order history: %v", err)
	}

	if len(orders) != 1 {
		t.Fatalf("Expected 1 order, got %d", len(orders))
	}

	order := orders[0]
	if order.OrderID != orderResult.OrderId {
		t.Errorf("Expected order ID %s, got %s", orderResult.OrderId, order.OrderID)
	}
	if order.UserID != userID {
		t.Errorf("Expected user ID %s, got %s", userID, order.UserID)
	}
	if order.Email != email {
		t.Errorf("Expected email %s, got %s", email, order.Email)
	}
	if order.TotalAmountCurrency != total.CurrencyCode {
		t.Errorf("Expected currency %s, got %s", total.CurrencyCode, order.TotalAmountCurrency)
	}
	if order.TotalAmountUnits != total.Units {
		t.Errorf("Expected units %d, got %d", total.Units, order.TotalAmountUnits)
	}
	if order.Status != "completed" {
		t.Errorf("Expected status 'completed', got %s", order.Status)
	}
}

func TestOrderService_SaveOrder_DatabaseError(t *testing.T) {
	orderService, mockDB := setupTestOrderService()
	defer mockDB.Close()

	// Configure mock to return errors
	mockDB.SetShouldError(true)

	orderResult, total, email, userID := createTestOrderResult()

	// Test error handling
	err := orderService.SaveOrder(orderResult, email, userID, total)
	if err == nil {
		t.Fatal("Expected error, got nil")
	}

	expectedError := "failed to save order to database: mock database error"
	if err.Error() != expectedError {
		t.Errorf("Expected error '%s', got '%s'", expectedError, err.Error())
	}
}

func TestOrderService_GetUserOrderHistory_Success(t *testing.T) {
	orderService, mockDB := setupTestOrderService()
	defer mockDB.Close()

	userID := "test-user-456"

	// Save multiple orders for the same user
	for i := 0; i < 3; i++ {
		orderResult, total, email, _ := createTestOrderResult()
		err := orderService.SaveOrder(orderResult, email, userID, total)
		if err != nil {
			t.Fatalf("Failed to save order %d: %v", i, err)
		}
		time.Sleep(1 * time.Millisecond) // Ensure different timestamps
	}

	// Retrieve order history
	orders, err := orderService.GetUserOrderHistory(userID)
	if err != nil {
		t.Fatalf("Failed to get order history: %v", err)
	}

	if len(orders) != 3 {
		t.Fatalf("Expected 3 orders, got %d", len(orders))
	}

	// Verify all orders belong to the correct user
	for i, order := range orders {
		if order.UserID != userID {
			t.Errorf("Order %d: expected user ID %s, got %s", i, userID, order.UserID)
		}
	}
}

func TestOrderService_GetUserOrderHistory_NoOrders(t *testing.T) {
	orderService, mockDB := setupTestOrderService()
	defer mockDB.Close()

	userID := "nonexistent-user"

	// Get order history for user with no orders
	orders, err := orderService.GetUserOrderHistory(userID)
	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}

	if len(orders) != 0 {
		t.Fatalf("Expected 0 orders, got %d", len(orders))
	}
}

func TestOrderService_GetUserOrderHistory_DatabaseError(t *testing.T) {
	orderService, mockDB := setupTestOrderService()
	defer mockDB.Close()

	// Configure mock to return errors
	mockDB.SetShouldError(true)

	userID := "test-user-789"

	// Test error handling
	_, err := orderService.GetUserOrderHistory(userID)
	if err == nil {
		t.Fatal("Expected error, got nil")
	}

	expectedError := "failed to get user order history: mock database error"
	if err.Error() != expectedError {
		t.Errorf("Expected error '%s', got '%s'", expectedError, err.Error())
	}
}

func TestOrderService_GetOrderDetails_Success(t *testing.T) {
	orderService, mockDB := setupTestOrderService()
	defer mockDB.Close()

	orderResult, total, email, userID := createTestOrderResult()

	// Save an order first
	err := orderService.SaveOrder(orderResult, email, userID, total)
	if err != nil {
		t.Fatalf("Failed to save order: %v", err)
	}

	// Get order details
	_, items, err := orderService.GetOrderDetails(orderResult.OrderId)
	if err != nil {
		t.Fatalf("Failed to get order details: %v", err)
	}

	expectedItemCount := len(orderResult.Items)
	if len(items) != expectedItemCount {
		t.Fatalf("Expected %d items, got %d", expectedItemCount, len(items))
	}

	// Verify item details
	for i, item := range items {
		expectedProductID := orderResult.Items[i].Item.ProductId
		if item.ProductID != expectedProductID {
			t.Errorf("Item %d: expected product ID %s, got %s", i, expectedProductID, item.ProductID)
		}

		expectedQuantity := orderResult.Items[i].Item.Quantity
		if item.Quantity != expectedQuantity {
			t.Errorf("Item %d: expected quantity %d, got %d", i, expectedQuantity, item.Quantity)
		}
	}
}

func TestOrderService_GetOrderDetails_NoItems(t *testing.T) {
	orderService, mockDB := setupTestOrderService()
	defer mockDB.Close()

	orderID := "nonexistent-order"

	// Get details for non-existent order
	_, items, err := orderService.GetOrderDetails(orderID)
	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}

	if len(items) != 0 {
		t.Fatalf("Expected 0 items, got %d", len(items))
	}
}

func TestOrderService_GetOrderDetails_DatabaseError(t *testing.T) {
	orderService, mockDB := setupTestOrderService()
	defer mockDB.Close()

	// Configure mock to return errors
	mockDB.SetShouldError(true)

	orderID := "test-order-error"

	// Test error handling
	_, _, err := orderService.GetOrderDetails(orderID)
	if err == nil {
		t.Fatal("Expected error, got nil")
	}

	expectedError := "failed to get order items: mock database error"
	if err.Error() != expectedError {
		t.Errorf("Expected error '%s', got '%s'", expectedError, err.Error())
	}
}

func TestOrderService_MultipleUsers(t *testing.T) {
	orderService, mockDB := setupTestOrderService()
	defer mockDB.Close()

	// Create orders for different users
	users := []string{"user1", "user2", "user3"}
	orderCounts := []int{2, 1, 3}

	for i, userID := range users {
		for j := 0; j < orderCounts[i]; j++ {
			orderResult, total, email, _ := createTestOrderResult()
			err := orderService.SaveOrder(orderResult, email, userID, total)
			if err != nil {
				t.Fatalf("Failed to save order for user %s: %v", userID, err)
			}
		}
	}

	// Verify each user has the correct number of orders
	for i, userID := range users {
		orders, err := orderService.GetUserOrderHistory(userID)
		if err != nil {
			t.Fatalf("Failed to get order history for user %s: %v", userID, err)
		}

		expectedCount := orderCounts[i]
		if len(orders) != expectedCount {
			t.Errorf("User %s: expected %d orders, got %d", userID, expectedCount, len(orders))
		}
	}
} 