// Copyright 2024 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"strings"
	"time"

	"cloud.google.com/go/secretmanager/apiv1"
	"cloud.google.com/go/secretmanager/apiv1/secretmanagerpb"
	_ "github.com/jackc/pgx/v5/stdlib"
	pb "github.com/GoogleCloudPlatform/microservices-demo/src/productcatalogservice/genproto"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

var db *sql.DB

// initDatabase initializes the database connection for semantic search
func initDatabase() error {
	if db != nil {
		return nil // Already initialized
	}

	cloudSQLHost := os.Getenv("CLOUDSQL_HOST")
	if cloudSQLHost == "" {
		log.Info("CLOUDSQL_HOST not set, semantic search disabled")
		return nil
	}

	password, err := getDatabasePassword()
	if err != nil {
		return fmt.Errorf("failed to get database password: %v", err)
	}

	connStr := fmt.Sprintf("host=%s port=5432 user=postgres password=%s dbname=products sslmode=disable",
		cloudSQLHost, password)

	db, err = sql.Open("pgx", connStr)
	if err != nil {
		return fmt.Errorf("failed to open database: %v", err)
	}

	// Test connection
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	
	if err := db.PingContext(ctx); err != nil {
		return fmt.Errorf("failed to ping database: %v", err)
	}

	log.Info("Database connection established for semantic search")
	return nil
}

// getDatabasePassword retrieves the database password from Secret Manager
func getDatabasePassword() (string, error) {
	projectID := os.Getenv("PROJECT_ID")
	if projectID == "" {
		projectID = "gke-hack-471804"
	}

	secretName := os.Getenv("CLOUDSQL_SECRET_NAME")
	if secretName == "" {
		secretName = "cloudsql-secret-private"
	}

	ctx := context.Background()
	client, err := secretmanager.NewClient(ctx)
	if err != nil {
		return "", fmt.Errorf("failed to create Secret Manager client: %v", err)
	}
	defer client.Close()

	name := fmt.Sprintf("projects/%s/secrets/%s/versions/latest", projectID, secretName)
	req := &secretmanagerpb.AccessSecretVersionRequest{
		Name: name,
	}

	result, err := client.AccessSecretVersion(ctx, req)
	if err != nil {
		return "", fmt.Errorf("failed to access secret version: %v", err)
	}

	return string(result.Payload.Data), nil
}

// callVertexAIEmbedding calls the Vertex AI embedding service
func callVertexAIEmbedding(text string) ([]float32, error) {
	embeddingServiceURL := os.Getenv("EMBEDDING_SERVICE_URL")
	if embeddingServiceURL == "" {
		embeddingServiceURL = "http://embeddingservice:8081"
	}
	log.Infof("Calling embedding service at %s with text: '%s'", embeddingServiceURL, text)
	
	// Prepare request payload
	payload := map[string]string{
		"text": text,
	}
	payloadBytes, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %v", err)
	}
	
	// Make HTTP request
	log.Infof("Making POST request to %s/embed", embeddingServiceURL)
	resp, err := http.Post(embeddingServiceURL+"/embed", "application/json", strings.NewReader(string(payloadBytes)))
	if err != nil {
		log.Errorf("HTTP request failed: %v", err)
		return nil, fmt.Errorf("failed to call embedding service: %v", err)
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		log.Errorf("Embedding service returned status %d", resp.StatusCode)
		return nil, fmt.Errorf("embedding service returned status %d", resp.StatusCode)
	}
	log.Infof("Embedding service responded with status %d", resp.StatusCode)
	
	// Parse response
	var response struct {
		Embedding  []float32 `json:"embedding"`
		Dimensions int       `json:"dimensions"`
		Model      string    `json:"model"`
	}
	
	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		return nil, fmt.Errorf("failed to decode response: %v", err)
	}
	
	return response.Embedding, nil
}

// generateEmbedding generates embedding using Vertex AI with fallback
func generateEmbedding(text string) []float32 {
	// Try to call Vertex AI service
	if embedding, err := callVertexAIEmbedding(text); err == nil {
		return embedding
	} else {
		log.Warnf("Failed to get Vertex AI embedding, using fallback: %v", err)
	}
	
	// Fallback to hash-based embedding
	words := strings.Fields(strings.ToLower(text))
	embedding := make([]float32, 768)
	
	for i, word := range words {
		if i >= 768 {
			break
		}
		// Simple hash function to generate deterministic values
		hash := 0
		for _, char := range word {
			hash = hash*31 + int(char)
		}
		embedding[i] = float32(hash%1000) / 1000.0
	}
	
	return embedding
}

