from django.contrib import admin
from .models import RFQTS, Job, Position, Advertisement, JobApplication


@admin.register(RFQTS)
class RFQTSAdmin(admin.ModelAdmin):
    list_display = ('rfqts_no', 'department', 'task_title', 'commencement_date_for_task', 'completion_date_for_task')
    search_fields = ('rfqts_no', 'task_title', 'department')
    list_filter = ('department', 'rfqts_type')


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'location', 'job_type', 'is_active', 'closing_date')
    search_fields = ('title', 'short_description')
    list_filter = ('job_type', 'location', 'is_active')


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('title', 'job', 'number_of_positions', 'is_filled')
    search_fields = ('title', 'job__title')
    list_filter = ('is_filled',)


@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = ('job', 'status', 'publish_date', 'expire_date', 'is_featured', 'view_count')
    search_fields = ('job__title',)
    list_filter = ('status', 'is_featured')


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'job', 'submission_date', 'status')
    search_fields = ('full_name', 'job__title')
    list_filter = ('status', 'submission_date')