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
	"os"
	"testing"
	"time"

	pb "github.com/GoogleCloudPlatform/microservices-demo/src/productcatalogservice/genproto"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

func TestSemanticSearchProducts(t *testing.T) {
	// Skip test if database not available
	if os.Getenv("CLOUDSQL_HOST") == "" {
		t.Skip("Skipping semantic search test: CLOUDSQL_HOST not set")
	}

	// Initialize database connection
	if err := initDatabase(); err != nil {
		t.Fatalf("Failed to initialize database: %v", err)
	}

	// Create service instance
	svc := &productCatalog{}

	tests := []struct {
		name     string
		query    string
		limit    int32
		minCount int // minimum expected results
	}{
		{
			name:     "comfortable seating",
			query:    "comfortable seating",
			limit:    5,
			minCount: 1,
		},
		{
			name:     "kitchen appliances",
			query:    "kitchen appliances",
			limit:    3,
			minCount: 1,
		},
		{
			name:     "winter clothing",
			query:    "winter clothing",
			limit:    3,
			minCount: 1,
		},
		{
			name:     "home decor",
			query:    "home decor",
			limit:    4,
			minCount: 1,
		},
		{
			name:     "office furniture",
			query:    "office furniture",
			limit:    3,
			minCount: 1,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
			defer cancel()

			req := &pb.SemanticSearchRequest{
				Query: tt.query,
				Limit: tt.limit,
			}

			resp, err := svc.SemanticSearchProducts(ctx, req)
			if err != nil {
				t.Fatalf("SemanticSearchProducts(%q) failed: %v", tt.query, err)
			}

			if len(resp.Results) < tt.minCount {
				t.Errorf("SemanticSearchProducts(%q) returned %d results, expected at least %d", 
					tt.query, len(resp.Results), tt.minCount)
			}

			// Log results for manual verification
			t.Logf("Query: %q returned %d products:", tt.query, len(resp.Results))
			for i, product := range resp.Results {
				if i < 3 { // Show first 3 results
					t.Logf("  %d. %s: %s", i+1, product.Name, product.Description[:min(60, len(product.Description))])
				}
			}
		})
	}
}

