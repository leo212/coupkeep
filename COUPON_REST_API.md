# Coupon REST API Documentation

## Overview

The Coupon Management REST API provides programmatic access to all coupon operations. This API is independent of the WhatsApp interface and can be used to build web or mobile applications.

## Authentication

All API requests require an API key for authentication.

### Getting Your API Key

1. Send `/web` command to the Coupi WhatsApp bot
2. You'll receive a URL like: `https://coupi.roymam.com/{YOUR_API_KEY}`
3. Extract the API key from the URL

### Using the API Key

Include the API key in the `X-Api-Key` header with every request:

```
X-Api-Key: your-api-key-here
```

## Base URL

```
https://coupi.roymam.com/api
```

## Endpoints

### 1. List Coupons

Get all coupons for the authenticated user.

**Endpoint:** `GET /api/coupons`

**Query Parameters:**
- `expiring_soon` (optional): `true` to filter coupons expiring within 30 days
- `include_shared` (optional): `true` (default) to include shared coupons

**Response:**
```json
{
  "coupons": [
    {
      "coupon_id": "uuid",
      "store": "Store Name",
      "coupon_code": "CODE123",
      "expiration_date": "2026-12-31T23:59:59",
      "discount_value": "20%",
      "value": "$50",
      "category": "food_and_drinks",
      "coupon_status": "unused",
      "misc": "Additional info"
    }
  ],
  "shared_coupons": [...]
}
```

### 2. Create Coupon

Create a new coupon from text or image.

**Endpoint:** `POST /api/coupons`

**Request Body (Text):**
```json
{
  "text": "Pizza Hut coupon: 20% off, expires 12/31/2026, code: PIZZA20"
}
```

**Request Body (Image):**
```json
{
  "image": "base64-encoded-image-data"
}
```

**Response:**
```json
{
  "status": "created",
  "coupon": {
    "coupon_id": "uuid",
    "store": "Pizza Hut",
    "coupon_code": "PIZZA20",
    "expiration_date": "2026-12-31T23:59:59",
    "discount_value": "20%",
    "category": "food_and_drinks",
    "valid": true
  }
}
```

**Status Codes:**
- `201`: Coupon created successfully
- `200`: Duplicate coupon found
- `400`: Invalid request

### 3. Get Coupon

Get details of a specific coupon.

**Endpoint:** `GET /api/coupons/{coupon_id}`

**Response:**
```json
{
  "coupon_id": "uuid",
  "store": "Store Name",
  "coupon_code": "CODE123",
  "expiration_date": "2026-12-31T23:59:59",
  "discount_value": "20%",
  "coupon_status": "unused"
}
```

**Status Codes:**
- `200`: Success
- `404`: Coupon not found

### 4. Update Coupon

Update coupon details using natural language.

**Endpoint:** `PUT /api/coupons/{coupon_id}`

**Request Body:**
```json
{
  "text": "Change expiration date to 1/15/2027"
}
```

**Response:**
```json
{
  "status": "updated",
  "coupon": {
    "coupon_id": "uuid",
    "expiration_date": "2027-01-15T23:59:59",
    ...
  }
}
```

**Status Codes:**
- `200`: Updated successfully
- `400`: Invalid update request
- `404`: Coupon not found

### 5. Delete Coupon

Delete a coupon.

**Endpoint:** `DELETE /api/coupons/{coupon_id}`

**Response:**
```json
{
  "status": "deleted"
}
```

**Status Codes:**
- `200`: Deleted successfully
- `404`: Coupon not found

### 6. Search Coupons

Search coupons using natural language.

**Endpoint:** `POST /api/coupons/search`

**Request Body:**
```json
{
  "query": "pizza"
}
```

**Response:**
```json
{
  "coupons": [
    {
      "coupon_id": "uuid",
      "store": "Pizza Hut",
      ...
    }
  ]
}
```

### 7. Mark Coupon as Used

Mark a coupon as used.

**Endpoint:** `POST /api/coupons/{coupon_id}/mark-used`

**Response:**
```json
{
  "status": "marked_used"
}
```

**Status Codes:**
- `200`: Marked successfully
- `404`: Coupon not found

### 8. Unmark Coupon as Used

Unmark a coupon (mark as unused).

**Endpoint:** `POST /api/coupons/{coupon_id}/unmark-used`

**Response:**
```json
{
  "status": "unmarked"
}
```

**Status Codes:**
- `200`: Unmarked successfully
- `404`: Coupon not found

### 9. Share Coupon

Generate a sharing token for a coupon.

**Endpoint:** `POST /api/coupons/{coupon_id}/share`

**Response:**
```json
{
  "status": "shared",
  "token": "ABC12345"
}
```

**Status Codes:**
- `200`: Token generated successfully
- `404`: Coupon not found

### 10. Add Shared Coupon

Add a shared coupon to your collection using a token.

**Endpoint:** `POST /api/coupons/shared`

**Request Body:**
```json
{
  "token": "ABC12345"
}
```

**Response:**
```json
{
  "status": "added",
  "coupon": {
    "coupon_id": "uuid",
    "store": "Store Name",
    ...
  }
}
```

**Status Codes:**
- `200`: Added successfully
- `404`: Token not found or expired

## Error Responses

All error responses follow this format:

```json
{
  "error": "Error message description"
}
```

**Common Status Codes:**
- `400`: Bad Request - Invalid input
- `401`: Unauthorized - Missing API key
- `403`: Forbidden - Invalid API key
- `404`: Not Found - Resource doesn't exist
- `500`: Internal Server Error

## Example Usage

### cURL Example

```bash
# List all coupons
curl -X GET "https://your-lambda-url.amazonaws.com/api/coupons" \
  -H "X-Api-Key: your-api-key-here"

# Create a coupon from text
curl -X POST "https://your-lambda-url.amazonaws.com/api/coupons" \
  -H "X-Api-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"text": "Starbucks 50% off, expires 12/31/2026"}'

# Search coupons
curl -X POST "https://your-lambda-url.amazonaws.com/api/coupons/search" \
  -H "X-Api-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"query": "coffee"}'

# Mark coupon as used
curl -X POST "https://your-lambda-url.amazonaws.com/api/coupons/{coupon-id}/mark-used" \
  -H "X-Api-Key: your-api-key-here"
```

### JavaScript Example

```javascript
const API_KEY = 'your-api-key-here';
const BASE_URL = 'https://your-lambda-url.amazonaws.com/api';

// List coupons
async function listCoupons() {
  const response = await fetch(`${BASE_URL}/coupons`, {
    headers: {
      'X-Api-Key': API_KEY
    }
  });
  return await response.json();
}

// Create coupon
async function createCoupon(text) {
  const response = await fetch(`${BASE_URL}/coupons`, {
    method: 'POST',
    headers: {
      'X-Api-Key': API_KEY,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ text })
  });
  return await response.json();
}

// Search coupons
async function searchCoupons(query) {
  const response = await fetch(`${BASE_URL}/coupons/search`, {
    method: 'POST',
    headers: {
      'X-Api-Key': API_KEY,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ query })
  });
  return await response.json();
}
```

## Security Notes

1. **Keep your API key secret** - Never share it publicly or commit it to version control
2. **API keys are user-specific** - Each user gets their own key via the `/web` command
3. **No user impersonation** - The API key is validated server-side and tied to a specific user
4. **Regenerate if compromised** - Send `/web` again to get a new API key (old one will be invalidated)

## Rate Limiting

Currently, there are no rate limits enforced. This may change in future versions.

## Support

For issues or questions, contact the bot via WhatsApp or refer to the main README.md file.
