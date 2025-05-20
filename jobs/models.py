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
    Job application model
    """
    APPLICATION_STATUS = [
        ('Pending', 'Pending'),
        ('Reviewing', 'Reviewing'),
        ('Interviewed', 'Interviewed'),
        ('Accepted', 'Accepted'),
        ('Rejected', 'Rejected'),
    ]

    job = models.ForeignKey(Job, related_name="applications", on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, related_name="applications", on_delete=models.CASCADE)
    full_name = models.CharField(max_length=200)  
    current_clearance = models.CharField(max_length=200, verbose_name="Current Level of Defence Clearance")  
    clearance_expiry_date = models.DateField(null=True, blank=True, verbose_name="Defence Clearance Expiry Date")  
    clearance_number = models.CharField(max_length=200, verbose_name="AGVSA CS Number", blank=True)  
    location_of_residence = models.CharField(max_length=200) 
    date_of_birth = models.DateField(null=True, blank=True)  
    earliest_start_date = models.DateField(null=True, blank=True, verbose_name="Earliest Start Date")  
    proposed_rate = models.CharField(max_length=200, blank=True, verbose_name="Proposed Contract Rate")  
    proposed_salary = models.CharField(max_length=200, blank=True, verbose_name="Proposed Annual Salary")  
    planned_leave = models.CharField(max_length=200, blank=True, verbose_name="Any Planned Leave") 
    available_for_interview = models.CharField(max_length=200, default='Yes') 
    cover_letter = models.TextField(blank=True)
    resume = models.FileField(upload_to='resumes/', blank=True, null=True)
    submission_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=APPLICATION_STATUS, default="Pending")

    def __str__(self):
        return f"Application for {self.job.title} by {self.full_name}"