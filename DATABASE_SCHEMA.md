# AlloyDB Database Schema for Online Boutique

This document outlines all database schemas, tables, and their structures used by the `cartservice` and `productcatalogservice` in the Online Boutique application.

## 🗄️ Database Overview

The Online Boutique application uses **AlloyDB (PostgreSQL)** with two main databases:

1. **`carts`** - Used by `cartservice` for shopping cart data
2. **`products`** - Used by `productcatalogservice` for product catalog data

---

## 📊 Database 1: `carts`

**Used by:** `cartservice`  
**Purpose:** Store shopping cart items for users

### Table: `cart_items`

**Primary Key:** `(userId, productId)`

| Column      | Type    | Constraints                    | Description                |
|-------------|---------|--------------------------------|----------------------------|
| `userId`    | `text`  | NOT NULL, Primary Key (part)  | User identifier            |
| `productId` | `text`  | NOT NULL, Primary Key (part)  | Product identifier         |
| `quantity`  | `int`   | NOT NULL                       | Number of items in cart    |

### Indexes

```sql
-- Primary key index (automatic)
PRIMARY KEY(userId, productId)

-- Additional index for efficient user queries
CREATE INDEX cartItemsByUserId ON cart_items(userId);
```

### SQL Schema Creation

```sql
-- Create database
CREATE DATABASE carts;

-- Create table
CREATE TABLE cart_items (
    userId text, 
    productId text, 
    quantity int, 
    PRIMARY KEY(userId, productId)
);

-- Create index
CREATE INDEX cartItemsByUserId ON cart_items(userId);
```

### Application Queries (cartservice)

```sql
-- Get item quantity for user and product
SELECT quantity FROM cart_items 
WHERE userID='{userId}' AND productID='{productId}';

-- Get all items in user's cart
SELECT productId, quantity FROM cart_items 
WHERE userId = '{userId}';

-- Add/Update item in cart (using UPSERT)
INSERT INTO cart_items (userId, productId, quantity)
VALUES ('{userId}', '{productId}', {totalQuantity})
ON CONFLICT (userId, productId)
DO UPDATE SET quantity = {totalQuantity};

-- Remove all items from user's cart
DELETE FROM cart_items WHERE userID = '{userId}';
```

---

## 📦 Database 2: `products`

**Used by:** `productcatalogservice`  
**Purpose:** Store product catalog data with AI/ML capabilities

### Table: `products` (or `catalog_items` in advanced setups)

**Primary Key:** `id`

| Column                     | Type           | Constraints              | Description                          |
|----------------------------|----------------|--------------------------|--------------------------------------|
| `id`                      | `TEXT`         | PRIMARY KEY              | Unique product identifier            |
| `name`                    | `TEXT`         | NOT NULL                 | Product name                         |
| `description`             | `TEXT`         |                          | Product description                  |
| `picture`                 | `TEXT`         |                          | Product image URL                    |
| `price_usd_currency_code` | `TEXT`         |                          | Currency code (e.g., 'USD')         |
| `price_usd_units`         | `INTEGER`      |                          | Price units (dollars)                |
| `price_usd_nanos`         | `BIGINT`       |                          | Price nanos (fractional cents)      |
| `categories`              | `TEXT`         |                          | Comma-separated categories           |
| `product_embedding`       | `VECTOR(768)`  |                          | AI-generated product embeddings     |
| `embed_model`             | `TEXT`         |                          | Model used for embeddings           |

### Extensions Required

```sql
-- Vector extension for AI/ML embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Google ML integration for embeddings
CREATE EXTENSION IF NOT EXISTS google_ml_integration CASCADE;

-- Grant permissions for embedding function
GRANT EXECUTE ON FUNCTION embedding TO postgres;
```

### SQL Schema Creation

```sql
-- Create database
CREATE DATABASE products;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS google_ml_integration CASCADE;
GRANT EXECUTE ON FUNCTION embedding TO postgres;

-- Create table (basic version)
CREATE TABLE products (
    id TEXT PRIMARY KEY,
    name TEXT,
    description TEXT,
    picture TEXT,
    price_usd_currency_code TEXT,
    price_usd_units INTEGER,
    price_usd_nanos BIGINT,
    categories TEXT
);

-- Advanced version with AI/ML capabilities
CREATE TABLE catalog_items (
    id TEXT PRIMARY KEY,
    name TEXT,
    description TEXT,
    picture TEXT,
    price_usd_currency_code TEXT,
    price_usd_units INTEGER,
    price_usd_nanos BIGINT,
    categories TEXT,
    product_embedding VECTOR(768),
    embed_model TEXT
);

-- Generate embeddings (if using AI features)
UPDATE catalog_items 
SET product_embedding = embedding('textembedding-gecko@003', description), 
    embed_model='textembedding-gecko@003';
```

### Application Queries (productcatalogservice)

```sql
-- Load all products for catalog
SELECT id, name, description, picture, price_usd_currency_code, 
       price_usd_units, price_usd_nanos, categories 
FROM products;

-- Advanced query with embeddings (for AI features)
SELECT id, name, description, picture, price_usd_currency_code, 
       price_usd_units, price_usd_nanos, categories 
FROM catalog_items;
```

---

## 🔧 Environment Variables Configuration

### CartService Configuration

```bash
# Database connection
ALLOYDB_PRIMARY_IP=10.79.0.2
ALLOYDB_DATABASE_NAME=carts
ALLOYDB_TABLE_NAME=cart_items
PROJECT_ID=gke-hack-471804
ALLOYDB_SECRET_NAME=alloydb-secret
```

