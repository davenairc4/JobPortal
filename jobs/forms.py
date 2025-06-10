from django import forms
from django.core.exceptions import ValidationError
from .models import RFQTS, Job, Position, Advertisement, JobApplication


class RFQTSForm(forms.ModelForm):
    class Meta:
        model = RFQTS
        fields = '__all__'
        widgets = {
            'commencement_date_for_task': forms.DateInput(attrs={'type': 'date'}),
            'completion_date_for_task': forms.DateInput(attrs={'type': 'date'}),
            'closing_date_for_quotation': forms.DateInput(attrs={'type': 'date'}),
            'scope_of_task': forms.Textarea(attrs={'rows': 4}),
            'deliverables': forms.Textarea(attrs={'rows': 4}),
            'evaluation_criteria': forms.Textarea(attrs={'rows': 4}),
            'rfq_file': forms.FileInput(attrs={
                'accept': '.pdf',
                'class': 'form-control',
                'help_text': 'Upload a PDF file to automatically extract and populate form fields'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rfq_file'].help_text = 'Upload a PDF file to automatically extract and populate form fields'

    def save(self, commit=True):
        """Override save to trigger PDF extraction when file is uploaded"""
        instance = super().save(commit=False)
        
        # Check if a new PDF file was uploaded
        if self.files.get('rfq_file') and commit:
            # Save the instance first to store the file
            instance.save()
            
            # Try to extract data from PDF
            extraction_successful = instance.extract_pdf_data()
            
            if extraction_successful:
                # Save again with extracted data
                instance.save()
            
            return instance
        elif commit:
            instance.save()
            
        return instance


class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        exclude = ['created_by']
        widgets = {
            'commencement_date': forms.DateInput(attrs={'type': 'date'}),
            'completion_date': forms.DateInput(attrs={'type': 'date'}),
            'closing_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 6}),
            'skills_sets': forms.Textarea(attrs={'rows': 4}),
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
    # Override boolean fields to be required checkboxes for declarations
    declaration_complete_correct = forms.BooleanField(
        required=True,
        label="I declare that the information I have provided on this form is complete and correct"
    )
    declaration_no_other_applications = forms.BooleanField(
        required=True,
        label="I declare that no applications for this role have occurred through other agencies"
    )
    understand_false_info = forms.BooleanField(
        required=True,
        label="I understand that giving false or misleading information is considered grounds for dismissal"
    )
    understand_additional_enquiries = forms.BooleanField(
        required=True,
        label="I understand that C4 may make additional enquiries to verify the information provided"
    )
    understand_waiver_approval = forms.BooleanField(
        required=False,
        label="I understand that requests for waiver take 10 business days to be approved (if applicable)"
    )
    written_third_person = forms.BooleanField(
        required=True,
        label="I confirm this application is written in 3rd person (i.e., first name not I, Me, My etc.)"
    )
    cv_no_gaps = forms.BooleanField(
        required=True,
        label="I confirm my CV has no gaps"
    )
    cv_month_year_listed = forms.BooleanField(
        required=True,
        label="I confirm month and year for each past role are listed in the CV"
    )

    class Meta:
        model = JobApplication
        exclude = ['user', 'job', 'submission_date', 'status']
        widgets = {
            # Date fields
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'clearance_expiry_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'earliest_start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'aps_employment_from': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'aps_employment_to': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'sercat_employment_from': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'sercat_employment_to': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'signature_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            
            # Text fields
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First, Middle, Last'}),
            'current_clearance': forms.TextInput(attrs={'class': 'form-control'}),
            'agsva_cs_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'For Defence Clearance Check'}),
            'location_of_residence': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City, State'}),
            'proposed_contract_rate': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '$ per day, ex GST'}),
            'abn': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ABN if contracting'}),
            'proposed_annual_salary': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '$ including Super'}),
            'available_for_interview': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Yes/No - Phone/In-person'}),
            'electronic_signature': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Type your full name'}),
            
            # Email fields
            'referee1_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'referee2_email': forms.EmailInput(attrs={'class': 'form-control'}),
            
            # Phone fields
            'referee1_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'referee2_phone': forms.TextInput(attrs={'class': 'form-control'}),
            
            # Textarea fields
            'planned_leave': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'industry_engagement_experience': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Write in 3rd person'}),
            'project_expectations': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Write in 3rd person'}),
            'qualifications_certifications': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'referee1_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'referee2_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'additional_materials': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'unique_skills': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'aps_engagement_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'sercat_engagement_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'cover_letter': forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
            
            # Radio/Checkbox fields
            'worked_on_project': forms.RadioSelect(choices=[(True, 'Yes'), (False, 'No')]),
            'worked_on_requirement': forms.RadioSelect(choices=[(True, 'Yes'), (False, 'No')]),
            'involved_in_selection': forms.RadioSelect(choices=[(True, 'Yes'), (False, 'No')]),
            'potential_conflict': forms.RadioSelect(choices=[(True, 'Yes'), (False, 'No')]),
            'currently_aps': forms.RadioSelect(choices=[(True, 'Yes'), (False, 'No')]),
            'aps_within_12_months': forms.RadioSelect(choices=[(True, 'Yes'), (False, 'No')]),
            'currently_sercat': forms.RadioSelect(choices=[(True, 'Yes'), (False, 'No')]),
            'sercat_within_12_months': forms.RadioSelect(choices=[(True, 'Yes'), (False, 'No')]),
            
            # File fields
            'resume': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.doc,.docx'}),
            'aps_resignation_evidence': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.png'}),
            'sercat_separation_evidence': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.png'}),
        }
        
        field_order = [
            # Applicant Details
            'full_name', 'current_clearance', 'clearance_expiry_date', 'agsva_cs_number',
            'date_of_birth', 'location_of_residence', 'earliest_start_date',
            'proposed_contract_rate', 'abn', 'proposed_annual_salary',
            'planned_leave', 'available_for_interview',
            
            # Experience Questions
            'industry_engagement_experience', 'project_expectations', 'qualifications_certifications',
            
            # References
            'referee1_name', 'referee1_email', 'referee1_phone', 'referee1_description',
            'referee2_name', 'referee2_email', 'referee2_phone', 'referee2_description',
            
            # Application Confirmation
            'written_third_person', 'cv_no_gaps', 'cv_month_year_listed',
            
            # Additional Information
            'additional_materials', 'unique_skills',
            
            # Conflict of Interest
            'worked_on_project', 'worked_on_requirement', 'involved_in_selection', 'potential_conflict',
            
            # APS/SERCAT Conflicts
            'currently_aps', 'aps_within_12_months', 'aps_engagement_details',
            'aps_employment_from', 'aps_employment_to', 'aps_resignation_evidence',
            'currently_sercat', 'sercat_within_12_months', 'sercat_engagement_details',
            'sercat_employment_from', 'sercat_employment_to', 'sercat_separation_evidence',
            
            # Files and Cover Letter
            'resume', 'cover_letter',
            
            # Declaration
            'declaration_complete_correct', 'declaration_no_other_applications',
            'understand_false_info', 'understand_additional_enquiries', 'understand_waiver_approval',
            
            # Signature
            'electronic_signature', 'signature_date'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Mark some fields as conditionally required
        self.fields['agsva_cs_number'].help_text = "Required if no Date of Birth provided"
        self.fields['date_of_birth'].help_text = "Only needed if AGSVA CS not provided"
        
        # Group fieldsets for template rendering
        self.fieldsets = {
            'applicant_details': [
                'full_name', 'current_clearance', 'clearance_expiry_date', 
                'agsva_cs_number', 'date_of_birth', 'location_of_residence',
                'earliest_start_date', 'proposed_contract_rate', 'abn',
                'proposed_annual_salary', 'planned_leave', 'available_for_interview'
            ],
            'experience': [
                'industry_engagement_experience', 'project_expectations',
                'qualifications_certifications'
            ],
            'references': [
                'referee1_name', 'referee1_email', 'referee1_phone', 'referee1_description',
                'referee2_name', 'referee2_email', 'referee2_phone', 'referee2_description'
            ],
            'application_confirmation': [
                'written_third_person', 'cv_no_gaps', 'cv_month_year_listed'
            ],
            'additional': [
                'additional_materials', 'unique_skills'
            ],
            'conflict_of_interest': [
                'worked_on_project', 'worked_on_requirement', 
                'involved_in_selection', 'potential_conflict'
            ],
            'aps_conflict': [
                'currently_aps', 'aps_within_12_months', 'aps_engagement_details',
                'aps_employment_from', 'aps_employment_to', 'aps_resignation_evidence'
            ],
            'sercat_conflict': [
                'currently_sercat', 'sercat_within_12_months', 'sercat_engagement_details',
                'sercat_employment_from', 'sercat_employment_to', 'sercat_separation_evidence'
            ],
            'documents': [
                'resume', 'cover_letter'
            ],
            'declaration': [
                'declaration_complete_correct', 'declaration_no_other_applications',
                'understand_false_info', 'understand_additional_enquiries',
                'understand_waiver_approval'
            ],
            'signature': [
                'electronic_signature', 'signature_date'
            ]
        }

    def clean(self):
        cleaned_data = super().clean()
        
        # Validate AGSVA CS Number or Date of Birth
        if not cleaned_data.get('agsva_cs_number') and not cleaned_data.get('date_of_birth'):
            raise ValidationError('Either AGSVA CS Number or Date of Birth must be provided')
        
        # Validate APS conflict details
        if cleaned_data.get('currently_aps') and not cleaned_data.get('aps_engagement_details'):
            self.add_error('aps_engagement_details', 'This field is required for current APS employees')
            
        if cleaned_data.get('aps_within_12_months'):
            if not cleaned_data.get('aps_employment_from') or not cleaned_data.get('aps_employment_to'):
                raise ValidationError('APS employment period must be provided')
                
        # Validate SERCAT conflict details  
        if cleaned_data.get('currently_sercat') and not cleaned_data.get('sercat_engagement_details'):
            self.add_error('sercat_engagement_details', 'This field is required for current SERCAT employees')
            
        if cleaned_data.get('sercat_within_12_months'):
            if not cleaned_data.get('sercat_employment_from') or not cleaned_data.get('sercat_employment_to'):
                raise ValidationError('SERCAT employment period must be provided')
        
        # Validate waiver requirement
        if any([cleaned_data.get('currently_aps'), cleaned_data.get('aps_within_12_months'),
                cleaned_data.get('currently_sercat'), cleaned_data.get('sercat_within_12_months')]):
            if not cleaned_data.get('understand_waiver_approval'):
                self.add_error('understand_waiver_approval', 
                             'You must acknowledge the waiver approval timeframe')
        
        return cleaned_data