# Datapilot - Architecture Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [System Architecture](#system-architecture)
3. [Backend Architecture](#backend-architecture)
4. [Frontend Architecture](#frontend-architecture)
5. [Infrastructure Architecture](#infrastructure-architecture)
6. [Key Architectural Decisions](#key-architectural-decisions)
7. [Data Flow](#data-flow)
8. [Security Architecture](#security-architecture)

---

## Project Overview

Datapilot is a full-stack, multi-tenant data intelligence platform designed for small to mid-sized organizations to manage their entire data lifecycle - from ingestion through cleaning, analysis, and visualization.

### Tech Stack Summary

**Backend:**
- FastAPI (async Python web framework)
- PostgreSQL (primary database)
- Redis (caching, queues, real-time features)
- SQLAlchemy (ORM)
- Celery/RQ (background workers)
- Cloudflare R2/S3 (file storage)

**Frontend:**
- Next.js 14+ (App Router)
- React 18+
- TypeScript
- Shadcn UI (component library)
- TanStack Query (server state)
- Zustand (client state)
- WebSockets (real-time updates)

**Infrastructure:**
- Docker & Docker Compose
- Kubernetes (optional, for production scale)
- GitHub Actions (CI/CD)
- Nginx (reverse proxy, SSL termination)
- Railway/Fly.io (deployment targets)

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Client Layer                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │   Browser  │  │   Mobile   │  │  API Clients│            │
│  └─────┬──────┘  └──────┬─────┘  └──────┬─────┘            │
└────────┼─────────────────┼────────────────┼──────────────────┘
         │                 │                │
         └─────────────────┴────────────────┘
                           │
         ┌─────────────────▼──────────────────┐
         │         Nginx (SSL/LB)             │
         └─────────────────┬──────────────────┘
                           │
         ┌─────────────────┴──────────────────┐
         │                                     │
┌────────▼─────────┐              ┌───────────▼──────────┐
│  Next.js Frontend │              │   FastAPI Backend    │
│  (SSR/SSG/CSR)   │◄────────────►│   (REST API)         │
└──────────────────┘              └──────┬───────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
           ┌────────▼────────┐  ┌────────▼────────┐  ┌───────▼──────┐
           │   PostgreSQL    │  │     Redis       │  │   R2/S3      │
           │   (Primary DB)  │  │  (Cache/Queue)  │  │ (File Store) │
           └─────────────────┘  └─────────────────┘  └──────────────┘
                                         │
                                ┌────────▼─────────┐
                                │  Celery Workers  │
                                │  (Background)    │
                                └──────────────────┘
```

### Multi-Tenancy Model

Datapilot implements **row-level multi-tenancy** using organization scoping:

- Every data table includes an `organization_id` foreign key
- All queries are automatically filtered by the authenticated user's organization
- Middleware enforces organization context on every request
- No data cross-contamination between organizations

---

## Backend Architecture

### Directory Structure Rationale

```
backend/
├── app/
│   ├── api/                    # API layer (routes, endpoints)
│   │   └── v1/                 # API versioning for future-proofing
│   │       ├── endpoints/      # Route handlers organized by domain
│   │       └── dependencies/   # FastAPI dependency injection
│   ├── core/                   # Core configurations, security, logging
│   ├── models/                 # SQLAlchemy ORM models (database layer)
│   ├── schemas/                # Pydantic schemas (validation/serialization)
│   ├── services/               # Business logic layer
│   │   ├── auth/              # Authentication & authorization services
│   │   ├── data_ingestion/    # CSV/Excel parsing, validation, loading
│   │   ├── transformation/    # Data cleaning, normalization
│   │   ├── visualization/     # Chart generation, aggregation
│   │   └── llm/               # AI-powered insights
│   ├── db/                    # Database session, initialization
│   ├── middleware/            # Request/response middleware
│   ├── workers/               # Celery/background task definitions
│   ├── utils/                 # Shared utilities (S3, email, helpers)
│   └── tests/                 # Test suite (unit, integration, e2e)
├── alembic/                   # Database migration management
├── storage/                   # Local file storage (development)
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Development dependencies
└── pyproject.toml            # Python project configuration
```

### Key Architectural Patterns

#### 1. **Layered Architecture**
- **API Layer** (`api/v1/endpoints/`) - HTTP request handling, route definitions
- **Schema Layer** (`schemas/`) - Input validation, output serialization via Pydantic
- **Service Layer** (`services/`) - Business logic, isolated from HTTP concerns
- **Data Layer** (`models/`, `db/`) - Database interaction via SQLAlchemy ORM

**Why:** Clear separation of concerns enables:
- Easier testing (mock services without HTTP)
- Reusability (services can be called from API endpoints or workers)
- Maintainability (changes to business logic don't affect routing)

#### 2. **Dependency Injection**
FastAPI's dependency injection system is used for:
- Authentication (`dependencies/auth.py`)
- Permission checking (`dependencies/permissions.py`)
- Tenant context enforcement (`dependencies/tenant.py`)

**Why:** Keeps route handlers clean, promotes reusability, and simplifies testing with mock dependencies.

#### 3. **API Versioning**
All routes are under `/api/v1/` namespace.

**Why:** Future API changes won't break existing clients. We can introduce `/api/v2/` with breaking changes while maintaining v1 compatibility.

#### 4. **Service-Oriented Business Logic**
Each domain (auth, data_ingestion, transformation) has dedicated service modules.

**Why:**
- Single Responsibility Principle
- Services can be unit tested independently
- Easy to swap implementations (e.g., switch from local storage to S3)

#### 5. **Async-First Design**
FastAPI with async SQLAlchemy, async Redis, async file I/O.

**Why:**
- Handle high concurrency efficiently
- Non-blocking I/O for file uploads, database queries
- Better resource utilization for I/O-bound operations

#### 6. **Background Task Processing**
Celery workers for heavy operations (large file parsing, bulk transformations).

**Why:**
- Prevent API timeout on long-running operations
- Progress tracking via WebSocket updates
- Horizontal scaling of worker instances

---

## Frontend Architecture

### Directory Structure Rationale

```
frontend/
├── src/
│   ├── app/                          # Next.js 14 App Router
│   │   ├── (auth)/                   # Route group for authentication
│   │   │   ├── login/
│   │   │   ├── register/
│   │   │   └── forgot-password/
│   │   ├── (dashboard)/              # Route group for authenticated dashboard
│   │   │   ├── dashboard/            # Main dashboard
│   │   │   ├── datasets/             # Dataset management
│   │   │   │   └── [id]/             # Dynamic dataset detail page
│   │   │   ├── visualizations/       # Chart/visualization builder
│   │   │   ├── insights/             # AI-generated insights
│   │   │   ├── settings/             # User/org settings
│   │   │   ├── team/                 # Team management
│   │   │   └── billing/              # Subscription management
│   │   ├── api/                      # Next.js API routes (middleware)
│   │   │   ├── auth/                 # Auth proxy to backend
│   │   │   ├── upload/               # File upload proxy
│   │   │   └── webhook/              # Webhook handlers
│   │   ├── layout.tsx                # Root layout
│   │   └── page.tsx                  # Landing page
│   ├── components/
│   │   ├── ui/                       # Shadcn UI components (Button, Input, etc.)
│   │   ├── layout/                   # Layout components (Header, Sidebar, Footer)
│   │   ├── forms/                    # Form components (login, upload, etc.)
│   │   ├── charts/                   # Chart visualization components
│   │   ├── tables/                   # Data table components
│   │   ├── dashboard/                # Dashboard-specific components
│   │   ├── datasets/                 # Dataset-specific components
│   │   └── shared/                   # Shared/common components
│   ├── lib/
│   │   ├── api/                      # API client (Axios/Fetch wrappers)
│   │   ├── auth/                     # Auth utilities, session management
│   │   ├── store/                    # Zustand stores (auth, dataset, UI state)
│   │   ├── hooks/                    # Custom React hooks
│   │   ├── utils/                    # Utility functions (formatting, etc.)
│   │   └── validators/               # Zod/validation schemas
│   ├── types/                        # TypeScript type definitions
│   └── styles/                       # Global styles, theme configuration
├── public/                           # Static assets
│   ├── images/
│   ├── icons/
│   └── fonts/
├── .env.local.example                # Environment variable template
└── next.config.ts                    # Next.js configuration
```

### Key Architectural Patterns

#### 1. **App Router with Route Groups**
Using Next.js 14 App Router with route groups `(auth)` and `(dashboard)`.

**Why:**
- Route groups allow shared layouts without affecting URL structure
- `(auth)` group can have a centered layout for login/register
- `(dashboard)` group has sidebar navigation layout
- Both routes are organized logically without `/auth/` or `/dashboard/` in URLs

#### 2. **Server Components by Default**
Next.js 14 defaults to React Server Components.

**Why:**
- Reduced JavaScript bundle size (server components don't ship to client)
- Faster initial page loads
- Direct database/API access in server components
- Client components (`'use client'`) only where needed (forms, interactive charts)

#### 3. **Colocation of Concerns**
Each route has its own `page.tsx`, `layout.tsx`, and can have `loading.tsx`, `error.tsx`.

**Why:**
- Easy to understand route structure
- Built-in loading states and error boundaries per route
- Better code splitting automatically

#### 4. **Component Organization by Feature**
Components are grouped by feature/domain rather than type.

**Why:**
- `components/dashboard/` contains all dashboard-related components
- `components/datasets/` contains dataset-specific components
- Easier to locate and refactor feature-specific code
- `components/shared/` for truly reusable components

#### 5. **State Management Strategy**
- **Server State:** TanStack Query for API data (caching, refetching, optimistic updates)
- **Client State:** Zustand for global UI state, auth state, temporary form state
- **URL State:** Next.js searchParams for filters, pagination

**Why:**
- TanStack Query handles server-side data complexity (caching, background refetch)
- Zustand is lightweight for simple global state (no boilerplate like Redux)
- URL state enables shareable links and browser back/forward

#### 6. **API Proxy Pattern**
Next.js API routes (`app/api/*`) proxy requests to FastAPI backend.

**Why:**
- Securely store backend API URL (not exposed to client)
- Add authentication headers server-side
- Handle file uploads with progress tracking
- CORS management

#### 7. **Type Safety with TypeScript**
Strict TypeScript configuration, shared types in `types/` directory.

**Why:**
- Catch errors at compile time
- Better IDE autocomplete
- Self-documenting code with interfaces
- Share types between API responses and UI components

---

## Infrastructure Architecture

### Directory Structure Rationale

```
infra/
├── docker/
│   ├── Dockerfile.backend          # Multi-stage backend build
│   ├── Dockerfile.frontend         # Multi-stage frontend build
│   ├── Dockerfile.worker           # Worker service
│   ├── docker-compose.yml          # Base compose file
│   ├── docker-compose.dev.yml      # Development overrides
│   ├── docker-compose.prod.yml     # Production configuration
│   └── .dockerignore               # Exclude unnecessary files
├── nginx/
│   ├── nginx.conf                  # Main Nginx configuration
│   ├── ssl.conf                    # SSL/TLS settings
│   └── upstream.conf               # Backend upstream configuration
├── scripts/
│   ├── setup.sh                    # Initial setup script
│   ├── deploy.sh                   # Deployment automation
│   ├── backup.sh                   # Database backup
│   ├── migrate.sh                  # Run migrations
│   └── seed.sh                     # Seed database
├── terraform/                      # Infrastructure as Code
│   ├── main.tf                     # Main infrastructure definition
│   ├── variables.tf                # Input variables
│   ├── outputs.tf                  # Output values
│   ├── backend.tf                  # Terraform state backend
│   ├── providers.tf                # Cloud provider configuration
│   └── modules/
│       ├── database/               # PostgreSQL/RDS module
│       ├── storage/                # S3/R2 module
│       ├── networking/             # VPC, subnets, security groups
│       └── compute/                # EC2/container instances
├── k8s/                            # Kubernetes manifests (optional)
│   ├── base/                       # Base configurations
│   │   ├── deployment.yml
│   │   ├── service.yml
│   │   ├── configmap.yml
│   │   ├── secrets.yml
│   │   ├── ingress.yml
│   │   └── kustomization.yml
│   └── overlays/                   # Environment-specific overlays
│       ├── dev/
│       ├── staging/
│       └── prod/
└── .github/
    └── workflows/
        ├── ci.yml                  # Continuous Integration
        ├── deploy-dev.yml          # Auto-deploy to dev
        ├── deploy-staging.yml      # Deploy to staging
        ├── deploy-prod.yml         # Deploy to production
        ├── test.yml                # Run test suite
        └── lint.yml                # Code quality checks
```

### Key Infrastructure Decisions

#### 1. **Multi-Stage Docker Builds**
Each Dockerfile uses multi-stage builds (builder → runtime).

**Why:**
- Smaller final images (exclude build tools, dependencies)
- Faster deployments (less data to transfer)
- Security (no build tools in production images)

#### 2. **Docker Compose for Local Development**
`docker-compose.dev.yml` with hot-reloading, exposed ports, local volumes.

**Why:**
- Consistent development environment across team
- Match production architecture locally
- Easy onboarding (single `docker-compose up`)

#### 3. **Nginx as Reverse Proxy**
Nginx sits in front of frontend and backend.

**Why:**
- SSL/TLS termination in one place
- Load balancing to multiple backend instances
- Serve static files efficiently
- Rate limiting, security headers

#### 4. **Infrastructure as Code (Terraform)**
Production infrastructure defined in Terraform.

**Why:**
- Version-controlled infrastructure
- Reproducible deployments
- Easy to create staging/production environments
- Disaster recovery (rebuild from code)

#### 5. **Kubernetes with Kustomize (Optional)**
Kustomize for environment-specific configurations.

**Why:**
- Base configurations shared across environments
- Environment overlays (dev/staging/prod) with minimal duplication
- GitOps-friendly (declarative YAML)

#### 6. **GitHub Actions CI/CD**
Separate workflows for CI, testing, and deployment.

**Why:**
- Automated testing on every PR
- Automatic deployment to dev on merge to main
- Manual approval for staging/production
- Fast feedback loop

---

## Key Architectural Decisions

### 1. Why FastAPI + Next.js?

**FastAPI:**
- Native async/await for high concurrency
- Automatic OpenAPI documentation
- Pydantic for data validation
- Python ecosystem for data processing (pandas, numpy)

**Next.js:**
- React Server Components (performance)
- Built-in routing, API routes
- SSR/SSG for SEO and fast initial loads
- Developer experience (hot reload, TypeScript)

### 2. Why PostgreSQL?

- ACID compliance for financial/critical data
- Excellent JSON support (for flexible schema fields)
- Row-level security features
- Mature ecosystem, good ORMs
- Full-text search capabilities

### 3. Why Redis?

- Fast caching for frequently accessed data
- Job queue (if not using Celery with RabbitMQ/SQS)
- Real-time features (pub/sub for WebSockets)
- Session storage

### 4. Why Celery/Background Workers?

- Large file processing can't block API responses
- Scale workers independently from API servers
- Progress tracking for long operations
- Retry logic for failed tasks

### 5. Why Row-Level Multi-Tenancy (Not Schema-per-Tenant)?

**Pros:**
- Simpler database management (one schema)
- Easier to query across organizations (for analytics)
- Lower overhead (no schema proliferation)

**Cons:**
- Requires careful query filtering (middleware enforces this)
- No database-level isolation (but adequate for most use cases)

**Decision:** Row-level is sufficient for small-to-mid-sized orgs, easier to manage.

### 6. Why Shadcn UI?

- Unstyled primitives (full control over design)
- Copy-paste components (no dependency bloat)
- Built on Radix UI (accessibility, behavior)
- Tailwind CSS (utility-first, responsive design)

### 7. Why TanStack Query + Zustand?

**TanStack Query:**
- Handles server state complexity (caching, refetching, invalidation)
- Reduces boilerplate compared to manual fetch + useState

**Zustand:**
- Minimal boilerplate for global client state
- No provider wrappers
- Simple API, TypeScript-friendly

---

## Data Flow

### 1. User Authentication Flow

```
1. User submits credentials (email/password)
2. Frontend → POST /api/v1/auth/login
3. Backend validates credentials, generates JWT
4. Frontend stores JWT in httpOnly cookie + Zustand store
5. Subsequent requests include JWT in Authorization header
6. Backend middleware validates JWT → extracts user + organization
7. Dependency injection provides current_user to route handlers
```

### 2. Data Ingestion Flow

```
1. User uploads CSV/Excel via frontend form
2. Frontend → POST /api/v1/files/upload (multipart/form-data)
3. Backend saves file to temporary storage (local or S3)
4. Backend enqueues Celery task: parse_and_ingest(file_id)
5. Worker processes file:
   a. Parse CSV/Excel (pandas)
   b. Infer column types
   c. Validate data
   d. Normalize/clean data
   e. Bulk insert into records table
6. Worker updates job status → publishes to WebSocket
7. Frontend receives real-time progress updates
8. On completion, frontend refetches dataset list (TanStack Query)
```

### 3. Visualization Generation Flow

```
1. User requests visualization for dataset
2. Frontend → POST /api/v1/visualizations/generate {dataset_id, chart_type}
3. Backend queries aggregated data from records table
4. Optionally, LLM service suggests chart type/insights
5. Backend returns chart configuration (labels, data, colors)
6. Frontend renders chart using React charting library
```

---

## Security Architecture

### 1. Authentication & Authorization

- **JWT tokens** with short expiration (15 min access, 7 day refresh)
- **httpOnly cookies** to prevent XSS attacks
- **RBAC** (Admin, Manager, Analyst, Viewer roles)
- **Permission system** (fine-grained permissions like `data:import`, `org:manage`)

### 2. Multi-Tenancy Enforcement

- **Middleware** automatically injects organization_id filter
- **Database queries** scoped by organization (no manual filtering)
- **File storage** organized by organization prefix (`org-123/files/...`)

### 3. Input Validation

- **Pydantic schemas** on backend (validate all inputs)
- **Zod schemas** on frontend (client-side validation)
- **SQL injection protection** via SQLAlchemy ORM (parameterized queries)

### 4. File Upload Security

- **File type validation** (whitelist CSV, XLSX)
- **File size limits** (enforced by Nginx and FastAPI)
- **Virus scanning** (optional: integrate ClamAV or cloud scanner)
- **Sandboxed processing** (workers run in isolated containers)

### 5. API Rate Limiting

- **Nginx rate limiting** by IP
- **Redis-based rate limiting** per user/organization
- **Throttling** on expensive endpoints (AI insights, bulk exports)

### 6. Data Privacy

- **Encryption at rest** (PostgreSQL, S3)
- **Encryption in transit** (HTTPS/TLS)
- **PII masking** (optional: mask sensitive columns in logs/exports)

---

## Conclusion

This architecture balances **simplicity** (for rapid development), **scalability** (async backend, horizontal scaling), and **maintainability** (clear separation of concerns, typed interfaces).

The scaffold is designed to be **production-ready** from day one, with:
- CI/CD pipelines
- Multi-environment support (dev, staging, prod)
- Monitoring hooks (health checks, logging)
- Extensibility (modular services, versioned APIs)

This foundation supports the 30-day implementation plan while keeping technical debt low and code quality high.
