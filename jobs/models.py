import uuid
import re
import json
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from users.models import CustomUser

from django.db.models.signals import post_save
from django.dispatch import receiver

# PDF processing imports
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


class RFQTSFieldMapping(models.Model):
    """
    Configurable field mappings for PDF extraction per RFQTS
    """
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "RFQTS Field Mapping Template"
        verbose_name_plural = "RFQTS Field Mapping Templates"
    
    def __str__(self):
        return self.name


class RFQTSField(models.Model):
    """
    Individual field configuration for PDF extraction
    """
    FIELD_TYPES = [
        ('text', 'Text'),
        ('date', 'Date'),
        ('decimal', 'Decimal'),
        ('multiline', 'Multi-line Text'),
        ('table', 'Table'),
    ]
    
    mapping_template = models.ForeignKey(RFQTSFieldMapping, related_name='fields', on_delete=models.CASCADE)
    field_name = models.CharField(max_length=100, help_text="Model field name (e.g., 'rfqts_no')")
    display_name = models.CharField(max_length=200, help_text="Display name for admin")
    pdf_label = models.CharField(max_length=200, help_text="Label to search for in PDF (e.g., 'RFQTS Number:')")
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES, default='text')
    extract_until = models.CharField(max_length=200, blank=True, help_text="Stop extraction at this label/pattern")
    extraction_pattern = models.TextField(blank=True, help_text="Custom regex pattern for extraction")
    is_required = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'field_name']
        unique_together = ['mapping_template', 'field_name']
    
    def __str__(self):
        return f"{self.display_name} ({self.field_name})"


class RFQTS(models.Model):
    """
    Request for Quotation and Tasking Statement
    """
    # Basic fields
    rfqts_no = models.CharField(max_length=200, default='RFQ-0000')  
    department = models.CharField(max_length=200, default='General')  
    group = models.CharField(max_length=200, default='Default Group')  
    directorate = models.CharField(max_length=200, default='Default Directorate')  
    project_section = models.CharField(max_length=200, default='Default Project Section') 
    task_title = models.CharField(max_length=500, default='Default Task Title') 
    
    # Date fields
    commencement_date_for_task = models.DateField(null=True, blank=True)  
    completion_date_for_task = models.DateField(null=True, blank=True)  
    closing_date_for_quotation = models.DateField(null=True, blank=True)
    date_rfqts_received = models.DateField(null=True, blank=True)
    
    # Type and category
    rfqts_type = models.CharField(max_length=200, default='General')  
    service_category = models.CharField(max_length=200, default='Default Service Category')  
    quote_form_type = models.CharField(max_length=200, default='Standard')
    
    # Skills and rates
    skills_sets = models.TextField(default='Default Skills Set')  
    skills_levels = models.CharField(max_length=200, default='Entry Level')  
    max_rate_per_day = models.CharField(max_length=100, blank=True)
    max_cvs = models.CharField(max_length=50, blank=True)
    
    # Location and scope
    location = models.CharField(max_length=255, default='ACT')  
    scope_of_task = models.TextField(default='Default Scope') 
    statement_of_duties = models.TextField(blank=True)
    
    # Deliverables and requirements
    deliverables = models.TextField(default='Default Deliverables')
    specified_personnel = models.TextField(default='Not Specified')
    evaluation_criteria = models.TextField(default="evaluate")  
    
    # Standards and conditions
    applicable_standards_or_references = models.TextField(default='None') 
    allowances_or_disbursements = models.TextField(default='None') 
    other_relevant_information_or_special_requirements = models.TextField(default='None')  
    special_conditions = models.TextField(default='None')  
    extension_options = models.TextField(default='None')  
    
    # Security
    security_clearances_required_for_personnel = models.TextField(default='None')  
    security_guidance = models.TextField(blank=True)
    
    # Key Result Areas
    key_result_areas = models.TextField(blank=True)
    
    # Files and metadata
    rfq_file = models.FileField(upload_to='rfq_files/', blank=True, null=True)
    field_mapping = models.ForeignKey(RFQTSFieldMapping, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Request for Quotation and Tasking Statement"
        verbose_name_plural = "Request for Quotation and Tasking Statements"   

    def __str__(self):
        return self.rfqts_no

    def extract_pdf_data(self):
        """
        Extract data from uploaded PDF and populate relevant fields
        """
        if not self.rfq_file or not PDF_AVAILABLE:
            return False
        
        try:
            # Read entire PDF content as one continuous text
            pdf_text = self._read_pdf_content()
            if not pdf_text:
                return False
            
            # Extract data using improved parsing
            extracted_data = self._parse_pdf_content(pdf_text)
            
            if not extracted_data:
                return False
            
            # Update fields with extracted data
            updated_fields = []
            for field_name, value in extracted_data.items():
                if hasattr(self, field_name) and value:
                    current_value = getattr(self, field_name)
                    if self._should_update_field(field_name, current_value):
                        setattr(self, field_name, value)
                        updated_fields.append(field_name)
            
            return len(updated_fields) > 0
            
        except Exception as e:
            print(f"PDF extraction error: {str(e)}")
            return False

    def _read_pdf_content(self):
        """
        Read entire PDF as continuous text, preserving structure
        """
        try:
            self.rfq_file.seek(0)
            pdf_reader = PyPDF2.PdfReader(self.rfq_file)
            
            # Combine all pages into one continuous text
            full_text = ""
            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                # Add page break marker for reference but process as continuous text
                full_text += f"\n[PAGE_{page_num + 1}]\n" + page_text
            
            return full_text
            
        except Exception as e:
            print(f"Error reading PDF: {str(e)}")
            return ""

    def _parse_pdf_content(self, text):
        """
        Parse PDF content with improved extraction logic
        """
        extracted_data = {}
        
        # Clean the text first
        text = self._clean_pdf_text(text)
        
        # Extract RFQTS Number - improved pattern
        rfqts_patterns = [
            r'RFQTS\s+Number:?\s*([A-Z0-9\-]+)',
            r'RFQTS\s+No\.?\s*:?\s*([A-Z0-9\-]+)',
            r'(?:Task\s+Title:\s*)?([A-Z]{3,4}-\d{2}-\d{4}[A-Z]?)',
        ]
        for pattern in rfqts_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                extracted_data['rfqts_no'] = match.group(1).strip()
                break
        
        # Extract basic organizational fields with precise patterns
        org_fields = {
            'department': [
                r'Department:\s*([A-Za-z\s]+?)(?:\s+Group:|$|\n)',
                r'Department\s*:\s*([A-Za-z]+)(?:\s+Group|\s*$|\s*\n)',
            ],
            'group': [
                r'Group:\s*([A-Za-z\s]+?)(?:\s+Directorate:|$|\n)',
                r'Group\s*:\s*([A-Za-z\s]+?)(?:\s+Directorate|\s*$|\s*\n)',
            ],
            'directorate': [
                r'Directorate:\s*([A-Za-z\s]+?)(?:\s+Project/Section:|$|\n)',
                r'Directorate\s*:\s*([A-Za-z\s]+?)(?:\s+Project|\s*$|\s*\n)',
            ],
            'project_section': [
                r'Project/Section:\s*([A-Za-z\s]+?)(?:\s+Task\s+Title:|$|\n)',
                r'Project/Section\s*:\s*([A-Za-z\s]+?)(?:\s+Task|\s*$|\s*\n)',
            ],
        }
        
        for field_name, patterns in org_fields.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    # Clean the extracted value
                    value = re.sub(r'\s+', ' ', value)  # Normalize whitespace
                    value = re.sub(r'^[:\-\s]+|[:\-\s]+$', '', value)  # Remove leading/trailing punctuation
                    if value and len(value) > 1:  # Avoid single letters/numbers
                        extracted_data[field_name] = value
                        break
        
        # Additional extraction logic for other fields...
        # (Include the rest of the PDF extraction methods from the original code)
        
        return extracted_data

    def _clean_pdf_text(self, text):
        """Clean PDF text while preserving structure"""
        # Remove page markers but keep the content continuous
        text = re.sub(r'\[PAGE_\d+\]', '\n', text)
        
        # Remove OFFICIAL headers/footers
        text = re.sub(r'\n\s*\d+\s+OFFICIAL\s*\n', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'\n\s*OFFICIAL\s*\n', '\n', text, flags=re.IGNORECASE)
        
        # Remove standalone page numbers at line start/end
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
        
        # Normalize whitespace but preserve single line breaks
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'\r\n', '\n', text)
        text = re.sub(r'\r', '\n', text)
        
        return text

    def _should_update_field(self, field_name, current_value):
        """
        Determine if a field should be updated based on its current value
        """
        default_values = {
            'rfqts_no': 'RFQ-0000',
            'department': 'General',
            'group': 'Default Group',
            'directorate': 'Default Directorate',
            'project_section': 'Default Project Section',
            'task_title': 'Default Task Title',
            'rfqts_type': 'General',
            'skills_sets': 'Default Skills Set',
            'skills_levels': 'Entry Level',
            'service_category': 'Default Service Category',
            'scope_of_task': 'Default Scope',
            'location': 'ACT',
            'deliverables': 'Default Deliverables',
            'specified_personnel': 'Not Specified',
            'evaluation_criteria': 'evaluate',
            'applicable_standards_or_references': 'None',
            'allowances_or_disbursements': 'None',
            'other_relevant_information_or_special_requirements': 'None',
            'special_conditions': 'None',
            'extension_options': 'None',
            'security_clearances_required_for_personnel': 'None',
            'quote_form_type': 'Standard'
        }
        
        # Always update if current value is a default value or empty
        is_default = current_value == default_values.get(field_name, '')
        is_empty = not current_value or str(current_value).strip() == ''
        
        return is_default or is_empty


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
        ('Tasmania', 'Tasmania'),
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
# NEW C4 COSTING MODELS - BASED ON SPREADSHEET STRUCTURE
# ═════════════════════════════════════════════════════════════════════════════

