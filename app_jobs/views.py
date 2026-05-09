from __future__ import annotations

from typing import Dict, List, Tuple

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from .forms import ProfileForm, SignupForm, UserUpdateForm
from .models import Job, JobBookmark, Profile
from .recommender import (
    load_artifacts,
    recommend_job_ids_by_index,
    resolve_title_to_index,
)


FEATURED_COMPANIES = [
    "Infosys",
    "TCS",
    "Wipro",
    "Capgemini",
    "Tech Mahindra",
    "Cognizant",
    "Accenture",
    "HCL",
]


def _filters_from_request(request: HttpRequest) -> Dict[str, str]:
    return {
        "Location": (request.GET.get("location") or "").strip(),
        "Year": (request.GET.get("year") or "").strip(),
        "Month": (request.GET.get("month") or "").strip(),
        "IT": (request.GET.get("it") or "").strip(),
    }


def _apply_filters(qs, filters: Dict[str, str]):
    if filters["Location"]:
        qs = qs.filter(Location=filters["Location"])
    if filters["Year"].isdigit():
        qs = qs.filter(Year=int(filters["Year"]))
    if filters["Month"].isdigit():
        qs = qs.filter(Month=int(filters["Month"]))
    if filters["IT"] in ("True", "False"):
        qs = qs.filter(IT=(filters["IT"] == "True"))
    return qs


def _filter_choices() -> Tuple[List[str], List[int], List[int], List[str]]:
    locations = list(
        Job.objects.values_list("Location", flat=True)
        .exclude(Location=None)
        .annotate(num=Count("Location"))
        .order_by("-num")[:100]
    )
    years = sorted(Job.objects.exclude(Year=None).values_list("Year", flat=True).distinct())
    months = sorted(Job.objects.exclude(Month=None).values_list("Month", flat=True).distinct())
    its = ["True", "False"]
    return locations, years, months, its


def _recent_ids(request: HttpRequest) -> List[int]:
    raw = request.session.get("recent_job_ids", [])
    out: List[int] = []
    for x in raw:
        try:
            out.append(int(x))
        except Exception:
            continue
    return out


def _push_recent(request: HttpRequest, job_id: int, limit: int = 10) -> None:
    ids = _recent_ids(request)
    if job_id in ids:
        ids.remove(job_id)
    ids.insert(0, job_id)
    request.session["recent_job_ids"] = ids[:limit]
    request.session.modified = True


def all_jobs_view(request: HttpRequest) -> HttpResponse:
    """
    Modern dashboard-like home page.
    - GET: show filtered/paginated jobs
    - POST: treat as recommendation search and show recommended jobs
    """
    filters = _filters_from_request(request)
    locations, years, months, its = _filter_choices()

    jobs_qs = Job.objects.all().only(
        "id",
        "Title",
        "Company",
        "Location",
        "Year",
        "Month",
        "IT",
    )
    jobs_qs = _apply_filters(jobs_qs, filters).order_by("-id")

    matched_title = None
    error = None

    if request.method == "POST":
        title = (request.POST.get("job_title") or "").strip()
        artifacts = load_artifacts()
        idx = resolve_title_to_index(artifacts, title)
        if idx is None:
            error = "We couldn't find that job title. Try a different spelling or choose a suggestion."
            messages.warning(request, error)
        else:
            matched_title = artifacts.jobs.iloc[idx]["Title"]
            rec_ids = recommend_job_ids_by_index(artifacts, job_index=idx, top_n=5)
            jobs_qs = Job.objects.filter(id__in=rec_ids).only(
                "id",
                "Title",
                "Company",
                "Location",
                "Year",
                "Month",
                "IT",
            )
            # Preserve recommendation order
            id_to_pos = {jid: i for i, jid in enumerate(rec_ids)}
            jobs_qs = sorted(list(jobs_qs), key=lambda j: id_to_pos.get(j.id, 9999))

            # Show recommendations as a single page "jobs_page" list.
            page_obj = None
            jobs_page = jobs_qs
            featured_jobs = Job.objects.order_by("-id")[:6]
            bookmarked_ids = set()
            if request.user.is_authenticated:
                bookmarked_ids = set(
                    JobBookmark.objects.filter(user=request.user).values_list("job_id", flat=True)
                )
            recent_jobs = Job.objects.filter(id__in=_recent_ids(request))[:5]
            return render(
                request,
                "index.html",
                {
                    "filters": filters,
                    "locations": locations,
                    "years": years,
                    "months": months,
                    "its": its,
                    "featured_companies": FEATURED_COMPANIES,
                    "featured_jobs": featured_jobs,
                    "jobs_page": jobs_page,
                    "page_obj": page_obj,
                    "query_params": dict(request.GET.items()),
                    "matched_title": matched_title,
                    "error": error,
                    "bookmarked_ids": bookmarked_ids,
                    "recent_jobs": recent_jobs,
                },
            )

    paginator = Paginator(jobs_qs, 12)
    page_obj = paginator.get_page(request.GET.get("page") or 1)
    jobs_page = page_obj.object_list

    featured_jobs = Job.objects.order_by("-id")[:6]

    bookmarked_ids = set()
    if request.user.is_authenticated:
        bookmarked_ids = set(
            JobBookmark.objects.filter(user=request.user).values_list("job_id", flat=True)
        )
    recent_jobs = Job.objects.filter(id__in=_recent_ids(request))[:5]

    return render(
        request,
        "index.html",
        {
            "filters": filters,
            "locations": locations,
            "years": years,
            "months": months,
            "its": its,
            "featured_companies": FEATURED_COMPANIES,
            "featured_jobs": featured_jobs,
            "jobs_page": jobs_page,
            "page_obj": page_obj,
            "query_params": dict(request.GET.items()),
            "matched_title": matched_title,
            "error": error,
            "bookmarked_ids": bookmarked_ids,
            "recent_jobs": recent_jobs,
        },
    )


