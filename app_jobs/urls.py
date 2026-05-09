from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import (
    all_jobs_view,
    job_detail_view,
    job_recommendation_view,
    signup_view,
    profile_view,
    profile_update_view,
    bookmark_toggle_view,
    bookmarks_view,
    recent_view,
    search_suggestions_view,
)

urlpatterns = [
    path('', all_jobs_view, name="all_jobs"),
    path('jobs/', all_jobs_view, name="all_jobs"),
    path('recommend/', job_recommendation_view, name="job_recommendation"),
    path('job/<int:job_id>/', job_detail_view, name="job_detail"),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile/', profile_view, name='profile'),
    path('profile/update/', profile_update_view, name='profile_update'),
    path('signup/', signup_view, name='signup'),
    path('bookmark/<int:job_id>/', bookmark_toggle_view, name='bookmark_toggle'),
    path('saved/', bookmarks_view, name='bookmarks'),
    path('recent/', recent_view, name='recent'),
    path('api/suggestions/', search_suggestions_view, name='search_suggestions'),
]