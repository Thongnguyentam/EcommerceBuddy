# Review Service Integration Guide

## Overview
This document describes the integration of the Review Service into the Frontend microservice, enabling users to view, create, update, and delete product reviews.

## Changes Made

### 1. Generated Protobuf Files
- **Location**: `src/frontend/genproto/`
- **Files**: 
  - `review.proto` - Review service protocol definition
  - `review.pb.go` - Generated Go structs for review messages
  - `review_grpc.pb.go` - Generated Go gRPC client code

### 2. Frontend Server Configuration
- **File**: `src/frontend/main.go`
- **Changes**:
  - Added `reviewSvcAddr` and `reviewSvcConn` fields to `frontendServer` struct
  - Added environment variable mapping for `REVIEW_SERVICE_ADDR`
  - Added gRPC connection initialization for review service
  - Added new HTTP routes for review operations:
    - `POST /review` - Create new review
    - `POST /review/{id}` - Update existing review
    - `POST /review/{id}/delete` - Delete review

### 3. Review Service RPC Methods
- **File**: `src/frontend/rpc.go`
- **New Methods**:
  - `getProductReviews()` - Fetch reviews for a specific product
  - `getProductReviewSummary()` - Get review statistics (average rating, total count)
  - `createReview()` - Create a new review
  - `updateReview()` - Update an existing review
  - `deleteReview()` - Delete a review
  - `getUserReviews()` - Get all reviews by a specific user

### 4. HTTP Handlers
- **File**: `src/frontend/handlers.go`
- **New Handlers**:
  - `createReviewHandler()` - Handle review creation form submission
  - `updateReviewHandler()` - Handle review update form submission
  - `deleteReviewHandler()` - Handle review deletion
- **Updated Handler**:
  - `productHandler()` - Enhanced to fetch and display review data

### 5. Template Helper Functions
- **File**: `src/frontend/handlers.go`
- **New Functions**:
  - `iterate(count)` - Generate array for star rating display
  - `sub(a, b)` - Subtract function for template math
  - `formatTimestamp(timestamp)` - Format Unix timestamp to readable date

### 6. UI Template Updates
- **File**: `src/frontend/templates/product.html`
- **New Sections**:
  - **Review Summary**: Shows average rating and total review count
  - **Review Form**: 
    - Create new review form (for users who haven't reviewed)
    - Edit existing review form (for users who have already reviewed)
    - Delete review button
  - **Reviews List**: Display all product reviews with ratings and timestamps

### 7. CSS Styling
- **File**: `src/frontend/static/styles/styles.css`
- **New Styles**:
  - `.reviews-section` - Main review container styling
  - `.review-summary` - Review statistics display
  - `.star-rating` - Star rating display (filled and empty stars)
  - `.review-form` - Form styling for review creation/editing
  - `.review-item` - Individual review display
  - Utility classes for spacing and layout

## Features Implemented

### 1. View Reviews
- Display all reviews for a product
- Show review summary with average rating and total count
- Star rating visualization
- Formatted timestamps

### 2. Create Reviews
- Form to submit new reviews
- Rating selection (1-5 stars)
- Text review input
- Validation for required fields

### 3. Update Reviews
- Edit existing user reviews
- Pre-populated form with current values
- Same validation as creation

### 4. Delete Reviews
- Delete button with confirmation dialog
- Secure deletion with review ID verification

### 5. User Experience
- Users can only edit/delete their own reviews
- Prevents duplicate reviews from same user
- Responsive design with proper styling
- Error handling and user feedback

## Environment Variables

Add this environment variable to your frontend deployment:

```bash
REVIEW_SERVICE_ADDR=localhost:8080  # or your review service address
```

## API Integration

The frontend now communicates with the Review Service via gRPC using these endpoints:

- `CreateReview` - Create new reviews
- `GetProductReviews` - Fetch reviews for display
- `GetProductReviewSummary` - Get aggregated review data
- `GetUserReviews` - Check if user has existing reviews
- `UpdateReview` - Modify existing reviews
- `DeleteReview` - Remove reviews

## Usage

1. **Start the Review Service** on the configured port (default: 8080)
2. **Set the environment variable** `REVIEW_SERVICE_ADDR` to point to your review service
3. **Start the Frontend Service** - it will automatically connect to the review service
4. **Navigate to any product page** - you'll see the new review section at the bottom

## Security Considerations

- Reviews are associated with session IDs (user identification)
- Users can only modify their own reviews
- Input validation prevents malicious data
- Proper error handling prevents information leakage

## Testing

You can test the integration by:

1. Running the review service integration test: `python src/reviewservice/test_integration.py`
2. Accessing product pages in the frontend
3. Creating, updating, and deleting reviews through the UI
4. Verifying data persistence in the review service database

## Future Enhancements

Potential improvements could include:

- Review helpfulness voting
- Review moderation features
- Image uploads for reviews
- Review filtering and sorting
- Pagination for large review sets
- Real-time review updates 