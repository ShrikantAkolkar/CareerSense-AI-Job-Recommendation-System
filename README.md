# AKS Job Listing - Job Recommendation System

## Overview

**AKS Job Listing** is a portfolio-ready Django application that combines a modern job board UI with an ML-based job recommender.

- **Modern UI**: Bootstrap 5 dashboard layout (hero, filters, responsive cards, toasts)
- **Auth & Profile**: signup/login/logout + profile photo upload and editable details
- **Bookmarks**: save/unsave jobs
- **Recently viewed**: session-based “recent jobs”
- **ML recommendations**: cosine similarity with safe DB ID alignment
- **Admin**: improved admin lists, filters, and search

---

## Key URLs

- `/` : home dashboard (jobs + filters + pagination)
- `/recommend/` : recommendation search (POST)
- `/job/<id>/` : job detail + recommended jobs
- `/saved/` : saved jobs (requires login)
- `/recent/` : recently viewed (requires login)
- `/api/suggestions/?q=data` : search suggestions
- `/admin/` : Django admin

---

## Setup (Windows / PowerShell)

Create and activate a venv:

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run migrations (SQLite):

```bash
python manage.py migrate
```

Add job data (choose one):

### Option A: Demo dataset (quick start)

```bash
python manage.py build_recommender_models --demo
```

### Option B: Your CSV dataset

```bash
python manage.py build_recommender_models --csv "path\to\your_jobs.csv"
```

Create admin user:

```bash
python manage.py createsuperuser
```

Run server:

```bash
python manage.py runserver
```

---

## ML recommender artifacts

Artifacts are saved to:

- `static/models/jobs.pkl`
- `static/models/similarity.pkl`

The builder keeps `jobs.pkl["id"]` aligned to DB `Job.id`, so similarity indices do not break if IDs are not perfectly sequential.

If artifacts are missing, the app attempts to auto-build demo artifacts on first use (useful for first-time runs).

