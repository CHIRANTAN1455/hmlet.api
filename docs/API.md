# API Reference — Sample Requests and Responses

Every response below was **captured from a live server**, not written by hand.
Regenerate with the server running on port 8000 after `python manage.py seed_demo`.

Base URL: `http://localhost:8000/api`

JWTs are truncated for readability. Long list responses are trimmed, marked
where that happened.

An interactive version is at `/api/docs/` (Swagger UI) with the server running.

---

## Authentication

### Register a staff user

Open endpoint. Returns the user together with a ready-to-use token pair, so no follow-up call to `/login` is needed.

```http
POST /auth/register
```

**Request**

```json
{
  "email": "reviewer@hmlet.com",
  "full_name": "API Reviewer",
  "password": "ReviewPass123!"
}
```

**Response — `400`**

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request payload failed validation.",
    "details": {
      "email": [
        "user with this email already exists."
      ]
    }
  }
}
```

### Log in

Returns the user alongside the tokens, so the client need not decode the JWT to know who signed in.

```http
POST /auth/login
```

**Request**

```json
{
  "email": "demo@hmlet.com",
  "password": "DemoPass123!"
}
```

**Response — `200`**

```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ...<truncated>",
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ...<truncated>",
  "user": {
    "id": 6,
    "email": "demo@hmlet.com",
    "full_name": "Demo Staff",
    "is_staff": true,
    "created_at": "2026-08-20T09:08:31.396190Z"
  }
}
```

### Log in with wrong credentials

```http
POST /auth/login
```

**Request**

```json
{
  "email": "demo@hmlet.com",
  "password": "wrong-password"
}
```

**Response — `401`**

```json
{
  "error": {
    "code": "authentication_failed",
    "message": "No active account found with the given credentials"
  }
}
```

### Current user

```http
GET /auth/me
```

**Response — `200`**

```json
{
  "id": 6,
  "email": "demo@hmlet.com",
  "full_name": "Demo Staff",
  "is_staff": true,
  "created_at": "2026-08-20T09:08:31.396190Z"
}
```

### Request without a token

Every endpoint except register, login and the docs requires `Authorization: Bearer <access_token>`.

```http
GET /auth/me
```

**Response — `401`**

```json
{
  "error": {
    "code": "not_authenticated",
    "message": "Authentication credentials were not provided."
  }
}
```


---

## Properties

### Create a property

`created_by` is taken from the token, never from the request body.

```http
POST /properties
```

**Request**

```json
{
  "name": "Bugis Garden Apartments",
  "address": "3 Liang Seah Street, Singapore 189031"
}
```

**Response — `201`**

```json
{
  "id": 10,
  "name": "Bugis Garden Apartments",
  "address": "3 Liang Seah Street, Singapore 189031",
  "unit_count": 0,
  "available_unit_count": 0,
  "created_by": "demo@hmlet.com",
  "created_at": "2026-08-20T09:08:32.064099Z",
  "updated_at": "2026-08-20T09:08:32.064117Z"
}
```

### List properties

Unit counts are annotated in SQL, so the query count stays flat as the portfolio grows.

```http
GET /properties
```

**Response — `200`**

```json
{
  "count": 4,
  "total_pages": 1,
  "page": 1,
  "page_size": 20,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 10,
      "name": "Bugis Garden Apartments",
      "address": "3 Liang Seah Street, Singapore 189031",
      "unit_count": 0,
      "available_unit_count": 0,
      "created_by": "demo@hmlet.com",
      "created_at": "2026-08-20T09:08:32.064099Z",
      "updated_at": "2026-08-20T09:08:32.064117Z"
    },
    {
      "id": 9,
      "name": "Joo Chiat Lofts",
      "address": "45 Joo Chiat Place, Singapore 427756",
      "unit_count": 2,
      "available_unit_count": 2,
      "created_by": "demo@hmlet.com",
      "created_at": "2026-08-20T09:08:31.526409Z",
      "updated_at": "2026-08-20T09:08:31.526413Z"
    },
    "... 2 more omitted for brevity"
  ]
}
```

### Retrieve a property with its units

The detail view embeds the full unit list; the list view deliberately does not, since that payload would grow with the portfolio.

```http
GET /properties/9
```

**Response — `200`**

```json
{
  "id": 9,
  "name": "Joo Chiat Lofts",
  "address": "45 Joo Chiat Place, Singapore 427756",
  "unit_count": 2,
  "available_unit_count": 2,
  "created_by": "demo@hmlet.com",
  "created_at": "2026-08-20T09:08:31.526409Z",
  "updated_at": "2026-08-20T09:08:31.526413Z",
  "units": [
    {
      "id": 43,
      "unit_number": "A-01",
      "monthly_rent": "1950.00",
      "status": "available"
    },
    {
      "id": 44,
      "unit_number": "A-02",
      "monthly_rent": "2050.00",
      "status": "available"
    }
  ]
}
```

### Property that does not exist

```http
GET /properties/9999
```

**Response — `404`**

```json
{
  "error": {
    "code": "not_found",
    "message": "The requested resource does not exist."
  }
}
```


---

## Units

### Add a unit to a property

The parent property comes from the URL, not the body, so a caller cannot create a unit under a property they did not address. `status` is not accepted — it is derived from contracts.

```http
POST /properties/10/units
```

**Request**

```json
{
  "unit_number": "07-03",
  "monthly_rent": "3150.00"
}
```

**Response — `201`**

```json
{
  "id": 45,
  "property_id": 10,
  "property_name": "Bugis Garden Apartments",
  "unit_number": "07-03",
  "monthly_rent": "3150.00",
  "status": "available",
  "created_at": "2026-08-20T09:08:32.152212Z",
  "updated_at": "2026-08-20T09:08:32.152220Z"
}
```

### Duplicate unit number in the same property

Enforced by a database unique constraint as well as this validation.

```http
POST /properties/10/units
```

**Request**

```json
{
  "unit_number": "07-03",
  "monthly_rent": "9999.00"
}
```

**Response — `400`**

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request payload failed validation.",
    "details": {
      "unit_number": [
        "Unit '07-03' already exists in property 'Bugis Garden Apartments'."
      ]
    }
  }
}
```

