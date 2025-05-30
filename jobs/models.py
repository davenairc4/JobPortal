import uuid
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from users.models import CustomUser


class RFQTS(models.Model):
    """
    Request for Quotation and Tasking Statement
    """
    rfqts_no = models.CharField(max_length=200, default='RFQ-0000')  
    department = models.CharField(max_length=200, default='General')  
    group = models.CharField(max_length=200, default='Default Group')  
    directorate = models.CharField(max_length=200, default='Default Directorate')  
    project_section = models.CharField(max_length=200, default='Default Project Section') 
    task_title = models.CharField(max_length=200, default='Default Task Title') 
    commencement_date_for_task = models.DateField(null=True, blank=True)  
    completion_date_for_task = models.DateField(null=True, blank=True)  
    rfqts_type = models.CharField(max_length=200, default='General')  
    closing_date_for_quotation = models.DateField(null=True, blank=True)
    skills_sets = models.TextField(default='Default Skills Set')  
    skills_levels = models.CharField(max_length=200, default='Entry Level')  
    service_category = models.CharField(max_length=200, default='Default Service Category')  
    scope_of_task = models.TextField(default='Default Scope') 
    location = models.CharField(max_length=50, default='ACT')  
    deliverables = models.TextField(default='Default Deliverables')
    specified_personnel = models.TextField(default='Not Specified')
    evaluation_criteria = models.TextField(default="evaluate")  
    applicable_standards_or_references = models.TextField(default='None') 
    allowances_or_disbursements = models.TextField(default='None') 
    other_relevant_information_or_special_requirements = models.TextField(default='None')  
    special_conditions = models.TextField(default='None')  
    extension_options = models.TextField(default='None')  
    security_clearances_required_for_personnel = models.TextField(default='None')  
    quote_form_type = models.CharField(max_length=200, default='Standard')
    rfq_file = models.FileField(upload_to='rfq_files/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Request for Quotation and Tasking Statement"
        verbose_name_plural = "Request for Quotation and Tasking Statements"   

    def __str__(self):
        return self.rfqts_no


class Job(models.Model):
    """
    Job listing model linked to a RFQTS
    """
    JOB_TYPES = [
        ('Contract', 'Contract'),
        ('Permanent', 'Permanent'),
        ('Part-time', 'Part-time'),
        ('Casual', 'Casual'),
        ('ICT', 'ICT'),
        ('Engineering', 'Engineering'),
        ('Management', 'Management'),
        ('Accounting', 'Accounting'),
    ]

    LOCATIONS = [
        ('VIC', 'VIC'),
        ('NSW', 'NSW'),
        ('ACT', 'ACT'),
        ('QLD', 'QLD'),
        ('NT', 'NT'),
        ('WA', 'WA'),
        ('SA', 'SA'),
        ('Brisbane', 'Brisbane'),
        ('Canberra', 'Canberra'),
        ('Remote', 'Remote'),
    ]

    CLEARANCE_LEVEL_CHOICES = [
        ('None', 'None'),
        ('Pending', 'Pending'),
        ('Baseline', 'Baseline'),
        ('NV1', 'NV1'),
        ('NV2', 'NV2'),
        ('PV', 'PV'),
    ]

    rfqts = models.ForeignKey(RFQTS, related_name='jobs', on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=200)
    short_description = models.CharField(max_length=200, help_text="Brief summary shown in the job list")
    description = models.TextField()
    location = models.CharField(max_length=50, choices=LOCATIONS, default='ACT')
    job_type = models.CharField(max_length=50, choices=JOB_TYPES, default='Contract')
    salary = models.CharField(max_length=100, default='Negotiable')
    clearance = models.CharField(max_length=20, choices=CLEARANCE_LEVEL_CHOICES, default='None')
    skills_sets = models.TextField(blank=True, null=True)
    skills_levels = models.CharField(max_length=100, blank=True, null=True)
    commencement_date = models.DateField(null=True, blank=True)
    completion_date = models.DateField(null=True, blank=True)
    closing_date = models.DateField(null=True, blank=True)
    submission_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(CustomUser, related_name='created_jobs', on_delete=models.CASCADE)

    class Meta:
        ordering = ['-submission_date']

    def __str__(self):
        return self.title
        
    def clean(self):
        # Validate that commencement date comes before completion date
        if self.commencement_date and self.completion_date:
            if self.commencement_date > self.completion_date:
                raise ValidationError('Commencement date must be before completion date')
        
        # Validate that closing date is not in the past
        if self.closing_date and self.closing_date < timezone.now().date():
            raise ValidationError('Closing date cannot be in the past')


class Position(models.Model):
    """
    Model to track number of positions for a job
    """
    job = models.ForeignKey(Job, related_name='positions', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    number_of_positions = models.PositiveIntegerField(default=1)
    is_filled = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.number_of_positions} positions for {self.title}"


class Advertisement(models.Model):
    """
    Public job advertisement model
    """
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Published', 'Published'),
        ('Expired', 'Expired'),
    ]
    
    job = models.OneToOneField(Job, related_name='advertisement', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft')
    publish_date = models.DateTimeField(null=True, blank=True)
    expire_date = models.DateTimeField(null=True, blank=True)
    is_featured = models.BooleanField(default=False)
    view_count = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"Ad for {self.job.title}"
        
    def clean(self):
        if self.publish_date and self.expire_date:
            if self.publish_date > self.expire_date:
                raise ValidationError('Publish date must be before expire date')


class JobApplication(models.Model):
    """
    Job application model with integrated declaration form
    """
    APPLICATION_STATUS = [
        ('Pending', 'Pending'),
        ('Reviewing', 'Reviewing'),
        ('Interviewed', 'Interviewed'),
        ('Accepted', 'Accepted'),
        ('Rejected', 'Rejected'),
    ]

    # Basic Information
    job = models.ForeignKey(Job, related_name="applications", on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, related_name="applications", on_delete=models.CASCADE)
    
    # Applicant Details
    full_name = models.CharField(max_length=200, verbose_name="Full Name (First, Middle, Last)")
    current_clearance = models.CharField(max_length=200, verbose_name="Current Level of Defence Clearance")
    clearance_expiry_date = models.DateField(null=True, blank=True, verbose_name="Defence Clearance Expiry Date")
    agsva_cs_number = models.CharField(max_length=200, blank=True, verbose_name="AGSVA CS Number")
    date_of_birth = models.DateField(null=True, blank=True, verbose_name="Date of Birth")
    location_of_residence = models.CharField(max_length=200, verbose_name="Location of residence (city, state)")
    earliest_start_date = models.DateField(verbose_name="Earliest date you can start work")
    proposed_contract_rate = models.CharField(max_length=200, blank=True, verbose_name="Proposed contract rate (per day, ex GST)")
    abn = models.CharField(max_length=200, blank=True, verbose_name="ABN")
    proposed_annual_salary = models.CharField(max_length=200, blank=True, verbose_name="Proposed annual salary (including Super)")
    planned_leave = models.TextField(blank=True, verbose_name="Any planned leave?")
    available_for_interview = models.CharField(max_length=200, verbose_name="Available for interview? Phone/In-person?")
    
    # Experience Questions
    industry_engagement_experience = models.TextField(
        verbose_name="Describe your level of knowledge and experience in relation to Industry Engagement Management within Defence, Government or similar industry"
    )
    project_expectations = models.TextField(
        verbose_name="Describe your expectations on joining the project"
    )
    qualifications_certifications = models.TextField(
        verbose_name="Provide details of your qualifications and industry certifications that are relevant to the role"
    )
    
    # References
    referee1_name = models.CharField(max_length=200, verbose_name="Referee 1 Name and Title")
    referee1_email = models.EmailField(verbose_name="Referee 1 Email")
    referee1_phone = models.CharField(max_length=20, verbose_name="Referee 1 Telephone")
    referee1_description = models.TextField(verbose_name="Referee 1 - Brief description of services performed")
    
    referee2_name = models.CharField(max_length=200, verbose_name="Referee 2 Name and Title")
    referee2_email = models.EmailField(verbose_name="Referee 2 Email")
    referee2_phone = models.CharField(max_length=20, verbose_name="Referee 2 Telephone")
    referee2_description = models.TextField(verbose_name="Referee 2 - Brief description of services performed")
    
    # Additional Information
    additional_materials = models.TextField(
        blank=True,
        verbose_name="Additional materials to include with application",
        help_text="List any referee reports, letters of merit/appreciation, awards etc."
    )
    unique_skills = models.TextField(
        blank=True,
        verbose_name="Unique skills or experience",
        help_text="Provide details on any unique skills or experience not identified in prior questions"
    )
    
    # Conflict of Interest - Role
    worked_on_project = models.BooleanField(
        default=False,
        verbose_name="Have you been working on this Project in any capacity within the last 6 months?"
    )
    worked_on_requirement = models.BooleanField(
        default=False,
        verbose_name="Have you been working on this requirement in any capacity within the last 12 months?"
    )
    involved_in_selection = models.BooleanField(
        default=False,
        verbose_name="Have you been involved in the selection of the associated Service Providers in any capacity?"
    )
    potential_conflict = models.BooleanField(
        default=False,
        verbose_name="Is there a potential for a real or perceived conflict of interest or a probity objection if you perform or contribute to the Project?"
    )
    
    # APS Defence Conflict of Interest
    currently_aps = models.BooleanField(
        default=False,
        verbose_name="Are you currently employed in Defence as a Public Servant?"
    )
    aps_within_12_months = models.BooleanField(
        default=False,
        verbose_name="Have you been employed in Defence as a Public Servant within the last 12 months?"
    )
    
    # APS Employment Details (if applicable)
    aps_engagement_details = models.TextField(
        blank=True,
        verbose_name="Details of your most recent area of engagement"
    )
    aps_employment_from = models.DateField(
        null=True, blank=True,
        verbose_name="APS Employment Period - From"
    )
    aps_employment_to = models.DateField(
        null=True, blank=True,
        verbose_name="APS Employment Period - To"
    )
    aps_resignation_evidence = models.FileField(
        upload_to='aps_resignations/', 
        blank=True, null=True,
        verbose_name="Evidence of Resignation from the APS"
    )
    
    # SERCAT Employment
    currently_sercat = models.BooleanField(
        default=False,
        verbose_name="Are you currently employed in Defence as SERCAT 1, 6 or 7?"
    )
    sercat_within_12_months = models.BooleanField(
        default=False,
        verbose_name="Have you been employed (excluding SERCAT 2-5) in the ADF within the last 12 months?"
    )
    
    # SERCAT Employment Details (if applicable)
    sercat_engagement_details = models.TextField(
        blank=True,
        verbose_name="Details of your most recent engagement"
    )
    sercat_employment_from = models.DateField(
        null=True, blank=True,
        verbose_name="SERCAT Employment Period - From"
    )
    sercat_employment_to = models.DateField(
        null=True, blank=True,
        verbose_name="SERCAT Employment Period - To"
    )
    sercat_separation_evidence = models.FileField(
        upload_to='sercat_separations/', 
        blank=True, null=True,
        verbose_name="Evidence of Separation from ADF"
    )
    
    # Application Confirmation
    written_third_person = models.BooleanField(
        default=False,
        verbose_name="Application is written in 3rd person"
    )
    cv_no_gaps = models.BooleanField(
        default=False,
        verbose_name="CV has no gaps"
    )
    cv_month_year_listed = models.BooleanField(
        default=False,
        verbose_name="Month and year for each past role are listed in the CV"
    )
    
    # Declaration
    declaration_complete_correct = models.BooleanField(
        default=False,
        verbose_name="I declare that the information I have provided on this form is complete and correct"
    )
    declaration_no_other_applications = models.BooleanField(
        default=False,
        verbose_name="I declare that no applications for this role have occurred through other agencies"
    )
    understand_false_info = models.BooleanField(
        default=False,
        verbose_name="I understand that giving false or misleading information is considered grounds for dismissal"
    )
    understand_additional_enquiries = models.BooleanField(
        default=False,
        verbose_name="I understand that C4 may make additional enquiries to verify the information provided"
    )
    understand_waiver_approval = models.BooleanField(
        default=False,
        verbose_name="I understand that requests for waiver take 10 business days to be approved"
    )
    
    # Files
    resume = models.FileField(upload_to='resumes/', verbose_name="CV/Resume")
    cover_letter = models.TextField(blank=True, verbose_name="Cover Letter")
    
    # Metadata
    submission_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=APPLICATION_STATUS, default="Pending")
    
    # Signature
    electronic_signature = models.CharField(
        max_length=200,
        verbose_name="Electronic Signature (Type your full name)"
    )
    signature_date = models.DateField(
        default=timezone.now,
        verbose_name="Signature Date"
    )

    def __str__(self):
        return f"Application for {self.job.title} by {self.full_name}"
    
    def clean(self):
        # Validate conflict of interest responses
        if self.currently_aps and not self.aps_engagement_details:
            raise ValidationError('Please provide details of your APS engagement')
            
        if self.aps_within_12_months and not all([self.aps_employment_from, self.aps_employment_to]):
            raise ValidationError('Please provide APS employment period details')
            
        if self.currently_sercat and not self.sercat_engagement_details:
            raise ValidationError('Please provide details of your SERCAT engagement')
            
        if self.sercat_within_12_months and not all([self.sercat_employment_from, self.sercat_employment_to]):
            raise ValidationError('Please provide SERCAT employment period details')
            
        # Validate all declaration checkboxes are checked
        if not all([
            self.declaration_complete_correct,
            self.declaration_no_other_applications,
            self.understand_false_info,
            self.understand_additional_enquiries
        ]):
            raise ValidationError('All declaration statements must be acknowledged')
            
        # Validate application confirmation
        if not all([self.written_third_person, self.cv_no_gaps, self.cv_month_year_listed]):
            raise ValidationError('Please confirm all application requirements are met')