// semanticSearchProducts performs semantic search on products
func (p *productCatalog) SemanticSearchProducts(ctx context.Context, req *pb.SemanticSearchRequest) (*pb.SearchProductsResponse, error) {
	log.Infof("SemanticSearchProducts called - START")
	
	// Add comprehensive nil checks and logging
	if p == nil {
		log.Errorf("productCatalog receiver is nil!")
		return nil, status.Error(codes.Internal, "productCatalog receiver is nil")
	}
	log.Infof("productCatalog receiver is valid: %p", p)
	
	if ctx == nil {
		log.Errorf("context is nil!")
		return nil, status.Error(codes.InvalidArgument, "context is nil")
	}
	log.Infof("context is valid: %p", ctx)
	
	if req == nil {
		log.Errorf("request is nil!")
		return nil, status.Error(codes.InvalidArgument, "request is nil")
	}
	log.Infof("request is valid: %p, query: '%s', limit: %d", req, req.Query, req.Limit)

	time.Sleep(extraLatency)

	if db == nil {
		// Fallback to regular search if database not available
		log.Warn("Database not available, falling back to regular search")
		searchReq := &pb.SearchProductsRequest{Query: req.Query}
		return p.SearchProducts(ctx, searchReq)
	}
	log.Infof("Database connection is valid: %p", db)

	limit := req.Limit
	if limit <= 0 || limit > 50 {
		limit = 10 // Default limit
	}

	// Generate query embedding using our embedding service
	log.Infof("Generating embedding for query: '%s'", req.Query)
	queryEmbedding, err := callVertexAIEmbedding(req.Query)
	if err != nil {
		log.Errorf("Failed to generate query embedding: %v", err)
		// Fallback to regular search if embedding generation fails
		log.Warn("Falling back to regular search due to embedding failure")
		searchReq := &pb.SearchProductsRequest{Query: req.Query}
		return p.SearchProducts(ctx, searchReq)
	}
	
	// Convert query embedding to PostgreSQL vector format
	queryEmbeddingStr := embeddingToVectorString(queryEmbedding)
	log.Infof("Generated query embedding with %d dimensions", len(queryEmbedding))

	// Hybrid search query with weighted similarity scores using precomputed embeddings
	query := `
		SELECT p.id, p.name, p.description, p.picture, p.price_usd_currency_code, 
			   p.price_usd_units, p.price_usd_nanos, p.categories, p.target_tags, p.use_context,
			   (
				   COALESCE(p.combined_embedding <=> $1::vector, 1.0) * 0.6 +
				   COALESCE(p.target_tags_embedding <=> $1::vector, 1.0) * 0.2 +
				   COALESCE(p.use_context_embedding <=> $1::vector, 1.0) * 0.2
			   ) as similarity_score
		FROM products p
		WHERE p.combined_embedding IS NOT NULL
		ORDER BY similarity_score ASC
		LIMIT $2
	`

	log.Infof("Executing semantic search query with params: query='%s', limit=%d", req.Query, limit)
	log.Infof("Query embedding string (first 100 chars): %s", queryEmbeddingStr[:minInt(100, len(queryEmbeddingStr))])
	log.Infof("Full SQL query: %s", query)
	
	rows, err := db.QueryContext(ctx, query, queryEmbeddingStr, limit)
	if err != nil {
		log.Errorf("Semantic search query failed: %v", err)
		// Fallback to regular search
		searchReq := &pb.SearchProductsRequest{Query: req.Query}
		return p.SearchProducts(ctx, searchReq)
	}
	defer rows.Close()
	log.Infof("Query executed successfully, processing rows...")

	var products []*pb.Product
	rowCount := 0
	for rows.Next() {
		rowCount++
		log.Infof("Processing row %d", rowCount)
		
		var product pb.Product
		product.PriceUsd = &pb.Money{} // Initialize PriceUsd to avoid nil pointer
		log.Infof("PriceUsd initialized: %p", product.PriceUsd)
		
		var categories, targetTags, useContext string
		var similarityScore float64

		log.Infof("About to scan row %d...", rowCount)
		err := rows.Scan(
			&product.Id,
			&product.Name,
			&product.Description,
			&product.Picture,
			&product.PriceUsd.CurrencyCode,
			&product.PriceUsd.Units,
			&product.PriceUsd.Nanos,
			&categories,
			&targetTags,
			&useContext,
			&similarityScore,
		)
		log.Infof("Row %d scan completed", rowCount)
		if err != nil {
			log.Errorf("Failed to scan product row %d: %v", rowCount, err)
			continue
		}
		log.Infof("Row %d scanned successfully - ID: %s, Name: %s", rowCount, product.Id, product.Name)

		// Parse categories
		log.Infof("Parsing categories for row %d: '%s'", rowCount, categories)
		if categories != "" {
			product.Categories = strings.Split(strings.Trim(categories, "{}"), ",")
		}

		// Parse target_tags
		log.Infof("Parsing target_tags for row %d: '%s'", rowCount, targetTags)
		if targetTags != "" {
			product.TargetTags = strings.Split(strings.Trim(targetTags, "{}"), ",")
		}

		// Parse use_context
		log.Infof("Parsing use_context for row %d: '%s'", rowCount, useContext)
		if useContext != "" {
			product.UseContext = strings.Split(strings.Trim(useContext, "{}"), ",")
		}

		log.Infof("About to append product %d to results...", rowCount)
		products = append(products, &product)
		log.Infof("Product %d appended successfully", rowCount)
	}

	log.Infof("Finished processing rows, checking for row errors...")
	if err = rows.Err(); err != nil {
		log.Errorf("Row iteration error: %v", err)
		return nil, status.Errorf(codes.Internal, "database error: %v", err)
	}

	log.Infof("Semantic search completed successfully - found %d products for query: %s", len(products), req.Query)
	return &pb.SearchProductsResponse{Results: products}, nil
}

