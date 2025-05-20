from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser, UserProfile


class CustomUserCreationForm(UserCreationForm):
    is_employer = forms.BooleanField(required=False)
    is_job_seeker = forms.BooleanField(required=False)
    
    class Meta:
        model = CustomUser
        fields = ('email', 'is_employer', 'is_job_seeker')


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('email', 'is_employer', 'is_job_seeker')


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('first_name', 'last_name', 'phone_number', 'resume')