### List units

```http
GET /units
```

**Response — `200`**

```json
{
  "count": 10,
  "total_pages": 1,
  "page": 1,
  "page_size": 20,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 36,
      "property_id": 7,
      "property_name": "Cantonment House",
      "unit_number": "01-01",
      "monthly_rent": "2500.00",
      "status": "occupied",
      "created_at": "2026-08-20T09:08:31.519019Z",
      "updated_at": "2026-08-20T09:08:31.535856Z"
    },
    {
      "id": 37,
      "property_id": 7,
      "property_name": "Cantonment House",
      "unit_number": "01-02",
      "monthly_rent": "2800.00",
      "status": "occupied",
      "created_at": "2026-08-20T09:08:31.520324Z",
      "updated_at": "2026-08-20T09:08:31.538812Z"
    },
    {
      "id": 38,
      "property_id": 7,
      "property_name": "Cantonment House",
      "unit_number": "02-01",
      "monthly_rent": "3200.00",
      "status": "occupied",
      "created_at": "2026-08-20T09:08:31.521306Z",
      "updated_at": "2026-08-20T09:08:31.549665Z"
    },
    "... 7 more omitted for brevity"
  ]
}
```

### Filter units by availability

`status` is never set by a client. A unit is `occupied` exactly when a contract covers today.

```http
GET /units?status=available
```

**Response — `200`**

```json
{
  "count": 6,
  "total_pages": 1,
  "page": 1,
  "page_size": 20,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 39,
      "property_id": 7,
      "property_name": "Cantonment House",
      "unit_number": "02-02",
      "monthly_rent": "3400.00",
      "status": "available",
      "created_at": "2026-08-20T09:08:31.522229Z",
      "updated_at": "2026-08-20T09:08:31.522232Z"
    },
    {
      "id": 41,
      "property_id": 8,
      "property_name": "Tanjong Pagar Residences",
      "unit_number": "05-12",
      "monthly_rent": "4350.00",
      "status": "available",
      "created_at": "2026-08-20T09:08:31.524817Z",
      "updated_at": "2026-08-20T09:08:31.524821Z"
    },
    {
      "id": 42,
      "property_id": 8,
      "property_name": "Tanjong Pagar Residences",
      "unit_number": "12-01",
      "monthly_rent": "6800.00",
      "status": "available",
      "created_at": "2026-08-20T09:08:31.525624Z",
      "updated_at": "2026-08-20T09:08:31.525627Z"
    },
    "... 3 more omitted for brevity"
  ]
}
```

