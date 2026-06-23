# RentalVerify Implementation Plan

## 1. Scope

This implementation plan covers a 3-actor landlord verification and scam intelligence system for Kenya.

In scope:
- Prospective Renter
- Registered Landlord
- Administrator
- Public landlord search
- Scam report submission and tracking
- Landlord registration and verification
- Admin review, approval, rejection, escalation, and analytics
- Audit logging and notifications

Out of scope:
- B2B API
- Partner registration
- External machine-to-machine verification
- API key management

Removing the B2B API does not affect the core product. It reduces complexity and keeps the system focused on the primary consumer workflow.

## 2. Actors

### 2.1 Prospective Renter
Primary public user who:
- searches a landlord by phone number, national ID, name, or M-Pesa number
- views verification status and scam history
- submits a scam report

### 2.2 Registered Landlord
User who:
- creates a landlord profile
- submits identity and property details for verification
- updates profile details when needed
- logs in to view registration status

### 2.3 Administrator
Privileged user who:
- reviews landlord registrations
- approves or rejects landlord accounts
- reviews and escalates scam reports
- manages analytics and audit logs

## 3. System Architecture

### 3.1 Technology Stack
- Frontend: HTML, CSS, minimal JavaScript where needed
- Backend: FastAPI
- Database: PostgreSQL
- Template rendering: Jinja2 for server-side pages
- Database access: raw SQL through a PostgreSQL driver such as `psycopg`
- Schema management: versioned SQL migration files, not Alembic
- Password hashing: bcrypt or passlib with bcrypt
- Session/auth: secure server sessions or JWT for authenticated roles

### 3.2 Logical Layers

#### Presentation Layer
Handles all browser-facing pages:
- landing page
- search page
- report form
- landlord onboarding pages
- login pages
- admin dashboard

#### Application Layer
FastAPI route handlers and services:
- validation
- authentication
- business rules
- role-based access control
- search scoring
- report escalation

#### Data Layer
PostgreSQL stores:
- users
- landlord profiles
- property details
- scam reports
- search logs
- admin actions
- audit trail

All database access should use parameterised SQL statements and explicit transaction handling. No ORM models are used.

## 4. Core Modules

### 4.1 Public Search Module
Allows a renter to search for a landlord and see:
- verification status
- report count
- risk level
- disclaimer when no match is found

### 4.2 Scam Reporting Module
Allows a renter to submit a complaint with:
- landlord identifier
- contact details
- property details
- M-Pesa reference
- description of incident

### 4.3 Landlord Registration Module
Allows a landlord to:
- create an account
- submit identity documents
- provide property information
- wait for admin review

### 4.4 Admin Management Module
Allows an administrator to:
- review pending landlords
- approve or reject submissions
- review scam reports
- escalate high-risk cases
- view statistics

### 4.5 Audit and Notification Module
Tracks important actions and sends notifications for:
- landlord approval or rejection
- report receipt
- report escalation
- profile updates

## 5. System Flows

### 5.1 Landlord Search Flow
1. User opens the search page.
2. User enters a search term.
3. Backend normalizes the term.
4. Backend checks landlord records and reports.
5. System returns:
   - Verified
   - Reported
   - Not Found
6. System shows a safety disclaimer when needed.

### 5.2 Scam Report Flow
1. User opens the scam report form.
2. User fills in landlord and incident details.
3. Backend validates inputs and checks for duplicates.
4. System stores the report.
5. System generates a report reference number.
6. Admin can later review or escalate the report.

### 5.3 Landlord Registration Flow
1. Landlord creates an account.
2. Landlord submits identity and property details.
3. Backend validates and stores the submission.
4. Submission status is set to `Pending Review`.
5. Admin reviews the submission.
6. Admin approves or rejects it.

### 5.4 Admin Review Flow
1. Admin logs in.
2. Admin opens the pending queue.
3. Admin reviews landlord identity and supporting details.
4. Admin approves or rejects.
5. System updates status and records the action in audit logs.

## 6. Pages To Build

### Public Pages
- Home / landing page
- Landlord search page
- Search result page
- Scam report page
- Scam report confirmation page
- Landlord registration page
- Landlord login page
- Landlord dashboard
- Admin login page
- Admin dashboard
- Admin registration review page
- Admin report review page
- Admin analytics page
- Error pages

### Page Responsibilities

#### Home Page
- explains what RentalVerify does
- provides links to search, report, and landlord registration

#### Search Page
- accepts query input
- shows result summary

#### Search Result Page
- displays landlord status
- shows report count and warnings

#### Scam Report Page
- collects incident details
- submits report securely

#### Landlord Registration Page
- collects identity and property details
- submits for admin review

#### Landlord Dashboard
- shows registration status
- allows profile update requests

#### Admin Dashboard
- shows queue counts
- shows recent reports
- shows approval statistics

#### Admin Review Pages
- pending landlord queue
- scam report queue
- escalation controls

## 7. Backend API Design

The frontend can be rendered server-side by FastAPI, but the same backend should still expose clean internal endpoints.

### 7.1 Authentication
- `POST /auth/login`
- `POST /auth/logout`
- `POST /auth/register-landlord`
- `GET /auth/me`

### 7.2 Public Search
- `POST /search`
- `GET /search/{landlord_id}`
- `GET /search/history/{search_id}` optional

### 7.3 Scam Reports
- `POST /reports`
- `GET /reports/{report_id}`
- `GET /reports/my-reports`

### 7.4 Landlord Management
- `POST /landlords`
- `GET /landlords/me`
- `PATCH /landlords/me`
- `GET /landlords/{landlord_id}` admin only

