from .models import Profile


def navbar_profile(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {"nav_profile": None}
    try:
        profile, _ = Profile.objects.get_or_create(user=request.user)
        return {"nav_profile": profile}
    except Exception:
        return {"nav_profile": None}

