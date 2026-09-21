from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Review


@admin.action(description='Approve selected reviews')
def approve_selected(modeladmin, request, queryset):
    queryset.update(status=Review.STATUS_APPROVED)


@admin.action(description='Reject selected reviews')
def reject_selected(modeladmin, request, queryset):
    queryset.update(status=Review.STATUS_REJECTED)


@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = ('service', 'reviewer_name', 'rating', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('reviewer_name', 'body', 'service__name')
    readonly_fields = ('service', 'reviewer_name', 'rating', 'body', 'created_at')
    actions = [approve_selected, reject_selected]
