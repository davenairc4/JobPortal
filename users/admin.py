from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('email', 'is_employer', 'is_job_seeker', 'is_staff', 'is_active',)
    list_filter = ('email', 'is_employer', 'is_job_seeker', 'is_staff', 'is_active',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_employer', 'is_job_seeker')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_active', 'is_employer', 'is_job_seeker')}
        ),
    )
    search_fields = ('email',)
    ordering = ('email',)
    inlines = [UserProfileInline]


admin.site.register(CustomUser, CustomUserAdmin)