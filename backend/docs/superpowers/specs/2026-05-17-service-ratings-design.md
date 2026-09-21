# Service Ratings — Design Spec

**Date:** 2026-05-17
**Status:** Approved

---

## Overview

Allow any visitor to submit a star rating + written review for a service listing. Reviews are held in a `pending` state until an admin approves or rejects them. Approved reviews appear on the service detail page; the average star rating appears on service listing cards.

---

## Data Model

New `reviews` Django app with a single `Review` model.

| Field | Type | Notes |
|---|---|---|
| `service` | `ForeignKey(Service, on_delete=CASCADE, related_name='reviews')` | The service being reviewed |
| `reviewer_name` | `CharField(max_length=100)` | Displayed publicly |
| `rating` | `PositiveSmallIntegerField` | Validated 1–5 inclusive |
| `body` | `TextField` | Written review text |
| `status` | `CharField(max_length=10)` | Choices: `pending` / `approved` / `rejected`; default `pending` |
| `created_at` | `DateTimeField(auto_now_add=True)` | |

Average rating is computed dynamically via `Avg('reviews__rating', filter=Q(reviews__status='approved'))` — no denormalised field.

---

## Submission

- A review form appears at the bottom of the service detail page.
- Fields: **Reviewer Name**, **Rating** (1–5 star selector), **Review** (textarea).
- Submits via `POST /services/<slug>/reviews/add/`.
- On success: Django flash message *"Thanks! Your review has been submitted and is awaiting approval."* — redirect back to the service detail page.
- On validation failure: form re-rendered with errors inline.
- No login required. No confirmation number required.

---

## Display

### Service detail page

- A **Reviews** section below the service description.
- Lists all `approved` reviews: star display (Bootstrap Icons filled/empty), reviewer name, date, body.
- If no approved reviews: *"No reviews yet — be the first!"*
- Submission form rendered below the reviews list (always visible).

### Service listing cards (`partials/service_card.html`)

- If a service has ≥ 1 approved review, show average rating as `★ 4.3 (12)` next to the price.
- No badge shown if zero approved reviews.

---

## Admin

`ReviewAdmin` in `reviews/admin.py`:

- `list_display`: service name, reviewer name, rating, status, created_at.
- `list_filter`: status.
- `search_fields`: reviewer_name, body, service__name.
- Two bulk actions: **Approve selected** and **Reject selected** — flip status on all selected rows in one click.
- No inline editing of reviewer content (integrity).

---

## URL & View

| Method | URL | View | Purpose |
|---|---|---|---|
| POST | `/services/<slug>/reviews/add/` | `add_review` | Create a pending Review |

`add_review` is POST-only. On GET it redirects to the service detail page.

The `service_detail` view (in `services/views.py`) is updated to:
1. Annotate the service queryset with `avg_rating`.
2. Pass `reviews` (approved, ordered by `-created_at`) and `review_form` (blank `ReviewForm`) to context.

---

## Files Changed / Created

**New files:**
- `reviews/__init__.py`
- `reviews/models.py`
- `reviews/admin.py`
- `reviews/forms.py`
- `reviews/views.py`
- `reviews/urls.py`
- `reviews/tests.py`
- `reviews/migrations/0001_initial.py`

**Modified files:**
- `config/settings.py` — add `'reviews'` to `INSTALLED_APPS`
- `config/urls.py` — include `reviews.urls`
- `services/views.py` — annotate `service_detail` with `avg_rating`; add `reviews` + `review_form` to context
- `templates/services/detail.html` — reviews section + submission form
- `templates/partials/service_card.html` — star badge

---

## Testing

All tests use real PostgreSQL (no SQLite, no mocks per project convention).

| Test | What it checks |
|---|---|
| `ReviewModelTest.test_default_status_pending` | New review defaults to `pending` |
| `ReviewModelTest.test_rating_validation` | Rating < 1 or > 5 raises ValidationError |
| `ReviewFormTest.test_blank_fields_invalid` | Empty reviewer_name / body / rating fails validation |
| `ReviewFormTest.test_valid_submission` | Valid form data creates a Review |
| `AddReviewViewTest.test_post_creates_pending_review` | POST to add_review creates a Review with status=pending |
| `AddReviewViewTest.test_get_redirects` | GET to add_review redirects to service detail |
| `AddReviewViewTest.test_invalid_post_rerenders` | Invalid POST returns form with errors |
| `ServiceDetailContextTest.test_approved_reviews_in_context` | Only approved reviews appear in context |
| `ServiceDetailContextTest.test_avg_rating_annotated` | avg_rating correct when approved reviews exist |
| `ServiceDetailContextTest.test_pending_not_in_context` | Pending reviews excluded from context |
| `ReviewAdminActionTest.test_bulk_approve` | Bulk approve action sets status=approved |
| `ReviewAdminActionTest.test_bulk_reject` | Bulk reject action sets status=rejected |