### 7.5 Admin Operations
- `GET /admin/dashboard`
- `GET /admin/landlords/pending`
- `POST /admin/landlords/{landlord_id}/approve`
- `POST /admin/landlords/{landlord_id}/reject`
- `GET /admin/reports`
- `POST /admin/reports/{report_id}/escalate`
- `GET /admin/audit-logs`
- `GET /admin/analytics`

### 7.6 Utility and Reference
- `GET /health`
- `GET /status`

## 8. Suggested Database Schema

### 8.1 users
Stores all authenticated accounts.
- `id`
- `full_name`
- `email`
- `phone_number`
- `password_hash`
- `role` (`renter`, `landlord`, `admin`)
- `is_active`
- `created_at`
- `updated_at`

### 8.2 landlord_profiles
Stores landlord verification information.
- `id`
- `user_id`
- `national_id_number`
- `m_pesa_number`
- `property_name`
- `property_location`
- `property_address`
- `verification_status` (`pending`, `verified`, `rejected`)
- `verified_at`
- `created_at`
- `updated_at`

### 8.3 landlord_documents
Stores uploaded document metadata.
- `id`
- `landlord_profile_id`
- `document_type`
- `file_path`
- `uploaded_at`

### 8.4 scam_reports
Stores scam complaints.
- `id`
- `reporter_user_id`
- `landlord_name`
- `phone_number`
- `national_id_number`
- `m_pesa_number`
- `property_address`
- `description`
- `status` (`open`, `under_review`, `escalated`, `closed`)
- `reference_number`
- `created_at`
- `updated_at`

### 8.5 search_logs
Tracks searches for analytics and risk scoring.
- `id`
- `search_term`
- `search_type`
- `result_status`
- `matched_landlord_id`
- `created_at`

### 8.6 admin_actions
Tracks moderation actions.
- `id`
- `admin_user_id`
- `action_type`
- `entity_type`
- `entity_id`
- `notes`
- `created_at`

### 8.7 audit_logs
Tracks all important state changes.
- `id`
- `actor_user_id`
- `action`
- `entity_type`
- `entity_id`
- `before_state`
- `after_state`
- `created_at`

## 8.8 SQL Migration Strategy

Use ordered SQL files instead of Alembic:
- `001_create_users.sql`
- `002_create_landlord_profiles.sql`
- `003_create_landlord_documents.sql`
- `004_create_scam_reports.sql`
- `005_create_search_logs.sql`
- `006_create_admin_actions.sql`
- `007_create_audit_logs.sql`

Migration rules:
- run each file once in order
- store applied migrations in a `schema_migrations` table
- keep rollback SQL in separate companion files only if needed
- never rely on ORM-generated schema changes

## 9. Recommended Folder Structure

```text
app/
  main.py
  core/
    config.py
    security.py
    dependencies.py
  db/
    connection.py
    migrations/
      001_create_users.sql
      002_create_landlord_profiles.sql
      003_create_landlord_documents.sql
      004_create_scam_reports.sql
      005_create_search_logs.sql
      006_create_admin_actions.sql
      007_create_audit_logs.sql
  models/
  schemas/
    auth.py
    landlord.py
    report.py
    search.py
    admin.py
  services/
    auth_service.py
    landlord_service.py
    report_service.py
    search_service.py
    admin_service.py
    audit_service.py
  routers/
    auth.py
    public.py
    landlords.py
    reports.py
    admin.py
  templates/
    base.html
    index.html
    search.html
    search_result.html
    report_form.html
    landlord_register.html
    landlord_dashboard.html
    admin_dashboard.html
    admin_reviews.html
  static/
    css/
      main.css
    js/
      app.js
    images/
```

## 10. Implementation Phases

### Phase 1: Project Setup
- create FastAPI project structure
- connect PostgreSQL
- define environment variables
- set up templates and static assets
- create base layout and navigation

### Phase 2: Database and Models
- define raw SQL schema
- create ordered SQL migration files
- seed admin account
- verify relationships and constraints

### Phase 3: Authentication and Roles
- implement login/logout
- implement role checks
- secure admin routes
- secure landlord routes

### Phase 4: Public Search
- build search form
- implement search normalization
- implement result ranking and status resolution

### Phase 5: Scam Reporting
- build report form
- implement duplicate detection
- generate reference numbers
- store report histories

### Phase 6: Landlord Registration
- build registration form
- support document upload
- set pending review workflow
- show landlord status in dashboard

### Phase 7: Admin Management
- pending landlord queue
- approve/reject actions
- report review and escalation
- audit log viewing
- dashboard metrics

### Phase 8: Frontend Styling
- apply consistent CSS system
- improve mobile responsiveness
- ensure accessible forms and tables
- add clear status indicators

### Phase 9: Testing
- unit tests for services
- integration tests for endpoints
- form validation tests
- role access tests
- database constraint tests

### Phase 10: Deployment Prep
- production settings
- secure secret handling
- database backup strategy
- logging and monitoring

## 11. Key Business Rules

- Search is public and requires no login.
- Scam reports can be submitted by any user.
- Landlord verification requires admin approval.
- Unverified landlords must not appear as verified.
- Not Found does not mean safe.
- Every admin state change must be logged.
- Duplicate reports should be detected or flagged.

## 12. Non-Functional Requirements

- Fast search response under normal load
- Secure password storage
- HTTPS in production
- Reliable audit logging
- Responsive desktop and mobile UI
- Low-friction public access
- Strong validation on all forms

## 13. Suggested Next Step

Create the backend first in this order:
1. project scaffold
2. raw SQL schema and migrations
3. auth and roles
4. public search
5. scam reports
6. landlord registration
7. admin review tools
8. frontend pages
