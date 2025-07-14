# API Documentation

Base URL: `https://api.example.com/v1`

## Authentication

Include bearer token in headers:
```
Authorization: Bearer <token>
```

## Endpoints

### POST /auth/login
Login and get access token.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password"
}
```

**Response:**
```json
{
  "token": "...",
  "user": { ... }
}
```

### GET /users
Get list of users.

**Query params:**
- `page` - Page number
- `limit` - Items per page

### GET /users/:id
Get user by ID.

### POST /users
Create new user.

### PUT /users/:id
Update user.

### DELETE /users/:id
Delete user.

## Error Codes

- `400` - Bad Request
- `401` - Unauthorized
- `404` - Not Found
- `500` - Server Error

---
Last updated: [Date]