@require_POST
def job_recommendation_view(request: HttpRequest) -> HttpResponse:
    # Same UI, separate URL for clarity and easier form actions.
    return all_jobs_view(request)


def job_detail_view(request: HttpRequest, job_id: int) -> HttpResponse:
    job = get_object_or_404(Job, id=job_id)
    _push_recent(request, job_id=job_id)

    artifacts = load_artifacts()
    job_index = artifacts.id_to_index.get(job_id)
    rec_jobs = []
    if job_index is not None:
        rec_ids = recommend_job_ids_by_index(artifacts, job_index=job_index, top_n=5)
        qs = Job.objects.filter(id__in=rec_ids).only("id", "Title", "Company", "Location", "Year", "IT")
        id_to_pos = {jid: i for i, jid in enumerate(rec_ids)}
        rec_jobs = sorted(list(qs), key=lambda j: id_to_pos.get(j.id, 9999))

    is_bookmarked = False
    if request.user.is_authenticated:
        is_bookmarked = JobBookmark.objects.filter(user=request.user, job=job).exists()

    return render(
        request,
        "job_detail.html",
        {"job": job, "recommended_jobs": rec_jobs, "is_bookmarked": is_bookmarked},
    )


@login_required
def profile_view(request: HttpRequest) -> HttpResponse:
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return render(request, "profile.html", {"profile": profile})


def signup_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully. Welcome!")
            return redirect("all_jobs")
    else:
        form = SignupForm()
    return render(request, "signup.html", {"form": form})


@login_required
def profile_update_view(request: HttpRequest) -> HttpResponse:
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Profile updated.")
            return redirect("profile")
        messages.error(request, "Please fix the errors below.")
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileForm(instance=profile)
    return render(
        request,
        "profile_update.html",
        {"user_form": user_form, "profile_form": profile_form, "profile": profile},
    )


@login_required
@require_POST
def bookmark_toggle_view(request: HttpRequest, job_id: int) -> HttpResponse:
    job = get_object_or_404(Job, id=job_id)
    obj, created = JobBookmark.objects.get_or_create(user=request.user, job=job)
    if not created:
        obj.delete()
        messages.info(request, "Removed from saved jobs.")
    else:
        messages.success(request, "Saved job.")
    return redirect(request.META.get("HTTP_REFERER") or reverse("job_detail", args=[job_id]))


@login_required
def bookmarks_view(request: HttpRequest) -> HttpResponse:
    bookmarks = (
        JobBookmark.objects.filter(user=request.user)
        .select_related("job")
        .only("id", "created_at", "job__id", "job__Title", "job__Company", "job__Location", "job__Year", "job__Month", "job__IT")
    )
    jobs = [b.job for b in bookmarks]
    page_obj = Paginator(jobs, 12).get_page(request.GET.get("page") or 1)
    return render(
        request,
        "index.html",
        {
            "filters": {"Location": "", "Year": "", "Month": "", "IT": ""},
            "locations": [],
            "years": [],
            "months": [],
            "its": ["True", "False"],
            "featured_companies": FEATURED_COMPANIES,
            "featured_jobs": [],
            "jobs_page": page_obj.object_list,
            "page_obj": page_obj,
            "query_params": dict(request.GET.items()),
            "matched_title": "Saved jobs",
            "error": None,
            "bookmarked_ids": set(j.id for j in jobs),
            "recent_jobs": Job.objects.filter(id__in=_recent_ids(request))[:5],
        },
    )


@login_required
def recent_view(request: HttpRequest) -> HttpResponse:
    ids = _recent_ids(request)
    qs = Job.objects.filter(id__in=ids).only("id", "Title", "Company", "Location", "Year", "Month", "IT")
    id_to_pos = {jid: i for i, jid in enumerate(ids)}
    jobs = sorted(list(qs), key=lambda j: id_to_pos.get(j.id, 9999))
    page_obj = Paginator(jobs, 12).get_page(request.GET.get("page") or 1)
    bookmarked_ids = set()
    if request.user.is_authenticated:
        bookmarked_ids = set(
            JobBookmark.objects.filter(user=request.user).values_list("job_id", flat=True)
        )
    return render(
        request,
        "index.html",
        {
            "filters": {"Location": "", "Year": "", "Month": "", "IT": ""},
            "locations": [],
            "years": [],
            "months": [],
            "its": ["True", "False"],
            "featured_companies": FEATURED_COMPANIES,
            "featured_jobs": [],
            "jobs_page": page_obj.object_list,
            "page_obj": page_obj,
            "query_params": dict(request.GET.items()),
            "matched_title": "Recently viewed",
            "error": None,
            "bookmarked_ids": bookmarked_ids,
            "recent_jobs": jobs[:5],
        },
    )


@require_GET
def search_suggestions_view(request: HttpRequest) -> JsonResponse:
    q = (request.GET.get("q") or "").strip().casefold()
    if len(q) < 2:
        return JsonResponse({"titles": []})
    artifacts = load_artifacts()
    titles = artifacts.jobs["Title"].fillna("").astype(str).tolist()
    out: List[str] = []
    for t in titles:
        if q in t.casefold():
            out.append(t)
        if len(out) >= 8:
            break
    return JsonResponse({"titles": out})