// populateEmbeddings populates embeddings for existing products
func populateEmbeddings() error {
	if db == nil {
		return fmt.Errorf("database not initialized")
	}

	// Get all products without embeddings
	rows, err := db.Query(`
		SELECT id, name, description, categories, target_tags, use_context 
		FROM products 
		WHERE combined_embedding IS NULL
	`)
	if err != nil {
		return fmt.Errorf("failed to query products: %v", err)
	}
	defer rows.Close()

	updateStmt, err := db.Prepare(`
		UPDATE products 
		SET description_embedding = $1::vector,
			category_embedding = $2::vector,
			combined_embedding = $3::vector,
			target_tags_embedding = $4::vector,
			use_context_embedding = $5::vector
		WHERE id = $6
	`)
	if err != nil {
		return fmt.Errorf("failed to prepare update statement: %v", err)
	}
	defer updateStmt.Close()

	count := 0
	for rows.Next() {
		var id, name, description, categories, targetTags, useContext sql.NullString
		
		err := rows.Scan(&id, &name, &description, &categories, &targetTags, &useContext)
		if err != nil {
			log.Errorf("Failed to scan product: %v", err)
			continue
		}

		// Generate embeddings
		descEmb := generateEmbedding(description.String)
		catEmb := generateEmbedding(categories.String)
		combined := fmt.Sprintf("%s %s %s", name.String, description.String, categories.String)
		combinedEmb := generateEmbedding(combined)
		targetEmb := generateEmbedding(targetTags.String)
		useContextEmb := generateEmbedding(useContext.String)

		// Convert to vector format
		descEmbStr := embeddingToVectorString(descEmb)
		catEmbStr := embeddingToVectorString(catEmb)
		combinedEmbStr := embeddingToVectorString(combinedEmb)
		targetEmbStr := embeddingToVectorString(targetEmb)
		useContextEmbStr := embeddingToVectorString(useContextEmb)

		// Update database
		_, err = updateStmt.Exec(descEmbStr, catEmbStr, combinedEmbStr, targetEmbStr, useContextEmbStr, id.String)
		if err != nil {
			log.Errorf("Failed to update embeddings for product %s: %v", id.String, err)
			continue
		}

		count++
		if count%10 == 0 {
			log.Infof("Updated embeddings for %d products", count)
		}
	}

	log.Infof("Successfully updated embeddings for %d products", count)
	return nil
}

// embeddingToVectorString converts float32 slice to PostgreSQL vector string
func embeddingToVectorString(embedding []float32) string {
	strs := make([]string, len(embedding))
	for i, v := range embedding {
		strs[i] = fmt.Sprintf("%.6f", v)
	}
	return fmt.Sprintf("[%s]", strings.Join(strs, ","))
}

// minInt returns the minimum of two integers
func minInt(a, b int) int {
	if a < b {
		return a
	}
	return b
} 