class ServiceProvider(models.Model):
    """
    Service providers like SME Gateway, ServeGate, etc. with configurable fees
    """
    name = models.CharField(
        "Provider Name", 
        max_length=100, 
        unique=True,
        help_text="e.g., SME Gateway, ServeGate, Jigsaw"
    )
    
    fee_percentage = models.DecimalField(
        "Fee Percentage (%)",
        max_digits=5,
        decimal_places=2,
        default=Decimal('8.00'),
        help_text="Management fee percentage"
    )
    
    fee_fixed_amount = models.DecimalField(
        "Fixed Fee Amount ($)",
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Fixed fee amount (if applicable)"
    )
    
    is_active = models.BooleanField("Active", default=True)
    is_default = models.BooleanField("Default Provider", default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Service Provider"
        verbose_name_plural = "Service Providers"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.fee_percentage}%)"

    def save(self, *args, **kwargs):
        # Ensure only one default provider
        if self.is_default:
            ServiceProvider.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)


class PayrollTaxRate(models.Model):
    """
    State-based payroll tax rates
    """
    STATE_CHOICES = [
        ('NSW', 'New South Wales'),
        ('VIC', 'Victoria'),
        ('QLD', 'Queensland'),
        ('WA', 'Western Australia'),
        ('SA', 'South Australia'),
        ('Tasmania', 'Tasmania'),
        ('ACT', 'Australian Capital Territory'),
        ('NT', 'Northern Territory'),
    ]
    
    state = models.CharField(
        "State/Territory",
        max_length=20,
        choices=STATE_CHOICES,
        unique=True
    )
    
    rate_percentage = models.DecimalField(
        "Payroll Tax Rate (%)",
        max_digits=5,
        decimal_places=2,
        help_text="Payroll tax rate for this state/territory"
    )
    
    effective_from = models.DateField(
        "Effective From",
        default=timezone.now
    )
    
    is_active = models.BooleanField("Active", default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Payroll Tax Rate"
        verbose_name_plural = "Payroll Tax Rates"
        ordering = ['state']

    def __str__(self):
        return f"{self.get_state_display()}: {self.rate_percentage}%"


class AssessmentQuestionTemplate(models.Model):
    """
    Configurable template for custom assessment questions
    """
    name = models.CharField(
        "Template Name",
        max_length=200,
        unique=True
    )
    
    description = models.TextField(
        "Description",
        blank=True
    )
    
    questions = models.JSONField(
        "Questions Configuration",
        default=list,
        help_text="List of custom questions for risk assessment"
    )
    
    is_active = models.BooleanField(
        "Active",
        default=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Assessment Question Template"
        verbose_name_plural = "Assessment Question Templates"

    def __str__(self):
        return self.name


class C4CostingSheet(models.Model):
    """
    C4 Costing calculations based on the provided spreadsheet structure
    """
    application = models.OneToOneField(
        JobApplication,
        on_delete=models.CASCADE,
        related_name="c4_costing",
        primary_key=True,
    )

    # ═════════════════════════════════════════════════════════════════════════
    # KEY VARIABLES (Management Editable)
    # ═════════════════════════════════════════════════════════════════════════
    use_gateway_servegate = models.BooleanField(
        "Use SME Gateway/ServeGate?",
        default=True,
        help_text="Whether to use gateway service provider"
    )
    
    payroll_tax_applicable = models.BooleanField(
        "Payroll Tax Applicable?",
        default=True,
        help_text="Whether payroll tax applies"
    )
    
    management_fee_percentage = models.DecimalField(
        "Management Fee (%)",
        max_digits=5,
        decimal_places=2,
        default=Decimal('8.00'),
        help_text="Management fee percentage (editable by C4)"
    )
    
    payroll_tax_percentage = models.DecimalField(
        "Payroll Tax (%)",
        max_digits=5,
        decimal_places=2,
        default=Decimal('4.85'),
        help_text="Payroll tax percentage (editable by C4)"
    )
    
    # ═════════════════════════════════════════════════════════════════════════
    # SERVICE PROVIDER SELECTION
    # ═════════════════════════════════════════════════════════════════════════
    service_provider = models.ForeignKey(
        ServiceProvider,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Selected service provider (SME Gateway, ServeGate, etc.)"
    )

    # ═════════════════════════════════════════════════════════════════════════
    # CUSTOMER CEILING RATE
    # ═════════════════════════════════════════════════════════════════════════
    customer_ceiling_rate_gst_inc = models.DecimalField(
        "Customer Ceiling Rate (GST Inclusive)",
        max_digits=10,
        decimal_places=2,
        default=Decimal('150.00'),
        help_text="Maximum rate chargeable to customer including GST"
    )
    
    # Auto-calculated fields for ceiling rate
    customer_ceiling_rate_gst_ex = models.DecimalField(
        "Customer Ceiling Rate (GST Exclusive)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    ceiling_rate_saving_percentage = models.DecimalField(
        "Ceiling Rate Saving (%)",
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    # ═════════════════════════════════════════════════════════════════════════
    # CANDIDATE NEEDS
    # ═════════════════════════════════════════════════════════════════════════
    equipment_cost_gst_inc = models.DecimalField(
        "Equipment Cost (GST Inclusive)",
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Equipment costs for candidate"
    )
    
    training_memberships_cost_gst_inc = models.DecimalField(
        "Training/Memberships Cost (GST Inclusive)",
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Training and membership costs"
    )

    # ═════════════════════════════════════════════════════════════════════════
    # CALCULATOR SECTION (Core calculations)
    # ═════════════════════════════════════════════════════════════════════════
    charge_to_c4_client_gst_inc = models.DecimalField(
        "Charge to C4 Client (GST Inc)",
        max_digits=10,
        decimal_places=2,
        default=Decimal('100.00'),
        help_text="Daily rate charged to C4 client including GST"
    )
    
    # Auto-calculated fields
    charge_to_c4_client_gst_ex = models.DecimalField(
        "Charge to C4 Client (GST Ex)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    charge_to_c4_client_gst = models.DecimalField(
        "GST Amount",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    gateway_fee_gst_inc = models.DecimalField(
        "Gateway/ServeGate Fee (GST Inc)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    gateway_fee_gst_ex = models.DecimalField(
        "Gateway/ServeGate Fee (GST Ex)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    gateway_fee_gst = models.DecimalField(
        "Gateway Fee GST",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    payroll_tax_amount = models.DecimalField(
        "Payroll Tax Amount",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    gst_difference_to_ato = models.DecimalField(
        "Difference in GST to ATO",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    subtotal_payment_to_c4_gst_inc = models.DecimalField(
        "Subtotal Payment to C4 (GST Inc)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    subtotal_payment_to_c4_gst_ex = models.DecimalField(
        "Subtotal Payment to C4 (GST Ex)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    subtotal_payment_to_c4_gst = models.DecimalField(
        "Subtotal Payment to C4 GST",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    payment_to_service_provider = models.DecimalField(
        "Payment to Service Provider",
        max_digits=10,
        decimal_places=2,
        default=Decimal('50.00'),
        help_text="Payment to service provider (e.g., Jigsaw)"
    )
    
    net_payment_to_c4_gst_inc = models.DecimalField(
        "Net Payment to C4 (GST Inc)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    net_payment_to_c4_gst_ex = models.DecimalField(
        "Net Payment to C4 (GST Ex)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    # ═════════════════════════════════════════════════════════════════════════
    # CANDIDATE COST CALCULATION
    # ═════════════════════════════════════════════════════════════════════════
    candidate_cost_to_c4_gst_inc = models.DecimalField(
        "Candidate Cost to C4 (GST Inc)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Includes superannuation"
    )
    
    candidate_cost_to_c4_gst_ex = models.DecimalField(
        "Candidate Cost to C4 (GST Ex)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    hourly_rate_gst_inc = models.DecimalField(
        "Hourly Rate (GST Inc)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    hourly_rate_gst_ex = models.DecimalField(
        "Hourly Rate (GST Ex)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    # ═════════════════════════════════════════════════════════════════════════
    # MARGIN CALCULATION
    # ═════════════════════════════════════════════════════════════════════════
    margin_amount = models.DecimalField(
        "Margin ($)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    margin_percentage = models.DecimalField(
        "Margin (%)",
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )

    # ═════════════════════════════════════════════════════════════════════════
    # PROJECT TOTALS
    # ═════════════════════════════════════════════════════════════════════════
    project_days = models.PositiveIntegerField(
        "Project Days",
        default=230,
        help_text="Total number of working days for the project"
    )
    
    project_total_cost = models.DecimalField(
        "Project Total Cost",
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    travel_costs = models.DecimalField(
        "Travel Costs",
        max_digits=12,
        decimal_places=2,
        default=Decimal('16500.00'),
        help_text="Total travel costs for the project"
    )
    
    project_grand_total = models.DecimalField(
        "Project Grand Total",
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )

    # ═════════════════════════════════════════════════════════════════════════
    # ANNUAL PACKAGE CALCULATIONS
    # ═════════════════════════════════════════════════════════════════════════
    equivalent_annual_package = models.DecimalField(
        "Equivalent Annual Package",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    standard_annual_salary = models.DecimalField(
        "Standard Annual Salary",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    superannuation_percentage = models.DecimalField(
        "Superannuation (%)",
        max_digits=5,
        decimal_places=2,
        default=Decimal('12.50'),
        help_text="Superannuation percentage"
    )

    # ═════════════════════════════════════════════════════════════════════════
    # WORKING DAYS CALCULATION
    # ═════════════════════════════════════════════════════════════════════════
    days_per_week = models.PositiveIntegerField(
        "Days per Week",
        default=5
    )
    
    weekdays_in_year = models.PositiveIntegerField(
        "Weekdays in Year",
        default=260
    )
    
    public_holidays = models.PositiveIntegerField(
        "Public Holidays",
        default=10
    )
    
    annual_leave_days = models.PositiveIntegerField(
        "Annual Leave Days",
        default=20
    )
    
    sick_leave_days = models.PositiveIntegerField(
        "Sick Leave Days",
        default=5
    )
    
    net_days_worked = models.PositiveIntegerField(
        "Net Days Worked",
        null=True,
        blank=True
    )

    # ═════════════════════════════════════════════════════════════════════════
    # METADATA AND CONTROLS
    # ═════════════════════════════════════════════════════════════════════════
    manual_override = models.BooleanField(
        "Manual Override",
        default=False,
        help_text="Check to prevent auto-calculation"
    )
    
    calculation_year = models.PositiveIntegerField(
        "Calculation Year",
        default=2024,
        help_text="Year for calculations"
    )
    
    notes = models.TextField(
        "Costing Notes",
        blank=True,
        help_text="Notes about costing decisions"
    )
    
    last_calculated = models.DateTimeField(auto_now=True)
    calculated_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Last user to update calculations"
    )

    class Meta:
        verbose_name = "C4 Costing Sheet"
        verbose_name_plural = "C4 Costing Sheets"

    def __str__(self):
        return f"C4 Costing for {self.application.full_name}"

    def calculate_all(self, save=True):
        """
        Calculate all cost components based on the spreadsheet structure
        """
        if self.manual_override:
            return
        
        # Step 1: Calculate Customer Ceiling Rate (GST Ex)
        self.customer_ceiling_rate_gst_ex = self.customer_ceiling_rate_gst_inc / Decimal('1.10')
        
        # Step 2: Calculate Core Client Charge rates
        self.charge_to_c4_client_gst_ex = self.charge_to_c4_client_gst_inc / Decimal('1.10')
        self.charge_to_c4_client_gst = self.charge_to_c4_client_gst_inc - self.charge_to_c4_client_gst_ex
        
        # Step 3: Calculate Gateway/ServeGate Fees
        if self.use_gateway_servegate and self.service_provider:
            gateway_fee_ex_gst = self.charge_to_c4_client_gst_ex * (self.service_provider.fee_percentage / 100)
            self.gateway_fee_gst_ex = gateway_fee_ex_gst
            self.gateway_fee_gst = gateway_fee_ex_gst * Decimal('0.10')
            self.gateway_fee_gst_inc = gateway_fee_ex_gst * Decimal('1.10')
        else:
            self.gateway_fee_gst_ex = Decimal('0.00')
            self.gateway_fee_gst = Decimal('0.00')
            self.gateway_fee_gst_inc = Decimal('0.00')
        
        # Step 4: Calculate Payroll Tax
        if self.payroll_tax_applicable:
            # Payroll tax is calculated on GST exclusive amount
            self.payroll_tax_amount = self.charge_to_c4_client_gst_ex * (self.payroll_tax_percentage / 100)
        else:
            self.payroll_tax_amount = Decimal('0.00')
        
        # Step 5: Calculate GST difference to ATO
        # This is the difference between GST collected and GST paid on gateway fees
        self.gst_difference_to_ato = self.charge_to_c4_client_gst - self.gateway_fee_gst
        
        # Step 6: Calculate Subtotal Payment to C4
        self.subtotal_payment_to_c4_gst_ex = (
            self.charge_to_c4_client_gst_ex - 
            self.gateway_fee_gst_ex - 
            self.payroll_tax_amount
        )
        self.subtotal_payment_to_c4_gst = self.subtotal_payment_to_c4_gst_ex * Decimal('0.10')
        self.subtotal_payment_to_c4_gst_inc = self.subtotal_payment_to_c4_gst_ex * Decimal('1.10')
        
        # Step 7: Calculate Net Payment to C4 (after service provider payment)
        self.net_payment_to_c4_gst_inc = self.subtotal_payment_to_c4_gst_inc - self.payment_to_service_provider
        self.net_payment_to_c4_gst_ex = self.net_payment_to_c4_gst_inc / Decimal('1.10')
        
        # Step 8: Calculate Candidate Cost (includes superannuation)
        # This is the net amount available for candidate payment
        candidate_cost_base = self.net_payment_to_c4_gst_ex
        self.candidate_cost_to_c4_gst_ex = candidate_cost_base / (1 + (self.superannuation_percentage / 100))
        self.candidate_cost_to_c4_gst_inc = self.candidate_cost_to_c4_gst_ex * Decimal('1.10')
        
        # Step 9: Calculate Hourly Rates (assuming 8-hour days)
        self.hourly_rate_gst_ex = self.candidate_cost_to_c4_gst_ex / 8
        self.hourly_rate_gst_inc = self.candidate_cost_to_c4_gst_inc / 8
        
        # Step 10: Calculate Margin
        self.margin_amount = self.net_payment_to_c4_gst_ex - self.candidate_cost_to_c4_gst_ex
        if self.candidate_cost_to_c4_gst_ex > 0:
            self.margin_percentage = (self.margin_amount / self.candidate_cost_to_c4_gst_ex) * 100
        else:
            self.margin_percentage = Decimal('0.00')
        
        # Step 11: Calculate Project Totals
        self.project_total_cost = self.charge_to_c4_client_gst_inc * self.project_days
        self.project_grand_total = self.project_total_cost + self.travel_costs
        
        # Step 12: Calculate Annual Package Equivalents
        self.net_days_worked = (
            self.weekdays_in_year - 
            self.public_holidays - 
            self.annual_leave_days - 
            self.sick_leave_days
        )
        
        if self.net_days_worked > 0:
            self.equivalent_annual_package = self.candidate_cost_to_c4_gst_inc * self.net_days_worked
            self.standard_annual_salary = self.equivalent_annual_package / (1 + (self.superannuation_percentage / 100))
        
        # Step 13: Calculate Ceiling Rate Saving
        if self.customer_ceiling_rate_gst_inc > 0:
            saving_amount = self.customer_ceiling_rate_gst_inc - self.charge_to_c4_client_gst_inc
            self.ceiling_rate_saving_percentage = (saving_amount / self.customer_ceiling_rate_gst_inc) * 100
        
        # Round all calculations to 2 decimal places
        self._round_all_decimals()
        
        if save:
            self.save()
        
        return True

    def _round_all_decimals(self):
        """Round all decimal fields to 2 decimal places"""
        decimal_fields = [
            'customer_ceiling_rate_gst_ex', 'ceiling_rate_saving_percentage',
            'charge_to_c4_client_gst_ex', 'charge_to_c4_client_gst',
            'gateway_fee_gst_inc', 'gateway_fee_gst_ex', 'gateway_fee_gst',
            'payroll_tax_amount', 'gst_difference_to_ato',
            'subtotal_payment_to_c4_gst_inc', 'subtotal_payment_to_c4_gst_ex', 'subtotal_payment_to_c4_gst',
            'net_payment_to_c4_gst_inc', 'net_payment_to_c4_gst_ex',
            'candidate_cost_to_c4_gst_inc', 'candidate_cost_to_c4_gst_ex',
            'hourly_rate_gst_inc', 'hourly_rate_gst_ex',
            'margin_amount', 'margin_percentage',
            'project_total_cost', 'project_grand_total',
            'equivalent_annual_package', 'standard_annual_salary'
        ]
        
        for field_name in decimal_fields:
            value = getattr(self, field_name)
            if value is not None:
                setattr(self, field_name, value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

    def save(self, *args, **kwargs):
        if not self.manual_override:
            self.calculate_all(save=False)
        super().save(*args, **kwargs)


class PreSubmissionAssessment(models.Model):
    """
    Risk assessment checklist before submitting applications
    """
    application = models.OneToOneField(
        JobApplication,
        on_delete=models.CASCADE,
        related_name="risk_assessment",
        primary_key=True,
    )
    
    # Assessment Template Selection
    assessment_template = models.ForeignKey(
        AssessmentQuestionTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Assessment Template",
        help_text="Select a template for custom assessment questions"
    )
    
    # Standard Risk Assessment Questions
    all_responses_checked = models.BooleanField(
        "All candidate responses have been checked and verified",
        default=False
    )
    
    clearance_verified = models.BooleanField(
        "Security clearance requirements verified",
        default=False
    )
    
    cv_reviewed = models.BooleanField(
        "CV reviewed for gaps and accuracy",
        default=False
    )
    
    references_contacted = models.BooleanField(
        "References have been contacted (if required)",
        default=False
    )
    
    costing_approved = models.BooleanField(
        "Costing has been reviewed and approved",
        default=False
    )
    
    conflict_assessed = models.BooleanField(
        "Conflict of interest assessment completed",
        default=False
    )
    
    waiver_processed = models.BooleanField(
        "APS/SERCAT waiver processed (if applicable)",
        default=False
    )
    
    client_requirements_met = models.BooleanField(
        "All client requirements have been confirmed as met",
        default=False
    )
    
    # Custom Assessment Fields (configurable)
    custom_assessment_data = models.JSONField(
        "Custom Assessment Responses",
        default=dict,
        blank=True,
        help_text="Responses to custom assessment questions from selected template"
    )
    
    # Assessment Results
    overall_risk_level = models.CharField(
        "Overall Risk Level",
        max_length=20,
        choices=[
            ('Low', 'Low Risk'),
            ('Medium', 'Medium Risk'),
            ('High', 'High Risk'),
        ],
        default='Medium'
    )
    
    ready_for_submission = models.BooleanField(
        "Ready for Submission",
        default=False,
        help_text="Check when application is ready to submit to client"
    )
    
    # Assessment Details
    risk_notes = models.TextField(
        "Risk Assessment Notes",
        blank=True,
        help_text="Additional notes about risks and mitigation strategies"
    )
    
    assessed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conducted_assessments"
    )
    
    assessed_at = models.DateTimeField(auto_now=True)
    
    # Submission tracking
    submitted_to_client = models.BooleanField(
        "Submitted to Client",
        default=False
    )
    
    submission_date = models.DateTimeField(
        "Submission Date",
        null=True,
        blank=True
    )
    
    submitted_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_applications"
    )

    class Meta:
        verbose_name = "Pre-Submission Risk Assessment"
        verbose_name_plural = "Pre-Submission Risk Assessments"

    def __str__(self):
        return f"Risk Assessment for {self.application.full_name}"

    def load_template_questions(self):
        """
        Load questions from the selected assessment template
        """
        if self.assessment_template and self.assessment_template.questions:
            # Initialize custom_assessment_data with template questions if empty
            if not self.custom_assessment_data:
                self.custom_assessment_data = {}
            
            # Add any new questions from template that aren't already in responses
            for question_data in self.assessment_template.questions:
                question_id = f"q_{abs(hash(question_data.get('question', '')))}"
                if question_id not in self.custom_assessment_data:
                    self.custom_assessment_data[question_id] = {
                        'question': question_data.get('question', ''),
                        'type': question_data.get('type', 'text'),
                        'required': question_data.get('required', False),
                        'answer': ''
                    }
            self.save()

    def get_template_questions(self):
        """
        Get formatted questions for display in admin
        """
        if not self.assessment_template or not self.assessment_template.questions:
            return []
        
        questions = []
        for question_data in self.assessment_template.questions:
            question_id = f"q_{abs(hash(question_data.get('question', '')))}"
            answer = ''
            if self.custom_assessment_data and question_id in self.custom_assessment_data:
                answer = self.custom_assessment_data[question_id].get('answer', '')
            
            questions.append({
                'id': question_id,
                'question': question_data.get('question', ''),
                'type': question_data.get('type', 'text'),
                'required': question_data.get('required', False),
                'answer': answer
            })
        return questions

    @property
    def completion_percentage(self):
        """Calculate assessment completion percentage including custom questions"""
        # Standard checks (8 total)
        standard_checks = 8
        completed_standard = sum([
            self.all_responses_checked,
            self.clearance_verified,
            self.cv_reviewed,
            self.references_contacted,
            self.costing_approved,
            self.conflict_assessed,
            self.waiver_processed,
            self.client_requirements_met,
        ])
        
        # Custom questions completion
        custom_questions = self.get_template_questions()
        custom_checks = len([q for q in custom_questions if q['required']])
        completed_custom = 0
        
        for q in custom_questions:
            if q['required'] and q['answer']:
                completed_custom += 1
        
        total_checks = standard_checks + custom_checks
        completed_total = completed_standard + completed_custom
        
        if total_checks == 0:
            return 100.0
        
        return (completed_total / total_checks) * 100

    @property
    def is_complete(self):
        """Check if assessment is complete"""
        return self.completion_percentage == 100

    def save(self, *args, **kwargs):
        # Auto-load template questions when template is selected
        if self.assessment_template and self.assessment_template.questions:
            self.load_template_questions()
        super().save(*args, **kwargs)


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


# ═════════════════════════════════════════════════════════════════════════════
# SIGNALS - Auto-create related models and data population
# ═════════════════════════════════════════════════════════════════════════════

@receiver(post_save, sender=JobApplication)
def create_c4_costing_and_assessment(sender, instance, created, **kwargs):
    """
    Auto-create C4CostingSheet and PreSubmissionAssessment for new applications
    """
    if created:
        # Parse proposed rate from application
        charge_rate = Decimal('100.00')  # Default
        if instance.proposed_contract_rate:
            # Try to extract numeric value from proposed rate
            import re
            rate_match = re.search(r'[\d,]+\.?\d*', instance.proposed_contract_rate.replace(',', ''))
            if rate_match:
                try:
                    charge_rate = Decimal(rate_match.group())
                except:
                    pass
        
        # Get default service provider
        default_provider = ServiceProvider.objects.filter(is_default=True).first()
        
        # Calculate estimated days from job dates
        estimated_days = 230  # Default
        if (instance.job.rfqts and 
            instance.job.rfqts.completion_date_for_task and 
            instance.job.rfqts.commencement_date_for_task):
            delta = instance.job.rfqts.completion_date_for_task - instance.job.rfqts.commencement_date_for_task
            estimated_days = max(1, delta.days)
        
        # Get payroll tax rate based on job location
        payroll_tax_rate = Decimal('4.85')  # Default
        if instance.job.location:
            tax_rate_obj = PayrollTaxRate.objects.filter(
                state=instance.job.location, 
                is_active=True
            ).first()
            if tax_rate_obj:
                payroll_tax_rate = tax_rate_obj.rate_percentage
        
        # Create C4 costing sheet with populated values
        costing_sheet = C4CostingSheet.objects.create(
            application=instance,
            charge_to_c4_client_gst_inc=charge_rate,
            project_days=estimated_days,
            service_provider=default_provider,
            payroll_tax_percentage=payroll_tax_rate
        )
        
        # Calculate initial costs
        costing_sheet.calculate_all()
        
        # Create risk assessment with default template if available
        default_template = AssessmentQuestionTemplate.objects.filter(is_active=True).first()
        PreSubmissionAssessment.objects.create(
            application=instance,
            assessment_template=default_template
        )


@receiver(post_save, sender=JobApplication)
def create_quotation_for_application(sender, instance, created, **kwargs):
    """
    Create a Quotation automatically when a new job application is created,
    populating only with data that directly exists in the application.
    """
    if created:
        job = instance.job
        rfqts = job.rfqts if job.rfqts else None
        user = instance.user
        
        # Helper function to parse location info from location_of_residence
        def parse_location_info(location_str):
            """Extract suburb/state info from location string"""
            if not location_str:
                return '', '', ''
            parts = [part.strip() for part in location_str.split(',') if part.strip()]
            if len(parts) >= 2:
                return parts[0], parts[1], ''  # suburb, state, postcode
            elif len(parts) == 1:
                return parts[0], '', ''
            return '', '', ''
        
        # Parse location information
        suburb, state, postcode = parse_location_info(instance.location_of_residence)
        
        # Determine if there's a conflict of interest based on application responses
        has_conflict = any([
            instance.potential_conflict,
            instance.worked_on_project,
            instance.worked_on_requirement,
            instance.involved_in_selection,
            instance.currently_aps,
            instance.aps_within_12_months,
            instance.currently_sercat,
            instance.sercat_within_12_months
        ])
        
        # Build security clearance comments from application data
        security_comments = []
        if instance.current_clearance and instance.current_clearance != 'None':
            security_comments.append(f"Current clearance: {instance.current_clearance}")
        if instance.clearance_expiry_date:
            security_comments.append(f"Expiry date: {instance.clearance_expiry_date}")
        if instance.agsva_cs_number:
            security_comments.append(f"AGSVA CS Number: {instance.agsva_cs_number}")
        
        # Quotation data - only direct mappings from application
        quotation_data = {
            'application': instance,
            
            # Basic Information from application/job/rfqts
            'rfqts_no': rfqts.rfqts_no if rfqts else '',
            'task_title': job.title,
            'service_provider_name': instance.full_name,
            'service_provider_abn': instance.abn,
            'location': rfqts.location if rfqts else job.location,
            
            # Personnel CV attachment status
            'personnel_cv_attached': bool(instance.resume),
            
            # Security Requirements from application
            'security_clearance_comments': '\n'.join(security_comments),
            
            # Services - methodology from application experience fields
            'methodology': instance.industry_engagement_experience,
            'conflict_of_interest': not has_conflict,  # Inverted because field asks for "no conflict"
            'other_services_comments': instance.unique_skills,
            
            # Representative Information from application
            'rep_name': instance.full_name,
            'rep_email': user.email if user else '',
            
            # Address from parsed location
            'suburb': suburb,
            'state': state,
            'postcode': postcode,
            
            # Signature from application
            'signature': instance.electronic_signature,
            'signature_date': instance.signature_date,
        }
        
        # Create the quotation
        quotation = Quotation.objects.create(**quotation_data)
        
        # Auto-create QuotationSpecifiedPersonnel entry with applicant
        QuotationSpecifiedPersonnel.objects.create(
            quotation=quotation,
            name=instance.full_name,
            role=job.title
        )
        
        # Auto-create QuotationSkillRate entries from RFQTS skills (no rates)
        if rfqts and rfqts.skills_sets:
            QuotationSkillRate.objects.create(
                quotation=quotation,
                skill_set=rfqts.skills_sets,
                skill_level=rfqts.skills_levels or ''
            )


# ─────────────────────────────────────────────────────────────────────────────
# Create default field mapping if none exists
# ─────────────────────────────────────────────────────────────────────────────
@receiver(post_save, sender=RFQTSFieldMapping)
def create_default_fields(sender, instance, created, **kwargs):
    """
    Create default field configurations when a new mapping is created
    """
    if created and not instance.fields.exists():
        default_fields = [
            {'field_name': 'rfqts_no', 'display_name': 'RFQTS Number', 'pdf_label': 'RFQTS Number:', 'extract_until': 'Department:', 'field_type': 'text', 'order': 1},
            {'field_name': 'department', 'display_name': 'Department', 'pdf_label': 'Department:', 'extract_until': 'Group:', 'field_type': 'text', 'order': 2},
            {'field_name': 'group', 'display_name': 'Group', 'pdf_label': 'Group:', 'extract_until': 'Directorate:', 'field_type': 'text', 'order': 3},
            {'field_name': 'directorate', 'display_name': 'Directorate', 'pdf_label': 'Directorate:', 'extract_until': 'Project/Section:', 'field_type': 'text', 'order': 4},
            {'field_name': 'project_section', 'display_name': 'Project/Section', 'pdf_label': 'Project/Section:', 'extract_until': 'Task Title:', 'field_type': 'text', 'order': 5},
            {'field_name': 'task_title', 'display_name': 'Task Title', 'pdf_label': 'Task Title:', 'extract_until': 'Commencement date', 'field_type': 'text', 'order': 6},
            {'field_name': 'commencement_date_for_task', 'display_name': 'Commencement Date', 'pdf_label': 'Commencement date for Task:', 'extract_until': 'Completion date', 'field_type': 'date', 'order': 7},
            {'field_name': 'completion_date_for_task', 'display_name': 'Completion Date', 'pdf_label': 'Completion date required for Task:', 'extract_until': 'RFQTS Type:', 'field_type': 'date', 'order': 8},
            {'field_name': 'rfqts_type', 'display_name': 'RFQTS Type', 'pdf_label': 'RFQTS Type:', 'extract_until': 'Date RFQTS Received:', 'field_type': 'text', 'order': 9},
            {'field_name': 'date_rfqts_received', 'display_name': 'Date RFQTS Received', 'pdf_label': 'Date RFQTS Received:', 'extract_until': 'Due to SME Gateway', 'field_type': 'date', 'order': 10},
            {'field_name': 'closing_date_for_quotation', 'display_name': 'Closing Date', 'pdf_label': 'Due to SME Gateway by', 'extract_until': 'Skill Set', 'field_type': 'date', 'order': 11},
            {'field_name': 'scope_of_task', 'display_name': 'Scope of Task', 'pdf_label': 'Scope of Task:', 'extract_until': 'Statement of Duties', 'field_type': 'multiline', 'order': 12},
            {'field_name': 'statement_of_duties', 'display_name': 'Statement of Duties', 'pdf_label': 'Statement of Duties', 'extract_until': 'Location(s):', 'field_type': 'multiline', 'order': 13},
            {'field_name': 'location', 'display_name': 'Location(s)', 'pdf_label': 'Location(s):', 'extract_until': 'Deliverables:', 'field_type': 'multiline', 'order': 14},
            {'field_name': 'deliverables', 'display_name': 'Deliverables', 'pdf_label': 'Deliverables:', 'extract_until': 'Specified Personnel:', 'field_type': 'multiline', 'order': 15},
            {'field_name': 'specified_personnel', 'display_name': 'Specified Personnel', 'pdf_label': 'Specified Personnel:', 'extract_until': 'Evaluation Criteria:', 'field_type': 'multiline', 'order': 16},
            {'field_name': 'evaluation_criteria', 'display_name': 'Evaluation Criteria', 'pdf_label': 'Evaluation Criteria:', 'extract_until': 'Applicable Standards', 'field_type': 'multiline', 'order': 17},
            {'field_name': 'applicable_standards_or_references', 'display_name': 'Applicable Standards', 'pdf_label': 'Applicable Standards or references:', 'extract_until': 'Allowances or disbursements:', 'field_type': 'multiline', 'order': 18},
            {'field_name': 'allowances_or_disbursements', 'display_name': 'Allowances/Disbursements', 'pdf_label': 'Allowances or disbursements:', 'extract_until': 'Other relevant information', 'field_type': 'multiline', 'order': 19},
            {'field_name': 'other_relevant_information_or_special_requirements', 'display_name': 'Other Information', 'pdf_label': 'Other relevant information or special requirements:', 'extract_until': 'Special Conditions', 'field_type': 'multiline', 'order': 20},
            {'field_name': 'special_conditions', 'display_name': 'Special Conditions', 'pdf_label': 'Special Conditions', 'extract_until': 'Extension Options', 'field_type': 'multiline', 'order': 21},
            {'field_name': 'extension_options', 'display_name': 'Extension Options', 'pdf_label': 'Extension Options', 'extract_until': 'Security Clearance(s)', 'field_type': 'multiline', 'order': 22},
            {'field_name': 'security_clearances_required_for_personnel', 'display_name': 'Security Clearances', 'pdf_label': 'Security Clearance(s) required for personnel working on this Task:', 'extract_until': 'Security Guidance:', 'field_type': 'multiline', 'order': 23},
            {'field_name': 'security_guidance', 'display_name': 'Security Guidance', 'pdf_label': 'Security Guidance:', 'extract_until': 'Key Result Areas', 'field_type': 'multiline', 'order': 24},
            {'field_name': 'key_result_areas', 'display_name': 'Key Result Areas', 'pdf_label': 'Key Result Areas', 'extract_until': None, 'field_type': 'multiline', 'order': 25},
        ]
        
        for field_data in default_fields:
            RFQTSField.objects.create(mapping_template=instance, **field_data)


# ─────────────────────────────────────────────────────────────────────────────
# Create default service providers and payroll tax rates
# ─────────────────────────────────────────────────────────────────────────────
def create_default_service_providers():
    """Create default service providers"""
    providers = [
        {'name': 'SME Gateway', 'fee_percentage': Decimal('8.00'), 'is_default': True},
        {'name': 'ServeGate', 'fee_percentage': Decimal('8.00'), 'is_default': False},
        {'name': 'Jigsaw', 'fee_percentage': Decimal('0.00'), 'is_default': False},
    ]
    
    for provider_data in providers:
        ServiceProvider.objects.get_or_create(
            name=provider_data['name'],
            defaults=provider_data
        )


def create_default_payroll_tax_rates():
    """Create default payroll tax rates for all states"""
    tax_rates = [
        {'state': 'NSW', 'rate_percentage': Decimal('5.45')},
        {'state': 'VIC', 'rate_percentage': Decimal('4.85')},
        {'state': 'QLD', 'rate_percentage': Decimal('4.75')},
        {'state': 'WA', 'rate_percentage': Decimal('5.50')},
        {'state': 'SA', 'rate_percentage': Decimal('4.95')},
        {'state': 'Tasmania', 'rate_percentage': Decimal('6.10')},
        {'state': 'ACT', 'rate_percentage': Decimal('6.85')},
        {'state': 'NT', 'rate_percentage': Decimal('5.50')},
    ]
    
    for tax_data in tax_rates:
        PayrollTaxRate.objects.get_or_create(
            state=tax_data['state'],
            defaults=tax_data
        )


# ─────────────────────────────────────────────────────────────────────────────
# Signal to create default data on application startup
# ─────────────────────────────────────────────────────────────────────────────
from django.db.models.signals import post_migrate

@receiver(post_migrate)
def create_default_costing_data(sender, **kwargs):
    """Create default costing data after migrations"""
    if sender.name == 'jobs':  # Only run for the jobs app
        create_default_service_providers()
        create_default_payroll_tax_rates()


# ─────────────────────────────────────────────────────────────────────────────
# Additional helper functions
# ─────────────────────────────────────────────────────────────────────────────

def get_payroll_tax_rate_for_state(state):
    """Get the current payroll tax rate for a given state"""
    try:
        tax_rate = PayrollTaxRate.objects.filter(
            state=state,
            is_active=True
        ).first()
        return tax_rate.rate_percentage if tax_rate else Decimal('4.85')
    except:
        return Decimal('4.85')  # Default fallback


def get_default_service_provider():
    """Get the default service provider"""
    try:
        return ServiceProvider.objects.filter(is_default=True, is_active=True).first()
    except:
        return None