### Filter units by property and rent

```http
GET /units?property=9&min_rent=3000
```

**Response — `200`**

```json
{
  "count": 0,
  "total_pages": 1,
  "page": 1,
  "page_size": 20,
  "next": null,
  "previous": null,
  "results": []
}
```

### Invalid filter value

```http
GET /units?status=bogus
```

**Response — `400`**

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request payload failed validation.",
    "details": {
      "status": [
        "Select a valid choice. bogus is not one of the available choices."
      ]
    }
  }
}
```


---

## Members

### Create a member

Members are tenants. They hold no credentials and cannot authenticate — this is a staff-only system.

```http
POST /members
```

**Request**

```json
{
  "full_name": "Amara Nwosu",
  "email": "amara.nwosu@example.com",
  "phone": "+65 8567 1234"
}
```

**Response — `201`**

```json
{
  "id": 14,
  "full_name": "Amara Nwosu",
  "email": "amara.nwosu@example.com",
  "phone": "+65 8567 1234",
  "created_at": "2026-08-20T09:08:32.227186Z",
  "updated_at": "2026-08-20T09:08:32.227195Z"
}
```

### Duplicate email

Email matching is case-insensitive, so casing cannot create two records for the same tenant.

```http
POST /members
```

**Request**

```json
{
  "full_name": "Someone Else",
  "email": "AMARA.NWOSU@example.com"
}
```

**Response — `400`**

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request payload failed validation.",
    "details": {
      "email": [
        "A member with this email already exists."
      ]
    }
  }
}
```

### List members

```http
GET /members
```

**Response — `200`**

```json
{
  "count": 6,
  "total_pages": 1,
  "page": 1,
  "page_size": 20,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 14,
      "full_name": "Amara Nwosu",
      "email": "amara.nwosu@example.com",
      "phone": "+65 8567 1234",
      "created_at": "2026-08-20T09:08:32.227186Z",
      "updated_at": "2026-08-20T09:08:32.227195Z"
    },
    {
      "id": 13,
      "full_name": "Hiroshi Tanaka",
      "email": "hiroshi.tanaka@example.com",
      "phone": "+65 8456 7890",
      "created_at": "2026-08-20T09:08:31.531754Z",
      "updated_at": "2026-08-20T09:08:31.531757Z"
    },
    {
      "id": 12,
      "full_name": "Sofia Alvarez",
      "email": "sofia.alvarez@example.com",
      "phone": "",
      "created_at": "2026-08-20T09:08:31.531028Z",
      "updated_at": "2026-08-20T09:08:31.531031Z"
    },
    "... 3 more omitted for brevity"
  ]
}
```

### Search members

```http
GET /members?search=priya
```

**Response — `200`**

```json
{
  "count": 1,
  "total_pages": 1,
  "page": 1,
  "page_size": 20,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 9,
      "full_name": "Priya Raman",
      "email": "priya.raman@example.com",
      "phone": "+65 8123 4567",
      "created_at": "2026-08-20T09:08:31.528736Z",
      "updated_at": "2026-08-20T09:08:31.528740Z"
    }
  ]
}
```


---

## Contracts

### Create a contract

`monthly_rent` omitted, so it defaults to the unit's rent. `total_value` is calculated server-side and can never be supplied by the client. 2031-01-01 to 2031-12-31 is twelve whole months — the end date is inclusive.

```http
POST /contracts
```

**Request**

```json
{
  "member_id": 14,
  "unit_id": 39,
  "start_date": "2031-01-01",
  "end_date": "2031-12-31"
}
```

**Response — `201`**

```json
{
  "id": 23,
  "member": {
    "id": 14,
    "full_name": "Amara Nwosu",
    "email": "amara.nwosu@example.com"
  },
  "unit": {
    "id": 39,
    "unit_number": "02-02",
    "monthly_rent": "3400.00",
    "status": "available"
  },
  "property_id": 7,
  "property_name": "Cantonment House",
  "start_date": "2031-01-01",
  "end_date": "2031-12-31",
  "monthly_rent": "3400.00",
  "total_value": "40800.00",
  "duration_months": {
    "months": 12,
    "extra_days": 0
  },
  "status": "upcoming",
  "is_active": false,
  "created_at": "2026-08-20T09:08:32.291435Z",
  "updated_at": "2026-08-20T09:08:32.291442Z"
}
```

