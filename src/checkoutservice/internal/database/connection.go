package database

import (
	"context"
	"database/sql"
	"fmt"
	"os"

	secretmanager "cloud.google.com/go/secretmanager/apiv1"
	"cloud.google.com/go/secretmanager/apiv1/secretmanagerpb"
	"github.com/sirupsen/logrus"
	_ "github.com/lib/pq"
)

// Config holds database configuration
type Config struct {
	Host         string
	DatabaseName string
	SecretName   string
	ProjectID    string
}

// Connection represents a database connection
type Connection struct {
	DB  *sql.DB
	log *logrus.Logger
}

// NewConnection creates a new database connection
func NewConnection(log *logrus.Logger) *Connection {
	return &Connection{
		log: log,
	}
}

// Connect initializes the database connection
func (c *Connection) Connect() error {
	config, err := c.loadConfig()
	if err != nil {
		return err
	}

	if config.Host == "" {
		return fmt.Errorf("CLOUDSQL_HOST not set - database connection is required")
	}

	c.log.Info("Initializing Cloud SQL connection for order history...")

	// Get database password from Secret Manager
	password, err := c.getSecretPayload(config.ProjectID, config.SecretName, "latest")
	if err != nil {
		return fmt.Errorf("failed to get database password: %v", err)
	}

	// Create connection string
	dsn := fmt.Sprintf("host=%s user=postgres password=%s dbname=%s sslmode=disable",
		config.Host, password, config.DatabaseName)

	// Open database connection
	db, err := sql.Open("postgres", dsn)
	if err != nil {
		return fmt.Errorf("failed to open database connection: %v", err)
	}

	// Test connection
	if err := db.Ping(); err != nil {
		db.Close()
		return fmt.Errorf("failed to ping database: %v", err)
	}

	c.DB = db
	c.log.Info("Successfully connected to Cloud SQL for order history")

	// Create tables if they don't exist
	if err := c.createTables(); err != nil {
		c.DB.Close()
		c.DB = nil
		return fmt.Errorf("failed to create tables: %v", err)
	}

	return nil
}

// Close closes the database connection
func (c *Connection) Close() error {
	if c.DB != nil {
		return c.DB.Close()
	}
	return nil
}

// loadConfig loads database configuration from environment variables
func (c *Connection) loadConfig() (*Config, error) {
	config := &Config{
		Host:         os.Getenv("CLOUDSQL_HOST"),
		DatabaseName: os.Getenv("ALLOYDB_DATABASE_NAME"),
		SecretName:   os.Getenv("ALLOYDB_SECRET_NAME"),
		ProjectID:    os.Getenv("PROJECT_ID"),
	}

	if config.Host != "" && (config.ProjectID == "" || config.DatabaseName == "" || config.SecretName == "") {
		return nil, fmt.Errorf("missing required environment variables: PROJECT_ID, ALLOYDB_DATABASE_NAME, ALLOYDB_SECRET_NAME")
	}

	return config, nil
}

// getSecretPayload retrieves secret from Google Secret Manager
func (c *Connection) getSecretPayload(projectID, secretID, version string) (string, error) {
	c.log.Infof("Attempting to connect to Secret Manager for project=%s, secret=%s", projectID, secretID)
	
	ctx := context.Background()
	client, err := secretmanager.NewClient(ctx)
	if err != nil {
		c.log.Errorf("Failed to create Secret Manager client: %v", err)
		return "", err
	}
	defer client.Close()

	name := fmt.Sprintf("projects/%s/secrets/%s/versions/%s", projectID, secretID, version)
	c.log.Infof("Accessing secret: %s", name)
	
	req := &secretmanagerpb.AccessSecretVersionRequest{Name: name}

	result, err := client.AccessSecretVersion(ctx, req)
	if err != nil {
		c.log.Errorf("Failed to access secret version: %v", err)
		return "", err
	}

	c.log.Info("Successfully retrieved secret from Secret Manager")
	return string(result.Payload.Data), nil
} 