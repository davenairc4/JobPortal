from django import forms
from .models import RFQTS, Job, Position, Advertisement, JobApplication


class RFQTSForm(forms.ModelForm):
    class Meta:
        model = RFQTS
        fields = '__all__'
        widgets = {
            'commencement_date_for_task': forms.DateInput(attrs={'type': 'date'}),
            'completion_date_for_task': forms.DateInput(attrs={'type': 'date'}),
            'closing_date_for_quotation': forms.DateInput(attrs={'type': 'date'}),
        }


class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        exclude = ['created_by']
        widgets = {
            'commencement_date': forms.DateInput(attrs={'type': 'date'}),
            'completion_date': forms.DateInput(attrs={'type': 'date'}),
            'closing_date': forms.DateInput(attrs={'type': 'date'}),
        }


class PositionForm(forms.ModelForm):
    class Meta:
        model = Position
        fields = ['title', 'number_of_positions', 'is_filled']


class AdvertisementForm(forms.ModelForm):
    class Meta:
        model = Advertisement
        exclude = ['view_count']
        widgets = {
            'publish_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'expire_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


class JobApplicationForm(forms.ModelForm):
    class Meta:
        model = JobApplication
        exclude = ['user', 'job', 'submission_date', 'status']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'clearance_expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'earliest_start_date': forms.DateInput(attrs={'type': 'date'}),
        }