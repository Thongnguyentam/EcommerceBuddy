package database

import (
	"fmt"
	"github.com/GoogleCloudPlatform/microservices-demo/src/checkoutservice/internal/models"
)

const (
	// SQL queries for order operations
	insertOrderSQL = `
	INSERT INTO order_history (
		order_id, user_id, email, total_amount_currency, total_amount_units, total_amount_nanos,
		shipping_tracking_id, shipping_address, order_date, status
	) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), 'completed')`

	insertOrderItemSQL = `
	INSERT INTO order_items (
		order_id, product_id, quantity, unit_price_currency, unit_price_units, unit_price_nanos,
		total_price_currency, total_price_units, total_price_nanos
	) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)`

	getOrdersByUserSQL = `
	SELECT order_id, user_id, email, total_amount_currency, total_amount_units, total_amount_nanos,
		   shipping_tracking_id, shipping_address, order_date, status
	FROM order_history
	WHERE user_id = $1
	ORDER BY order_date DESC`

	getOrderItemsSQL = `
	SELECT id, order_id, product_id, quantity, unit_price_currency, unit_price_units, unit_price_nanos,
		   total_price_currency, total_price_units, total_price_nanos
	FROM order_items
	WHERE order_id = $1`
)

// SaveOrder saves an order and its items to the database
func (c *Connection) SaveOrder(order *models.Order, items []models.OrderItem) error {
	if c.DB == nil {
		return fmt.Errorf("database connection not initialized")
	}

	tx, err := c.DB.Begin()
	if err != nil {
		return fmt.Errorf("failed to begin transaction: %v", err)
	}
	defer tx.Rollback()

	// Insert order
	_, err = tx.Exec(insertOrderSQL,
		order.OrderID,
		order.UserID,
		order.Email,
		order.TotalAmountCurrency,
		order.TotalAmountUnits,
		order.TotalAmountNanos,
		order.ShippingTrackingID,
		order.ShippingAddress,
	)
	if err != nil {
		return fmt.Errorf("failed to insert order: %v", err)
	}

	// Insert order items
	for _, item := range items {
		_, err = tx.Exec(insertOrderItemSQL,
			item.OrderID,
			item.ProductID,
			item.Quantity,
			item.UnitPriceCurrency,
			item.UnitPriceUnits,
			item.UnitPriceNanos,
			item.TotalPriceCurrency,
			item.TotalPriceUnits,
			item.TotalPriceNanos,
		)
		if err != nil {
			return fmt.Errorf("failed to insert order item: %v", err)
		}
	}

	return tx.Commit()
}

// GetOrdersByUser retrieves all orders for a specific user
func (c *Connection) GetOrdersByUser(userID string) ([]models.Order, error) {
	if c.DB == nil {
		return nil, fmt.Errorf("database connection not initialized")
	}

	rows, err := c.DB.Query(getOrdersByUserSQL, userID)
	if err != nil {
		return nil, fmt.Errorf("failed to query orders: %v", err)
	}
	defer rows.Close()

	var orders []models.Order
	for rows.Next() {
		var order models.Order
		err := rows.Scan(
			&order.OrderID,
			&order.UserID,
			&order.Email,
			&order.TotalAmountCurrency,
			&order.TotalAmountUnits,
			&order.TotalAmountNanos,
			&order.ShippingTrackingID,
			&order.ShippingAddress,
			&order.OrderDate,
			&order.Status,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan order: %v", err)
		}
		orders = append(orders, order)
	}

	if err = rows.Err(); err != nil {
		return nil, fmt.Errorf("row iteration error: %v", err)
	}

	return orders, nil
}

// GetOrderItems retrieves all items for a specific order
func (c *Connection) GetOrderItems(orderID string) ([]models.OrderItem, error) {
	if c.DB == nil {
		return nil, fmt.Errorf("database connection not initialized")
	}

	rows, err := c.DB.Query(getOrderItemsSQL, orderID)
	if err != nil {
		return nil, fmt.Errorf("failed to query order items: %v", err)
	}
	defer rows.Close()

	var items []models.OrderItem
	for rows.Next() {
		var item models.OrderItem
		err := rows.Scan(
			&item.ID,
			&item.OrderID,
			&item.ProductID,
			&item.Quantity,
			&item.UnitPriceCurrency,
			&item.UnitPriceUnits,
			&item.UnitPriceNanos,
			&item.TotalPriceCurrency,
			&item.TotalPriceUnits,
			&item.TotalPriceNanos,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan order item: %v", err)
		}
		items = append(items, item)
	}

	if err = rows.Err(); err != nil {
		return nil, fmt.Errorf("row iteration error: %v", err)
	}

	return items, nil
} 