### Create a contract with a rent override and a part-month tail

Fifteen days in January: 1000 x 15/31 = 483.87. The pro-rata denominator is the length of the calendar month the remainder falls in.

```http
POST /contracts
```

**Request**

```json
{
  "member_id": 14,
  "unit_id": 39,
  "start_date": "2032-01-01",
  "end_date": "2032-01-15",
  "monthly_rent": "1000.00"
}
```

**Response — `201`**

```json
{
  "id": 24,
  "member": {
    "id": 14,
    "full_name": "Amara Nwosu",
    "email": "amara.nwosu@example.com"
  },
  "unit": {
    "id": 39,
    "unit_number": "02-02",
    "monthly_rent": "3400.00",
    "status": "available"
  },
  "property_id": 7,
  "property_name": "Cantonment House",
  "start_date": "2032-01-01",
  "end_date": "2032-01-15",
  "monthly_rent": "1000.00",
  "total_value": "483.87",
  "duration_months": {
    "months": 0,
    "extra_days": 15
  },
  "status": "upcoming",
  "is_active": false,
  "created_at": "2026-08-20T09:08:32.312705Z",
  "updated_at": "2026-08-20T09:08:32.312715Z"
}
```

### Reject an overlapping contract

Double-booking prevention. The error names the conflicting contract. This is the friendly layer — the service re-checks under a row lock, and a PostgreSQL exclusion constraint is the actual guarantee.

```http
POST /contracts
```

**Request**

```json
{
  "member_id": 14,
  "unit_id": 39,
  "start_date": "2031-06-01",
  "end_date": "2031-07-01"
}
```

**Response — `400`**

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request payload failed validation.",
    "details": {
      "unit_id": [
        "Unit 02-02 already has a contract from 2031-01-01 to 2031-12-31 (contract #23) overlapping this range."
      ]
    }
  }
}
```

### Adjacent ranges are allowed

Starting the day after another contract ends is not an overlap.

```http
POST /contracts
```

**Request**

```json
{
  "member_id": 14,
  "unit_id": 39,
  "start_date": "2033-01-01",
  "end_date": "2033-06-30"
}
```

**Response — `201`**

```json
{
  "id": 25,
  "member": {
    "id": 14,
    "full_name": "Amara Nwosu",
    "email": "amara.nwosu@example.com"
  },
  "unit": {
    "id": 39,
    "unit_number": "02-02",
    "monthly_rent": "3400.00",
    "status": "available"
  },
  "property_id": 7,
  "property_name": "Cantonment House",
  "start_date": "2033-01-01",
  "end_date": "2033-06-30",
  "monthly_rent": "3400.00",
  "total_value": "20400.00",
  "duration_months": {
    "months": 6,
    "extra_days": 0
  },
  "status": "upcoming",
  "is_active": false,
  "created_at": "2026-08-20T09:08:32.354475Z",
  "updated_at": "2026-08-20T09:08:32.354484Z"
}
```

### End date before start date

```http
POST /contracts
```

**Request**

```json
{
  "member_id": 14,
  "unit_id": 39,
  "start_date": "2035-06-01",
  "end_date": "2035-01-01"
}
```

**Response — `400`**

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request payload failed validation.",
    "details": {
      "end_date": [
        "End date must be on or after start date."
      ]
    }
  }
}
```

### List contracts

```http
GET /contracts
```

**Response — `200`**

```json
{
  "count": 10,
  "total_pages": 1,
  "page": 1,
  "page_size": 20,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 25,
      "member": {
        "id": 14,
        "full_name": "Amara Nwosu",
        "email": "amara.nwosu@example.com"
      },
      "unit": {
        "id": 39,
        "unit_number": "02-02",
        "monthly_rent": "3400.00",
        "status": "available"
      },
      "property_id": 7,
      "property_name": "Cantonment House",
      "start_date": "2033-01-01",
      "end_date": "2033-06-30",
      "monthly_rent": "3400.00",
      "total_value": "20400.00",
      "duration_months": {
        "months": 6,
        "extra_days": 0
      },
      "status": "upcoming",
      "is_active": false,
      "created_at": "2026-08-20T09:08:32.354475Z",
      "updated_at": "2026-08-20T09:08:32.354484Z"
    },
    {
      "id": 24,
      "member": {
        "id": 14,
        "full_name": "Amara Nwosu",
        "email": "amara.nwosu@example.com"
      },
      "unit": {
        "id": 39,
        "unit_number": "02-02",
        "monthly_rent": "3400.00",
        "status": "available"
      },
      "property_id": 7,
      "property_name": "Cantonment House",
      "start_date": "2032-01-01",
      "end_date": "2032-01-15",
      "monthly_rent": "1000.00",
      "total_value": "483.87",
      "duration_months": {
        "months": 0,
        "extra_days": 15
      },
      "status": "upcoming",
      "is_active": false,
      "created_at": "2026-08-20T09:08:32.312705Z",
      "updated_at": "2026-08-20T09:08:32.312715Z"
    },
    "... 8 more omitted for brevity"
  ]
}
```

