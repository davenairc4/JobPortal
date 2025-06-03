import uuid
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from users.models import CustomUser

from django.db.models.signals import post_save
from django.dispatch import receiver


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

# ═════════════════════════════════════════════════════════════════════════════
# QUOTATION MODELS - Structured according to DSS Deed Quotation Form
# ═════════════════════════════════════════════════════════════════════════════


class Quotation(models.Model):
    """
    QUOTATION
    Under Defence Support Services (DSS) Standing Offer Deed
    The Service Provider submits this Quotation in accordance with the Deed and 
    in response to the Commonwealth Request for Quotation and Tasking Statement.
    """
    
    EMPLOYEE_COUNT_CHOICES = [
        ('4_or_less', '4 or less'),
        ('5_to_19', '5 to 19'),
        ('20_to_99', '20 to 99'),
        ('100_to_199', '100 to 199'),
        ('200_or_more', '200 or more'),
    ]

    application = models.OneToOneField(
        JobApplication,
        on_delete=models.CASCADE,
        related_name="quotation",
        primary_key=True,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # BASIC QUOTATION DETAILS
    # ─────────────────────────────────────────────────────────────────────────
    rfqts_no = models.CharField(
        "RFQTS No.", 
        max_length=100, 
        blank=True,
        help_text="Request for Quotation and Tasking Statement Number"
    )
    task_title = models.CharField(
        "Task Title", 
        max_length=255, 
        blank=True
    )
    service_provider_name = models.CharField(
        "Service Provider Name", 
        max_length=255, 
        blank=True
    )
    service_provider_abn = models.CharField(
        "Service Provider ABN", 
        max_length=50, 
        blank=True
    )
    service_provider_employee_count = models.CharField(
        "How many full time employees (or equivalent) does the Service Provider have?",
        max_length=20,
        choices=EMPLOYEE_COUNT_CHOICES,
        blank=True
    )

    # ─────────────────────────────────────────────────────────────────────────
    # LOCATION
    # ─────────────────────────────────────────────────────────────────────────
    location = models.CharField(
        "Location", 
        max_length=255, 
        blank=True,
        help_text="Location where services will be provided"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # SPECIFIED PERSONNEL
    # ─────────────────────────────────────────────────────────────────────────
    complies_clause_2_4 = models.BooleanField(
        "The Service Provider confirms that any Specified Personnel comply with Clause 2.4 of the DSS Deed",
        default=True,
        help_text="If no, having regard to clause 2.4.6, the Service Provider must submit a request for written approval not less than 10 working days prior to a response from the Deed Manager being required."
    )
    personnel_cv_attached = models.BooleanField(
        "Specified Personnel CV(s) Attached (if applicable)",
        default=False
    )

    # ─────────────────────────────────────────────────────────────────────────
    # SUBCONTRACTORS TO BE USED IN PROVIDING THE SERVICES
    # ─────────────────────────────────────────────────────────────────────────
    subcontractor_cv_attached = models.BooleanField(
        "Subcontractor Personnel CV(s) Attached (if applicable)",
        default=False
    )
    subcontractor_employee_count = models.CharField(
        "How many full time employees (or equivalent) does the Subcontractor have?",
        max_length=20,
        choices=EMPLOYEE_COUNT_CHOICES,
        blank=True
    )
    subcontractors_indigenous_enterprise = models.BooleanField(
        "Are any of the subcontractors an Indigenous enterprise for the purposes of the Commonwealth's Indigenous Procurement Policy?",
        default=False
    )

    # ─────────────────────────────────────────────────────────────────────────
    # SECURITY REQUIREMENTS
    # ─────────────────────────────────────────────────────────────────────────
    security_clearance_comments = models.TextField(
        "Comments relating Security Clearance requirements",
        blank=True,
        help_text="Details about security clearance requirements for personnel"
    )
    security_guidance_comments = models.TextField(
        "Comments relating Security Guidance",
        blank=True,
        help_text="Comments about security guidance compliance"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # KEY RESULT AREAS
    # ─────────────────────────────────────────────────────────────────────────
    key_result_areas = models.TextField(
        "Agreement with Commonwealth proposed Key Result Areas",
        blank=True,
        help_text="Confirmation of agreement with proposed KRAs"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # CURRENCY OF INSURANCES DETAILED BELOW
    # ─────────────────────────────────────────────────────────────────────────
    workers_compensation = models.CharField(
        "Workers Compensation",
        max_length=100,
        blank=True,
        help_text="Yes/No - Current workers compensation insurance"
    )
    professional_indemnity = models.CharField(
        "Professional Indemnity",
        max_length=100,
        blank=True,
        help_text="Yes/No - Current professional indemnity insurance"
    )
    public_liability = models.CharField(
        "Public Liability",
        max_length=100,
        blank=True,
        help_text="Yes/No - Current public liability insurance"
    )
    other_insurance_details = models.TextField(
        "Other Task Specific insurances required",
        blank=True,
        help_text="Details of any other specific insurance requirements"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # SERVICES
    # ─────────────────────────────────────────────────────────────────────────
    methodology = models.TextField(
        "Methodology proposed to provide the Services",
        blank=True,
        help_text="Detailed methodology for service delivery"
    )
    plans_attached = models.TextField(
        "Copies of the following plans are attached",
        blank=True,
        help_text="List any plans or documents attached"
    )
    gfm = models.TextField(
        "GFM",
        blank=True,
        help_text="Government Furnished Materials - If Special Condition 2 applies, detail any changes to the GFM detailed in the GFM table provided in the RFQTS"
    )
    third_party_ip = models.TextField(
        "Third Party and/or Background IP that is proposed to be used in the Contract",
        blank=True,
        help_text="Details of any third party or background intellectual property"
    )
    confidential_info = models.TextField(
        "Information that the Service Provider claims is Confidential Information",
        blank=True,
        help_text="Information claimed as confidential"
    )
    conflict_of_interest = models.BooleanField(
        "Confirmation that no Conflict of Interest exists, or is anticipated to arise in the course of the Contract in accordance with Clause 2.3 of the DSS Deed",
        default=False
    )
    executed_confidentiality_deed = models.BooleanField(
        "Confirmation that an Executed Deed of Confidentiality will be provided if required by the Commonwealth",
        default=False
    )
    other_services_comments = models.TextField(
        "Others",
        blank=True,
        help_text="Any other relevant information about services"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # DELIVERY SCHEDULE AND PRICING DETAILS (GST Inclusive)
    # ─────────────────────────────────────────────────────────────────────────
    
    # Time and Materials Totals
    time_materials_sub_total = models.DecimalField(
        "Sub-total (Time and Materials)",
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Sub-total for time and materials items"
    )
    time_materials_allowances = models.DecimalField(
        "Allowances - Travel, Accommodation and Other Approved Expenses (Time and Materials)",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    time_materials_other_disbursements = models.DecimalField(
        "Other proposed disbursements (Time and Materials)",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    time_materials_total = models.DecimalField(
        "Time and Materials Total",
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )

    # Fixed Price Totals
    fixed_price_sub_total = models.DecimalField(
        "Sub-total (Fixed Price)",
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Sub-total for fixed price deliverables"
    )
    fixed_price_allowances = models.DecimalField(
        "Allowances - Travel, Accommodation and Other Approved Expenses (Fixed Price)",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    fixed_price_other_disbursements = models.DecimalField(
        "Other proposed disbursements (Fixed Price)",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    fixed_price_total = models.DecimalField(
        "Fixed Price Total",
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )

    # ─────────────────────────────────────────────────────────────────────────
    # TOTAL PRICE OF CONTRACT
    # ─────────────────────────────────────────────────────────────────────────
    total_price = models.DecimalField(
        "TOTAL PRICE (All prices are GST inclusive)",
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total contract price including GST"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # DECLINE TO BID
    # ─────────────────────────────────────────────────────────────────────────
    decline_to_bid = models.BooleanField(
        "Declining to Bid",
        default=False,
        help_text="Check if declining to bid for this contract"
    )
    decline_no_personnel = models.BooleanField(
        "No personnel available/qualified",
        default=False
    )
    decline_full_capacity = models.BooleanField(
        "Currently working at full capacity",
        default=False
    )
    decline_unable_location = models.BooleanField(
        "Unable to work in specified location",
        default=False
    )
    decline_insufficient_time = models.BooleanField(
        "Insufficient Quotation Response Period",
        default=False
    )
    decline_conflict_interest = models.BooleanField(
        "Conflict of Interest",
        default=False
    )
    decline_other = models.BooleanField(
        "Other",
        default=False
    )
    decline_other_reason = models.TextField(
        "Other reason for declining (please specify)",
        blank=True
    )

    # ─────────────────────────────────────────────────────────────────────────
    # QUOTATION AUTHORISED BY THE SERVICE PROVIDER
    # ─────────────────────────────────────────────────────────────────────────
    rep_title = models.CharField(
        "Title",
        max_length=100,
        blank=True,
        help_text="Title of company representative authorising this quotation"
    )
    rep_name = models.CharField(
        "Name",
        max_length=100,
        blank=True,
        help_text="Name of company representative authorising this quotation"
    )
    rep_position = models.CharField(
        "Position",
        max_length=100,
        blank=True,
        help_text="Position of company representative"
    )
    rep_email = models.EmailField(
        "Email",
        blank=True,
        help_text="Email address of company representative"
    )
    rep_telephone = models.CharField(
        "Telephone",
        max_length=50,
        blank=True,
        help_text="Telephone number of company representative"
    )
    
    # Address
    address_line1 = models.CharField(
        "Address Line 1",
        max_length=255,
        blank=True
    )
    address_line2 = models.CharField(
        "Address Line 2",
        max_length=255,
        blank=True
    )
    suburb = models.CharField(
        "Suburb",
        max_length=100,
        blank=True
    )
    state = models.CharField(
        "State",
        max_length=100,
        blank=True
    )
    postcode = models.CharField(
        "Postcode",
        max_length=20,
        blank=True
    )
    
    # Signature and Date
    signature = models.CharField(
        "Signature",
        max_length=200,
        blank=True,
        help_text="Electronic signature of authorised representative"
    )
    signature_date = models.DateField(
        "Date",
        null=True,
        blank=True,
        help_text="Date of quotation authorisation"
    )

    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Quotation"
        verbose_name_plural = "Quotations"

    def __str__(self):
        return f"Quotation for {self.application.full_name} — {self.rfqts_no or 'TBC'}"

    def save(self, *args, **kwargs):
        # Auto-calculate totals
        if self.time_materials_sub_total or self.time_materials_allowances or self.time_materials_other_disbursements:
            total = 0
            if self.time_materials_sub_total:
                total += self.time_materials_sub_total
            if self.time_materials_allowances:
                total += self.time_materials_allowances
            if self.time_materials_other_disbursements:
                total += self.time_materials_other_disbursements
            self.time_materials_total = total

        if self.fixed_price_sub_total or self.fixed_price_allowances or self.fixed_price_other_disbursements:
            total = 0
            if self.fixed_price_sub_total:
                total += self.fixed_price_sub_total
            if self.fixed_price_allowances:
                total += self.fixed_price_allowances
            if self.fixed_price_other_disbursements:
                total += self.fixed_price_other_disbursements
            self.fixed_price_total = total

        # Calculate overall total
        overall_total = 0
        if self.time_materials_total:
            overall_total += self.time_materials_total
        if self.fixed_price_total:
            overall_total += self.fixed_price_total
        if overall_total > 0:
            self.total_price = overall_total

        super().save(*args, **kwargs)


# ═════════════════════════════════════════════════════════════════════════════
# TABLE MODELS - For displaying tabular data in Django Admin
# ═════════════════════════════════════════════════════════════════════════════


class QuotationSkillRate(models.Model):
    """
    SKILL SETS AND LEVELS / DAILY RATE TABLE
    """
    quotation = models.ForeignKey(
        Quotation,
        on_delete=models.CASCADE,
        related_name='skill_rates'
    )
    skill_set = models.CharField(
        "Skill Set (list)",
        max_length=255,
        help_text="e.g., Program & Product Management Services & Support"
    )
    skill_level = models.CharField(
        "Skill Level",
        max_length=100,
        help_text="e.g., Level 2 - Practitioner"
    )
    short_term_rate = models.DecimalField(
        "Short Term Daily Rate ($)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="For tasks less than 183 days"
    )
    long_term_rate = models.DecimalField(
        "Long Term Daily Rate ($)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="For tasks of duration greater than 183 days"
    )

    class Meta:
        verbose_name = "Skill Set and Rate"
        verbose_name_plural = "Skill Sets and Rates"

    def __str__(self):
        return f"{self.skill_set} - Level {self.skill_level}"


class QuotationSpecifiedPersonnel(models.Model):
    """
    SPECIFIED PERSONNEL TABLE
    Names of Specified Personnel proposed to provide Services and the roles that each will undertake
    """
    quotation = models.ForeignKey(
        Quotation,
        on_delete=models.CASCADE,
        related_name='specified_personnel'
    )
    name = models.CharField(
        "Name",
        max_length=200,
        help_text="Name of specified personnel"
    )
    role = models.CharField(
        "Role",
        max_length=200,
        help_text="Role that this person will undertake"
    )

    class Meta:
        verbose_name = "Specified Personnel"
        verbose_name_plural = "Specified Personnel"

    def __str__(self):
        return f"{self.name} - {self.role}"


class QuotationSubcontractor(models.Model):
    """
    SUBCONTRACTORS TO BE USED IN PROVIDING THE SERVICES TABLE
    """
    quotation = models.ForeignKey(
        Quotation,
        on_delete=models.CASCADE,
        related_name='subcontractors'
    )
    company_name = models.CharField(
        "Subcontractor Company Name",
        max_length=255
    )
    abn = models.CharField(
        "Subcontractor ABN",
        max_length=50,
        blank=True
    )
    specified_personnel_names = models.TextField(
        "Subcontractor Specified Personnel Name(s)",
        help_text="Names of personnel from this subcontractor"
    )

    class Meta:
        verbose_name = "Subcontractor"
        verbose_name_plural = "Subcontractors"

    def __str__(self):
        return self.company_name


class QuotationTimeMaterialsItem(models.Model):
    """
    TIME AND MATERIALS PAYMENT SCHEDULE TABLE
    Note: Use this table to provide a quotation for tasks based on a level of effort or other time and materials basis.
    For tasks of duration greater than 183 days Long Term rates must be used.
    For tasks less than 183 days short term rates apply.
    The duration of task is as per the RFQTS "Duration of Contract" field.
    """
    quotation = models.ForeignKey(
        Quotation,
        on_delete=models.CASCADE,
        related_name='time_materials_items'
    )
    skill_set = models.CharField(
        "Skill Set (as defined in the DSS Deed)",
        max_length=255,
        help_text="e.g., Program & Project Management Services & Support"
    )
    skill_level = models.CharField(
        "Skill Level",
        max_length=100,
        help_text="Skill level number"
    )
    days = models.PositiveIntegerField(
        "Days (8 hours)",
        help_text="Number of 8-hour days"
    )
    daily_rate_short_term = models.DecimalField(
        "Daily Rate $ (GST Inc.) - Short Term",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="For tasks less than 183 days"
    )
    daily_rate_long_term = models.DecimalField(
        "Daily Rate $ (GST Inc.) - Long Term",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="For tasks greater than 183 days"
    )
    total_price = models.DecimalField(
        "Total Price $ GST Inc.",
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Calculated: Days × Daily Rate"
    )

    class Meta:
        verbose_name = "Time and Materials Item"
        verbose_name_plural = "Time and Materials Items"

    def __str__(self):
        return f"{self.skill_set} - {self.days} days"

    def save(self, *args, **kwargs):
        # Auto-calculate total price
        rate = self.daily_rate_long_term if self.daily_rate_long_term else self.daily_rate_short_term
        if rate and self.days:
            self.total_price = rate * self.days
        super().save(*args, **kwargs)


class QuotationFixedPriceDeliverable(models.Model):
    """
    FIXED PRICE DELIVERABLES AND PAYMENT SCHEDULE TABLE
    Note: Use this table for fixed price task.
    """
    quotation = models.ForeignKey(
        Quotation,
        on_delete=models.CASCADE,
        related_name='fixed_price_deliverables'
    )
    deliverable = models.TextField(
        "Deliverables",
        help_text="Description of deliverable"
    )
    delivery_date = models.DateField(
        "Delivery Date",
        help_text="Date when deliverable will be completed"
    )
    payment = models.DecimalField(
        "Payment $ (GST Inc.)",
        max_digits=12,
        decimal_places=2,
        help_text="Payment amount for this deliverable"
    )

    class Meta:
        verbose_name = "Fixed Price Deliverable"
        verbose_name_plural = "Fixed Price Deliverables"
        ordering = ['delivery_date']

    def __str__(self):
        return f"{self.deliverable[:50]}..." if len(self.deliverable) > 50 else self.deliverable


# ─────────────────────────────────────────────────────────────────────────────
# Signals
# ─────────────────────────────────────────────────────────────────────────────
@receiver(post_save, sender=JobApplication)
def create_quotation_for_application(sender, instance, created, **kwargs):
    """Create a blank Quotation automatically whenever a new job application is created"""
    if created:
        job = instance.job
        rfqts = job.rfqts if job.rfqts else None
        
        # Pre-populate basic information from the application and job
        quotation_data = {
            'application': instance,
            'rfqts_no': rfqts.rfqts_no if rfqts else '',
            'task_title': job.title,
            'service_provider_name': instance.user.get_full_name() or instance.full_name,
            'service_provider_abn': instance.abn or '',
            'location': job.location,
        }
        
        # Create the blank quotation
        Quotation.objects.create(**quotation_data)


