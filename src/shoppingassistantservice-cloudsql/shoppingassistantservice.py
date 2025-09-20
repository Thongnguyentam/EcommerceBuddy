#!/usr/bin/python
#
# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import psycopg2
from google.cloud import secretmanager_v1
from urllib.parse import unquote
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from flask import Flask, request
import logging

# Set the Google API key for langchain
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment variables
PROJECT_ID = os.environ.get("PROJECT_ID", "gke-hack-471804")
REGION = os.environ.get("REGION", "us-central1")
CLOUDSQL_HOST = os.environ.get("CLOUDSQL_HOST", "10.103.0.3")
CLOUDSQL_DATABASE_NAME = os.environ.get("CLOUDSQL_DATABASE_NAME", "products")
CLOUDSQL_TABLE_NAME = os.environ.get("CLOUDSQL_TABLE_NAME", "products")
CLOUDSQL_SECRET_NAME = os.environ.get("CLOUDSQL_SECRET_NAME", "cloudsql-secret-private")

def get_database_password():
    """Get database password from Google Secret Manager."""
    try:
        client = secretmanager_v1.SecretManagerServiceClient()
        name = f"projects/{PROJECT_ID}/secrets/{CLOUDSQL_SECRET_NAME}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        password = response.payload.data.decode("UTF-8").strip()
        logger.info("Successfully retrieved database password from Secret Manager")
        return password
    except Exception as e:
        logger.error(f"Failed to get database password: {e}")
        raise Exception(f"Unable to retrieve database password from Secret Manager: {e}")

def get_database_connection():
    """Get PostgreSQL database connection."""
    try:
        password = get_database_password()
        conn = psycopg2.connect(
            host=CLOUDSQL_HOST,
            database=CLOUDSQL_DATABASE_NAME,
            user="postgres",
            password=password,
            port=5432
        )
        logger.info(f"Successfully connected to Cloud SQL: {CLOUDSQL_HOST}:{CLOUDSQL_DATABASE_NAME}")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return None

def search_products(query, limit=5):
    """Search for products in the database based on query."""
    try:
        conn = get_database_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        
        # Simple text search on name and description
        search_sql = """
        SELECT id, name, description, price_usd_units, price_usd_nanos, price_usd_currency_code, categories
        FROM products 
        WHERE LOWER(name) LIKE LOWER(%s) 
           OR LOWER(description) LIKE LOWER(%s)
           OR LOWER(categories) LIKE LOWER(%s)
        LIMIT %s
        """
        
        search_term = f"%{query}%"
        cursor.execute(search_sql, (search_term, search_term, search_term, limit))
        results = cursor.fetchall()
        
        products = []
        for row in results:
            product = {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "price_units": row[3],
                "price_nanos": row[4],
                "price_currency": row[5],
                "categories": row[6]
            }
            products.append(product)
        
        cursor.close()
        conn.close()
        
        logger.info(f"Found {len(products)} products for query: {query}")
        return products
        
    except Exception as e:
        logger.error(f"Failed to search products: {e}")
        return []

def create_app():
    app = Flask(__name__)

    @app.route("/", methods=['POST'])
    def talkToGemini():
        logger.info("Beginning AI recommendation call")
        
        try:
            request_data = request.json
            prompt = request_data.get('message', '')
            image_data = request_data.get('image')
            
            if not prompt:
                return {"content": "Please provide a query for product recommendations."}, 400
            
            prompt = unquote(prompt)
            logger.info(f"Processing query: {prompt[:100]}...")

            # Step 1 – Handle image if provided (simplified version)
            room_description = ""
            if image_data:
                try:
                    llm_vision = ChatGoogleGenerativeAI(
                        model="gemini-1.5-flash",
                        google_api_key=GOOGLE_API_KEY
                    )
                    message = HumanMessage(
                        content=[
                            {
                                "type": "text",
                                "text": "You are a professional interior designer, give me a detailed description of the style of the room in this image",
                            },
                            {"type": "image_url", "image_url": image_data},
                        ]
                    )
                    response = llm_vision.invoke([message])
                    room_description = response.content
                    logger.info("Successfully analyzed room image")
                except Exception as e:
                    logger.warning(f"Image analysis failed: {e}")
                    room_description = "modern interior style"

            # Step 2 – Search products in Cloud SQL database
            # Extract key terms from the query for product search
            search_terms = []
            furniture_keywords = ['sofa', 'chair', 'table', 'lamp', 'bed', 'desk', 'shelf', 'cabinet']
            style_keywords = ['modern', 'rustic', 'minimalist', 'industrial', 'vintage']
            room_keywords = ['living room', 'bedroom', 'kitchen', 'bathroom', 'office']
            
            query_lower = prompt.lower()
            for keyword in furniture_keywords + style_keywords + room_keywords:
                if keyword in query_lower:
                    search_terms.append(keyword)
            
            # If no specific terms found, use the full prompt
            if not search_terms:
                search_terms = [prompt]
            
            # Search for relevant products
            all_products = []
            for term in search_terms[:3]:  # Limit to first 3 terms
                products = search_products(term, limit=3)
                all_products.extend(products)
            
            # Remove duplicates while preserving order
            seen_ids = set()
            unique_products = []
            for product in all_products:
                if product['id'] not in seen_ids:
                    seen_ids.add(product['id'])
                    unique_products.append(product)
                    if len(unique_products) >= 5:  # Limit to 5 products
                        break
            
            logger.info(f"Found {len(unique_products)} relevant products")

            # Step 3 – Generate AI response with Gemini
            llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=GOOGLE_API_KEY
            )
            
            # Prepare product information for the prompt
            product_info = ""
            product_ids = []
            for product in unique_products:
                price = f"${product['price_units']}.{product['price_nanos']:02d}" if product['price_units'] else "Price available"
                product_info += f"- {product['name']} [{product['id']}]: {product['description']} - {price}\n"
                product_ids.append(product['id'])
            
            design_prompt = f"""You are an interior designer that works for Online Boutique. You are tasked with providing recommendations to a customer on what they should add to a given room from our catalog.

Customer request: {prompt}

{f"Room analysis: {room_description}" if room_description else ""}

Available products from our catalog:
{product_info}

Please provide your recommendations based on the customer's request. Focus on the most relevant products from our catalog. At the end of your response, add a list of the product IDs for the top 3 recommendations in the following format: [<product_id>], [<product_id>], [<product_id>]

If no products seem relevant to the customer's request, please say so instead of making inappropriate recommendations."""

            logger.info("Generating AI response...")
            design_response = llm.invoke(design_prompt)

            response_data = {'content': design_response.content}
            logger.info("Successfully generated AI recommendations")
            return response_data

        except Exception as e:
            logger.error(f"Error in AI recommendation: {e}")
            return {"content": f"Sorry, I encountered an error while processing your request: {str(e)}"}, 500

    @app.route("/health", methods=['GET'])
    def health_check():
        """Health check endpoint."""
        try:
            # Test database connection
            conn = get_database_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                conn.close()
                db_status = "healthy"
            else:
                db_status = "unhealthy"
            
            return {
                "status": "healthy" if db_status == "healthy" else "unhealthy",
                "service": "shopping-assistant-cloudsql",
                "database": db_status,
                "host": CLOUDSQL_HOST,
                "database_name": CLOUDSQL_DATABASE_NAME
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "service": "shopping-assistant-cloudsql",
                "error": str(e)
            }, 500

    return app

if __name__ == "__main__":
    # Create an instance of flask server when called directly
    app = create_app()
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True) 