### Only active contracts

Active means the date range covers today, end date inclusive. There is no stored status flag to fall out of date.

```http
GET /contracts?active=true
```

**Response — `200`**

```json
{
  "count": 4,
  "total_pages": 1,
  "page": 1,
  "page_size": 20,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 17,
      "member": {
        "id": 10,
        "full_name": "Wei Lim",
        "email": "wei.lim@example.com"
      },
      "unit": {
        "id": 37,
        "unit_number": "01-02",
        "monthly_rent": "2800.00",
        "status": "occupied"
      },
      "property_id": 7,
      "property_name": "Cantonment House",
      "start_date": "2026-07-20",
      "end_date": "2027-07-20",
      "monthly_rent": "2800.00",
      "total_value": "33690.32",
      "duration_months": {
        "months": 12,
        "extra_days": 1
      },
      "status": "active",
      "is_active": true,
      "created_at": "2026-08-20T09:08:31.538083Z",
      "updated_at": "2026-08-20T09:08:31.538087Z"
    },
    {
      "id": 20,
      "member": {
        "id": 13,
        "full_name": "Hiroshi Tanaka",
        "email": "hiroshi.tanaka@example.com"
      },
      "unit": {
        "id": 40,
        "unit_number": "05-11",
        "monthly_rent": "4100.00",
        "status": "occupied"
      },
      "property_id": 8,
      "property_name": "Tanjong Pagar Residences",
      "start_date": "2026-06-20",
      "end_date": "2026-12-20",
      "monthly_rent": "3950.00",
      "total_value": "23827.42",
      "duration_months": {
        "months": 6,
        "extra_days": 1
      },
      "status": "active",
      "is_active": true,
      "created_at": "2026-08-20T09:08:31.545306Z",
      "updated_at": "2026-08-20T09:08:31.545310Z"
    },
    "... 2 more omitted for brevity"
  ]
}
```

### Contracts for one member

```http
GET /contracts?member=14
```

**Response — `200`**

```json
{
  "count": 3,
  "total_pages": 1,
  "page": 1,
  "page_size": 20,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 25,
      "member": {
        "id": 14,
        "full_name": "Amara Nwosu",
        "email": "amara.nwosu@example.com"
      },
      "unit": {
        "id": 39,
        "unit_number": "02-02",
        "monthly_rent": "3400.00",
        "status": "available"
      },
      "property_id": 7,
      "property_name": "Cantonment House",
      "start_date": "2033-01-01",
      "end_date": "2033-06-30",
      "monthly_rent": "3400.00",
      "total_value": "20400.00",
      "duration_months": {
        "months": 6,
        "extra_days": 0
      },
      "status": "upcoming",
      "is_active": false,
      "created_at": "2026-08-20T09:08:32.354475Z",
      "updated_at": "2026-08-20T09:08:32.354484Z"
    },
    {
      "id": 24,
      "member": {
        "id": 14,
        "full_name": "Amara Nwosu",
        "email": "amara.nwosu@example.com"
      },
      "unit": {
        "id": 39,
        "unit_number": "02-02",
        "monthly_rent": "3400.00",
        "status": "available"
      },
      "property_id": 7,
      "property_name": "Cantonment House",
      "start_date": "2032-01-01",
      "end_date": "2032-01-15",
      "monthly_rent": "1000.00",
      "total_value": "483.87",
      "duration_months": {
        "months": 0,
        "extra_days": 15
      },
      "status": "upcoming",
      "is_active": false,
      "created_at": "2026-08-20T09:08:32.312705Z",
      "updated_at": "2026-08-20T09:08:32.312715Z"
    },
    "... 1 more omitted for brevity"
  ]
}
```