func TestSemanticVsRegularSearch(t *testing.T) {
	// Skip test if database not available
	if os.Getenv("CLOUDSQL_HOST") == "" {
		t.Skip("Skipping semantic search test: CLOUDSQL_HOST not set")
	}

	// Initialize database connection
	if err := initDatabase(); err != nil {
		t.Fatalf("Failed to initialize database: %v", err)
	}

	// Create service instance
	svc := &productCatalog{}
	
	// Load catalog for regular search
	if err := loadCatalog(&svc.catalog); err != nil {
		t.Fatalf("Failed to load catalog: %v", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	query := "furniture"

	// Regular search
	regReq := &pb.SearchProductsRequest{Query: query}
	regResp, err := svc.SearchProducts(ctx, regReq)
	if err != nil {
		t.Fatalf("SearchProducts failed: %v", err)
	}

	// Semantic search
	semReq := &pb.SemanticSearchRequest{Query: query, Limit: 10}
	semResp, err := svc.SemanticSearchProducts(ctx, semReq)
	if err != nil {
		t.Fatalf("SemanticSearchProducts failed: %v", err)
	}

	t.Logf("Regular search for %q: %d results", query, len(regResp.Results))
	t.Logf("Semantic search for %q: %d results", query, len(semResp.Results))

	// Both should return some results
	if len(regResp.Results) == 0 && len(semResp.Results) == 0 {
		t.Error("Both regular and semantic search returned no results")
	}
}

func TestSemanticSearchEdgeCases(t *testing.T) {
	// Skip test if database not available
	if os.Getenv("CLOUDSQL_HOST") == "" {
		t.Skip("Skipping semantic search test: CLOUDSQL_HOST not set")
	}

	// Initialize database connection
	if err := initDatabase(); err != nil {
		t.Fatalf("Failed to initialize database: %v", err)
	}

	svc := &productCatalog{}
	ctx := context.Background()

	tests := []struct {
		name  string
		query string
		limit int32
	}{
		{
			name:  "empty query",
			query: "",
			limit: 5,
		},
		{
			name:  "very long query",
			query: "this is a very long query that should still work with semantic search functionality",
			limit: 3,
		},
		{
			name:  "zero limit",
			query: "test",
			limit: 0,
		},
		{
			name:  "large limit",
			query: "test",
			limit: 100,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			req := &pb.SemanticSearchRequest{
				Query: tt.query,
				Limit: tt.limit,
			}

			resp, err := svc.SemanticSearchProducts(ctx, req)
			if err != nil {
				t.Errorf("SemanticSearchProducts failed for %s: %v", tt.name, err)
				return
			}

			// Should not crash and should return valid response
			if resp == nil {
				t.Errorf("SemanticSearchProducts returned nil response for %s", tt.name)
			}

			t.Logf("%s: returned %d results", tt.name, len(resp.Results))
		})
	}
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// TestSemanticSearchIntegration tests semantic search via gRPC client
func TestSemanticSearchIntegration(t *testing.T) {
	// Skip if not running integration tests
	if os.Getenv("INTEGRATION_TEST") == "" {
		t.Skip("Skipping integration test: set INTEGRATION_TEST=1 to run")
	}

	t.Log("🚀 Testing ProductCatalogService Semantic Search Integration")

	// Connect to service (assumes port forwarding is active)
	conn, err := grpc.Dial("localhost:3550", grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		t.Fatalf("Failed to connect: %v", err)
	}
	defer conn.Close()

	client := pb.NewProductCatalogServiceClient(conn)
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	// Test 1: List all products first
	t.Log("📋 Test 1: Listing all products...")
	listResp, err := client.ListProducts(ctx, &pb.Empty{})
	if err != nil {
		t.Fatalf("ListProducts failed: %v", err)
	}
	t.Logf("Total products available: %d", len(listResp.Products))
	if len(listResp.Products) == 0 {
		t.Error("Expected products to be available")
	}

	// Test 2: Regular search
	t.Log("🔍 Test 2: Regular search for 'furniture'...")
	searchResp, err := client.SearchProducts(ctx, &pb.SearchProductsRequest{Query: "furniture"})
	if err != nil {
		t.Fatalf("SearchProducts failed: %v", err)
	}
	t.Logf("Regular search found: %d products", len(searchResp.Results))

	// Test 3: Semantic search for comfortable seating
	t.Log("🤖 Test 3: Semantic search for 'comfortable seating'...")
	semResp, err := client.SemanticSearchProducts(ctx, &pb.SemanticSearchRequest{
		Query: "comfortable seating",
		Limit: 5,
	})
	if err != nil {
		t.Fatalf("SemanticSearchProducts failed: %v", err)
	}
	t.Logf("Semantic search found: %d products", len(semResp.Results))
	for i, product := range semResp.Results {
		if i < 3 {
			desc := product.Description
			if len(desc) > 50 {
				desc = desc[:50]
			}
			t.Logf("  %d. %s: %s", i+1, product.Name, desc)
		}
	}

	// Test 4: Semantic search for kitchen items
	t.Log("🍳 Test 4: Semantic search for 'kitchen appliances'...")
	kitchenResp, err := client.SemanticSearchProducts(ctx, &pb.SemanticSearchRequest{
		Query: "kitchen appliances",
		Limit: 3,
	})
	if err != nil {
		t.Fatalf("SemanticSearchProducts failed: %v", err)
	}
	t.Logf("Kitchen search found: %d products", len(kitchenResp.Results))
	for i, product := range kitchenResp.Results {
		t.Logf("  %d. %s", i+1, product.Name)
	}

	// Test 5: Semantic search for winter clothing
	t.Log("🧥 Test 5: Semantic search for 'winter clothing'...")
	winterResp, err := client.SemanticSearchProducts(ctx, &pb.SemanticSearchRequest{
		Query: "winter clothing",
		Limit: 3,
	})
	if err != nil {
		t.Fatalf("SemanticSearchProducts failed: %v", err)
	}
	t.Logf("Winter clothing search found: %d products", len(winterResp.Results))
	for i, product := range winterResp.Results {
		t.Logf("  %d. %s", i+1, product.Name)
	}

	t.Log("✅ All semantic search integration tests completed successfully!")
} 