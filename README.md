# Finance Dashboard Backend

A Django REST Framework backend for an internal finance dashboard with role-based access control, financial records CRUD, and dashboard analytics.

## Tech Stack

- **Framework**: Django 5.2 + Django REST Framework
- **Python**: 3.12+ (3.14 supported)
- **Database**: SQLite (local) / PostgreSQL (Docker)
- **Authentication**: JWT via `djangorestframework-simplejwt`
- **Filtering**: `django-filter`
- **Containerization**: Docker + Docker Compose

---

## Quick Start (Local)

```bash
# 1. Create virtual environment
py -m venv venv
.\venv\Scripts\activate    # Windows
# source venv/bin/activate  # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run migrations
python manage.py makemigrations users records
python manage.py migrate

# 4. Create admin superuser
python manage.py createsuperuser
# When prompted, set role to ADMIN from the admin panel

# 5. Start development server
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/`

## Quick Start (Docker)

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Build and start containers
docker-compose up --build

# 3. Create superuser (in another terminal)
docker-compose exec web python manage.py createsuperuser
```

---

## Project Structure

```
finance_dashboard/
├── apps/
│   ├── users/              # User model, auth, permissions, user management
│   │   ├── models.py       # Custom User with Role (VIEWER/ANALYST/ADMIN)
│   │   ├── permissions.py  # IsAdmin, IsAnalystOrAbove, IsViewerOrAbove
│   │   ├── serializers.py  # User, CreateUser, UpdateUser, JWT serializers
│   │   ├── views.py        # Login, Refresh, Me endpoints
│   │   ├── management_views.py  # Admin-only user CRUD
│   │   ├── services.py     # User business logic
│   │   └── urls.py / management_urls.py
│   ├── records/            # Financial records CRUD
│   │   ├── models.py       # FinancialRecord with soft delete
│   │   ├── filters.py      # django-filter filterset
│   │   ├── serializers.py  # Full and List serializers
│   │   ├── views.py        # Records ViewSet
│   │   ├── services.py     # Record business logic
│   │   └── urls.py
│   └── dashboard/          # Analytics and aggregation
│       ├── services.py     # All aggregation logic (ORM)
│       ├── views.py        # Summary, trends, category, recent
│       └── urls.py
├── core/
│   ├── settings/
│   │   ├── base.py         # Shared settings (PostgreSQL for Docker)
│   │   └── local.py        # Local overrides (SQLite, DEBUG=True)
│   ├── urls.py             # Root URL config
│   ├── wsgi.py
│   └── exceptions.py       # Custom error handler
├── manage.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env / .env.example
└── README.md
```

---

## API Endpoints

### Authentication

| Method | Endpoint            | Description                    | Permission |
|--------|---------------------|--------------------------------|------------|
| POST   | `/api/auth/login/`  | Returns access + refresh JWT   | Open       |
| POST   | `/api/auth/refresh/`| Refresh an access token        | Open       |
| GET    | `/api/auth/me/`     | Get current user profile       | Any auth   |

> **Note**: There is no public registration endpoint. This is an internal dashboard — admins create user accounts.

### User Management (Admin Only)

| Method | Endpoint            | Description               | Permission |
|--------|---------------------|---------------------------|------------|
| GET    | `/api/users/`       | List all users            | Admin      |
| POST   | `/api/users/`       | Create a new user         | Admin      |
| GET    | `/api/users/{id}/`  | Get single user           | Admin      |
| PATCH  | `/api/users/{id}/`  | Update role or status     | Admin      |
| DELETE | `/api/users/{id}/`  | Deactivate user           | Admin      |

**Create user payload:**
```json
{
  "username": "john",
  "email": "john@example.com",
  "password": "securepassword",
  "role": "VIEWER",
  "first_name": "John",
  "last_name": "Doe"
}
```

### Financial Records

| Method | Endpoint              | Description                    | Permission |
|--------|-----------------------|--------------------------------|------------|
| GET    | `/api/records/`       | List records (with filters)    | Viewer+    |
| POST   | `/api/records/`       | Create a record                | Admin      |
| GET    | `/api/records/{id}/`  | Get single record              | Viewer+    |
| PATCH  | `/api/records/{id}/`  | Update a record                | Admin      |
| DELETE | `/api/records/{id}/`  | Soft delete a record           | Admin      |

**Filters & Search** (query parameters):
- `record_type` — `INCOME` or `EXPENSE`
- `category` — `SALARY`, `FREELANCE`, `INVESTMENT`, `RENT`, `UTILITIES`, `FOOD`, `TRANSPORT`, `HEALTHCARE`, `ENTERTAINMENT`, `EDUCATION`, `OTHER`
- `date_after` — `YYYY-MM-DD` (records on or after)
- `date_before` — `YYYY-MM-DD` (records on or before)
- `search` — free-text, matches against `notes` and `category` (case-insensitive)
- `ordering` — `date`, `amount`, `created_at`, `category` (prefix with `-` for descending)

**Example:** `GET /api/records/?record_type=INCOME&date_after=2025-01-01&search=salary&ordering=-amount`

**Create record payload:**
```json
{
  "amount": "5000.00",
  "record_type": "INCOME",
  "category": "SALARY",
  "date": "2025-01-15",
  "notes": "January salary"
}
```

### Dashboard

| Method | Endpoint                          | Description                     | Permission |
|--------|-----------------------------------|---------------------------------|------------|
| GET    | `/api/dashboard/summary/`         | Total income, expense, balance  | Viewer+    |
| GET    | `/api/dashboard/category-totals/` | Breakdown by category           | Viewer+    |
| GET    | `/api/dashboard/monthly-trends/`  | Month-wise trends (`month_label` field included) | Analyst+   |
| GET    | `/api/dashboard/recent/`          | Last N transactions             | Viewer+    |

**Monthly trends** response fields per row: `month` (date), `month_label` (e.g. `"2025-03"`), `record_type`, `total`, `count`.

**Recent transactions** accepts optional `?count=5` (default 10, max 50).

---

## Role Permission Matrix

| Action                         | VIEWER | ANALYST | ADMIN |
|--------------------------------|--------|---------|-------|
| View financial records         | ✅     | ✅      | ✅    |
| Filter records                 | ✅     | ✅      | ✅    |
| View dashboard summary         | ✅     | ✅      | ✅    |
| View category totals           | ✅     | ✅      | ✅    |
| View recent transactions       | ✅     | ✅      | ✅    |
| Access monthly trends          | ❌     | ✅      | ✅    |
| Create financial record        | ❌     | ❌      | ✅    |
| Update financial record        | ❌     | ❌      | ✅    |
| Soft-delete financial record   | ❌     | ❌      | ✅    |
| View all users                 | ❌     | ❌      | ✅    |
| Create user                    | ❌     | ❌      | ✅    |
| Update user role/status        | ❌     | ❌      | ✅    |
| Deactivate user                | ❌     | ❌      | ✅    |

---

## Error Response Format

All errors follow a consistent JSON shape:

```json
{
  "error": true,
  "message": "Human-readable error message.",
  "details": {}
}
```

| Status Code | Meaning                         |
|-------------|---------------------------------|
| 400         | Bad input / validation error    |
| 401         | Not authenticated               |
| 403         | Insufficient role/permission    |
| 404         | Resource not found              |

---

## Rate Limiting

All endpoints are throttled to prevent abuse:

| Client type         | Limit       | Purpose |
|---------------------|-------------|----------|
| Unauthenticated     | 10 req/min  | Slows brute-force on `/api/auth/login/` |
| Authenticated user  | 300 req/min | Generous for interactive use, blocks runaway scripts |

When a limit is exceeded the API returns **HTTP 429 Too Many Requests**.

---

## Design Decisions & Assumptions

### Architecture
1. **Service layer pattern** — Business logic lives in `services.py`, views are thin controllers
2. **Separate URL files** — Auth (`urls.py`) and user management (`management_urls.py`) are separate to keep concerns clean
3. **Split settings** — `base.py` for shared config, `local.py` for SQLite/dev overrides

### Data
1. **`DecimalField` for money** — Avoids floating-point precision errors inherent in `FloatField`
2. **Soft delete** — Financial records are never hard-deleted; `is_deleted=True` flag preserves audit trail
3. **`SET_NULL` on `created_by`** — Records survive user deletion
4. **System-defined categories** — `TextChoices` enum keeps aggregation queries clean and fast. Upgrade path: if categories need to be dynamic, they become a separate model with no breaking API changes
5. **Roles as `TextChoices`** — Roles are fixed and small (3 values), so a separate table adds complexity without benefit
6. **Future-date guard** — Record dates more than 1 year in the future are rejected (catches typos like "2099" while allowing legitimate budget/planned entries)
7. **`month_label` in trends** — `GET /api/dashboard/monthly-trends/` returns both a raw `month` date and a `month_label` (`"YYYY-MM"`) string so frontends can render it directly without date formatting

### Auth & Access
1. **No public registration** — This is an internal finance dashboard; admins create accounts and assign roles
2. **User deactivation** — `DELETE /api/users/{id}/` sets `is_active=False`, never hard-deletes
3. **JWT tokens** — 30-minute access, 1-day refresh, with token rotation

### Performance
1. **Database indexes** on `record_type`, `category`, `date`, and `is_deleted` for fast dashboard queries
2. **Paginated results** — 20 records per page by default
3. **Light serializer** for list views (excludes notes and detailed timestamps)

---

## Pagination

All list endpoints return paginated results:

```json
{
  "count": 42,
  "next": "http://127.0.0.1:8000/api/records/?page=2",
  "previous": null,
  "results": [...]
}
```

Default page size: **20 records**. Use `?page=N` to navigate.

---

## Environment Variables

| Variable             | Description                  | Default           |
|----------------------|------------------------------|--------------------|
| `SECRET_KEY`         | Django secret key            | -                  |
| `DEBUG`              | Debug mode                   | `False`            |
| `ALLOWED_HOSTS`      | Comma-separated hosts        | `localhost,127...` |
| `DB_NAME`            | PostgreSQL database name     | `finance_db`       |
| `DB_USER`            | PostgreSQL user              | `postgres`         |
| `DB_PASSWORD`        | PostgreSQL password          | `postgres`         |
| `DB_HOST`            | PostgreSQL host              | `db`               |
| `DB_PORT`            | PostgreSQL port              | `5432`             |
| `CORS_ALLOWED_ORIGINS` | Allowed CORS origins       | `localhost:3000`   |

> Local development uses SQLite and ignores the `DB_*` variables.

# zorvyn-fintech-project
