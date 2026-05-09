from django.contrib import admin
from .models import Job, Profile, JobBookmark


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("id", "Title", "Company", "Location", "Year", "Month", "IT")
    list_filter = ("IT", "Year", "Month", "Location")
    search_fields = ("Title", "Company", "Location", "tags")
    ordering = ("-id",)
    list_per_page = 50


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "phone")
    search_fields = ("user__username", "user__email", "phone")


@admin.register(JobBookmark)
class JobBookmarkAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "job", "created_at")
    search_fields = ("user__username", "job__Title", "job__Company")
    list_filter = ("created_at",)
    ordering = ("-created_at",)