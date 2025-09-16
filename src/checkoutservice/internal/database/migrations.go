package database

import "fmt"

// createTables creates the required database tables and indexes
func (c *Connection) createTables() error {
	// Create order_history table
	orderHistorySQL := `
	CREATE TABLE IF NOT EXISTS order_history (
		order_id VARCHAR(255) PRIMARY KEY,
		user_id VARCHAR(255) NOT NULL,
		email VARCHAR(255),
		total_amount_currency VARCHAR(10),
		total_amount_units BIGINT,
		total_amount_nanos INTEGER,
		shipping_tracking_id VARCHAR(255),
		shipping_address TEXT,
		order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
		status VARCHAR(50) DEFAULT 'completed'
	);`

	if _, err := c.DB.Exec(orderHistorySQL); err != nil {
		return fmt.Errorf("failed to create order_history table: %v", err)
	}

	// Create order_items table
	orderItemsSQL := `
	CREATE TABLE IF NOT EXISTS order_items (
		id SERIAL PRIMARY KEY,
		order_id VARCHAR(255) REFERENCES order_history(order_id) ON DELETE CASCADE,
		product_id VARCHAR(255) NOT NULL,
		quantity INTEGER NOT NULL,
		unit_price_currency VARCHAR(10),
		unit_price_units BIGINT,
		unit_price_nanos INTEGER,
		total_price_currency VARCHAR(10),
		total_price_units BIGINT,
		total_price_nanos INTEGER
	);`

	if _, err := c.DB.Exec(orderItemsSQL); err != nil {
		return fmt.Errorf("failed to create order_items table: %v", err)
	}

	// Create indexes for performance
	indexSQL := `
	CREATE INDEX IF NOT EXISTS idx_order_history_user_id ON order_history(user_id);
	CREATE INDEX IF NOT EXISTS idx_order_history_date ON order_history(order_date);
	CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
	CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);`

	if _, err := c.DB.Exec(indexSQL); err != nil {
		return fmt.Errorf("failed to create indexes: %v", err)
	}

	c.log.Info("Database tables created successfully")
	return nil
} 