### ProductCatalogService Configuration

```bash
# Database connection  
PROJECT_ID=gke-hack-471804
REGION=us-central1
ALLOYDB_CLUSTER_NAME=onlineboutique-cluster
ALLOYDB_INSTANCE_NAME=onlineboutique-instance
ALLOYDB_DATABASE_NAME=products
ALLOYDB_TABLE_NAME=products  # or catalog_items for advanced setup
ALLOYDB_SECRET_NAME=alloydb-secret
```

---

## 🏗️ Database Creation Scripts

### Basic Setup (Current Implementation)

From `kustomize/components/alloydb/README.md`:

```bash
# Create carts database and table
psql -h ${ALLOYDB_PRIMARY_IP} -U postgres -c "CREATE DATABASE carts"
psql -h ${ALLOYDB_PRIMARY_IP} -U postgres -d carts -c "CREATE TABLE cart_items (userId text, productId text, quantity int, PRIMARY KEY(userId, productId))"
psql -h ${ALLOYDB_PRIMARY_IP} -U postgres -d carts -c "CREATE INDEX cartItemsByUserId ON cart_items(userId)"

# Products database needs to be created manually
psql -h ${ALLOYDB_PRIMARY_IP} -U postgres -c "CREATE DATABASE products"
psql -h ${ALLOYDB_PRIMARY_IP} -U postgres -d products -c "CREATE TABLE products (id TEXT PRIMARY KEY, name TEXT, description TEXT, picture TEXT, price_usd_currency_code TEXT, price_usd_units INTEGER, price_usd_nanos BIGINT, categories TEXT)"
```

### Advanced Setup (With AI/ML Features)

From `kustomize/components/shopping-assistant/scripts/2_create_populate_alloydb_tables.sh`:

```bash
# Create carts database and table
psql -h ${ALLOYDB_PRIMARY_IP} -U postgres -c "CREATE DATABASE carts"
psql -h ${ALLOYDB_PRIMARY_IP} -U postgres -d carts -c "CREATE TABLE cart_items (userId text, productId text, quantity int, PRIMARY KEY(userId, productId))"
psql -h ${ALLOYDB_PRIMARY_IP} -U postgres -d carts -c "CREATE INDEX cartItemsByUserId ON cart_items(userId)"

# Create products database with AI/ML extensions
psql -h ${ALLOYDB_PRIMARY_IP} -U postgres -c "CREATE DATABASE products"
psql -h ${ALLOYDB_PRIMARY_IP} -U postgres -d products -c "CREATE EXTENSION IF NOT EXISTS vector"
psql -h ${ALLOYDB_PRIMARY_IP} -U postgres -d products -c "CREATE EXTENSION IF NOT EXISTS google_ml_integration CASCADE;"
psql -h ${ALLOYDB_PRIMARY_IP} -U postgres -d products -c "GRANT EXECUTE ON FUNCTION embedding TO postgres;"
psql -h ${ALLOYDB_PRIMARY_IP} -U postgres -d products -c "CREATE TABLE catalog_items (id TEXT PRIMARY KEY, name TEXT, description TEXT, picture TEXT, price_usd_currency_code TEXT, price_usd_units INTEGER, price_usd_nanos BIGINT, categories TEXT, product_embedding VECTOR(768), embed_model TEXT)"

# Populate products (requires generate_sql_from_products.py)
python3 ./generate_sql_from_products.py > products.sql
psql -h ${ALLOYDB_PRIMARY_IP} -U postgres -d products -f products.sql

# Generate AI embeddings
psql -h ${ALLOYDB_PRIMARY_IP} -U postgres -d products -c "UPDATE catalog_items SET product_embedding = embedding('textembedding-gecko@003', description), embed_model='textembedding-gecko@003';"
```

---

## 📝 Data Sources

### CartService Data Flow

1. **Source**: User interactions (add/remove items from cart)
2. **Storage**: AlloyDB `carts.cart_items` table
3. **Queries**: CRUD operations for cart management

### ProductCatalogService Data Flow

1. **Source**: 
   - **Default**: Static `products.json` file (bundled with container)
   - **AlloyDB**: Database table when `ALLOYDB_DATABASE_NAME` is configured
2. **Storage**: AlloyDB `products.products` table (or `products.catalog_items`)
3. **Queries**: Read-only catalog queries

---

## 🔍 Key Findings

1. **CartService** always uses AlloyDB when configured (no fallback)
2. **ProductCatalogService** falls back to `products.json` if AlloyDB is not configured
3. **Database names** are configurable via environment variables
4. **Table schemas** are simple but support the full application functionality
5. **AI/ML features** are available via vector extensions and embeddings
6. **No automatic schema creation** - databases and tables must be created manually

---

## 🚀 Quick Setup Commands

Use the jumpbox VM to create the required databases and tables:

```bash
# Create jumpbox VM
./scripts/vm_jumpbox.sh create

# Create basic schema
./scripts/vm_jumpbox.sh psql postgres -c "CREATE DATABASE carts"
./scripts/vm_jumpbox.sh psql postgres -c "CREATE DATABASE products"

# Query existing tables
./scripts/vm_jumpbox.sh query-dbs
./scripts/vm_jumpbox.sh query-products
./scripts/vm_jumpbox.sh query-carts
``` 