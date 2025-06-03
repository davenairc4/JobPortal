from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    RFQTS, Job, Position, Advertisement, JobApplication, 
    Quotation, QuotationSkillRate, QuotationSpecifiedPersonnel, 
    QuotationSubcontractor, QuotationTimeMaterialsItem, 
    QuotationFixedPriceDeliverable
)


# ═════════════════════════════════════════════════════════════════════════════
# QUOTATION INLINE ADMIN CLASSES (Tables within Quotation)
# ═════════════════════════════════════════════════════════════════════════════

class QuotationSkillRateInline(admin.TabularInline):
    """SKILL SETS AND LEVELS / DAILY RATE TABLE"""
    model = QuotationSkillRate
    extra = 1
    fields = [
        'skill_set', 
        'skill_level', 
        'short_term_rate', 
        'long_term_rate'
    ]
    verbose_name = "Skill Set and Rate"
    verbose_name_plural = "SKILL SETS AND LEVELS / DAILY RATE"
    
    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }


class QuotationSpecifiedPersonnelInline(admin.TabularInline):
    """SPECIFIED PERSONNEL TABLE"""
    model = QuotationSpecifiedPersonnel
    extra = 1
    fields = ['name', 'role']
    verbose_name = "Specified Personnel"
    verbose_name_plural = "SPECIFIED PERSONNEL - Names and Roles"


class QuotationSubcontractorInline(admin.TabularInline):
    """SUBCONTRACTORS TO BE USED IN PROVIDING THE SERVICES TABLE"""
    model = QuotationSubcontractor
    extra = 1
    fields = [
        'company_name', 
        'abn', 
        'specified_personnel_names'
    ]
    verbose_name = "Subcontractor"
    verbose_name_plural = "SUBCONTRACTORS TO BE USED IN PROVIDING THE SERVICES"


class QuotationTimeMaterialsItemInline(admin.TabularInline):
    """TIME AND MATERIALS PAYMENT SCHEDULE TABLE"""
    model = QuotationTimeMaterialsItem
    extra = 1
    fields = [
        'skill_set', 
        'skill_level', 
        'days', 
        'daily_rate_short_term', 
        'daily_rate_long_term', 
        'total_price'
    ]
    readonly_fields = ['total_price']
    verbose_name = "Time and Materials Item"
    verbose_name_plural = "TIME AND MATERIALS PAYMENT SCHEDULE"


class QuotationFixedPriceDeliverableInline(admin.TabularInline):
    """FIXED PRICE DELIVERABLES AND PAYMENT SCHEDULE TABLE"""
    model = QuotationFixedPriceDeliverable
    extra = 1
    fields = [
        'deliverable', 
        'delivery_date', 
        'payment'
    ]
    verbose_name = "Fixed Price Deliverable"
    verbose_name_plural = "FIXED PRICE DELIVERABLES AND PAYMENT SCHEDULE"


# ═════════════════════════════════════════════════════════════════════════════
# MAIN ADMIN CLASSES
# ═════════════════════════════════════════════════════════════════════════════

@admin.register(RFQTS)
class RFQTSAdmin(admin.ModelAdmin):
    list_display = [
        'rfqts_no', 
        'task_title', 
        'department', 
        'location', 
        'closing_date_for_quotation', 
        'created_at'
    ]
    list_filter = [
        'department', 
        'location', 
        'rfqts_type', 
        'created_at'
    ]
    search_fields = [
        'rfqts_no', 
        'task_title', 
        'department', 
        'project_section'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = [
        ('Basic Information', {
            'fields': [
                'rfqts_no',
                'task_title',
                'department',
                'group',
                'directorate',
                'project_section'
            ]
        }),
        ('Task Details', {
            'fields': [
                'rfqts_type',
                'service_category',
                'scope_of_task',
                'deliverables',
                'location'
            ]
        }),
        ('Dates', {
            'fields': [
                'commencement_date_for_task',
                'completion_date_for_task',
                'closing_date_for_quotation'
            ]
        }),
        ('Requirements', {
            'fields': [
                'skills_sets',
                'skills_levels',
                'specified_personnel',
                'security_clearances_required_for_personnel'
            ]
        }),
        ('Additional Information', {
            'fields': [
                'evaluation_criteria',
                'applicable_standards_or_references',
                'allowances_or_disbursements',
                'other_relevant_information_or_special_requirements',
                'special_conditions',
                'extension_options'
            ],
            'classes': ['collapse']
        }),
        ('Files and Form', {
            'fields': [
                'quote_form_type',
                'rfq_file'
            ]
        })
    ]


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = [
        'title', 
        'rfqts', 
        'location', 
        'job_type', 
        'clearance', 
        'is_active', 
        'created_by', 
        'submission_date'
    ]
    list_filter = [
        'location', 
        'job_type', 
        'clearance', 
        'is_active', 
        'submission_date'
    ]
    search_fields = [
        'title', 
        'description', 
        'rfqts__rfqts_no', 
        'rfqts__task_title'
    ]
    date_hierarchy = 'submission_date'
    
    fieldsets = [
        ('Basic Information', {
            'fields': [
                'rfqts',
                'title',
                'short_description',
                'description'
            ]
        }),
        ('Job Details', {
            'fields': [
                'location',
                'job_type',
                'salary',
                'clearance'
            ]
        }),
        ('Requirements', {
            'fields': [
                'skills_sets',
                'skills_levels'
            ]
        }),
        ('Dates', {
            'fields': [
                'commencement_date',
                'completion_date',
                'closing_date'
            ]
        }),
        ('Management', {
            'fields': [
                'created_by',
                'is_active'
            ]
        })
    ]


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = [
        'title', 
        'job', 
        'number_of_positions', 
        'is_filled'
    ]
    list_filter = ['is_filled']
    search_fields = ['title', 'job__title']


@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = [
        'job', 
        'status', 
        'publish_date', 
        'expire_date', 
        'is_featured', 
        'view_count'
    ]
    list_filter = [
        'status', 
        'is_featured', 
        'publish_date'
    ]
    search_fields = ['job__title']
    date_hierarchy = 'publish_date'


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = [
        'full_name', 
        'job', 
        'status', 
        'current_clearance', 
        'earliest_start_date', 
        'submission_date'
    ]
    list_filter = [
        'status', 
        'current_clearance', 
        'currently_aps', 
        'currently_sercat', 
        'submission_date'
    ]
    search_fields = [
        'full_name', 
        'user__username', 
        'user__email', 
        'job__title'
    ]
    date_hierarchy = 'submission_date'
    
    fieldsets = [
        ('Application Information', {
            'fields': [
                'job',
                'user',
                'status'
            ]
        }),
        ('Applicant Details', {
            'fields': [
                'full_name',
                'date_of_birth',
                'location_of_residence',
                'abn'
            ]
        }),
        ('Clearance Information', {
            'fields': [
                'current_clearance',
                'clearance_expiry_date',
                'agsva_cs_number'
            ]
        }),
        ('Availability', {
            'fields': [
                'earliest_start_date',
                'proposed_contract_rate',
                'proposed_annual_salary',
                'planned_leave',
                'available_for_interview'
            ]
        }),
        ('Experience', {
            'fields': [
                'industry_engagement_experience',
                'project_expectations',
                'qualifications_certifications'
            ]
        }),
        ('References', {
            'fields': [
                'referee1_name',
                'referee1_email',
                'referee1_phone',
                'referee1_description',
                'referee2_name',
                'referee2_email',
                'referee2_phone',
                'referee2_description'
            ]
        }),
        ('Additional Information', {
            'fields': [
                'additional_materials',
                'unique_skills'
            ],
            'classes': ['collapse']
        }),
        ('Conflict of Interest - Role', {
            'fields': [
                'worked_on_project',
                'worked_on_requirement',
                'involved_in_selection',
                'potential_conflict'
            ],
            'classes': ['collapse']
        }),
        ('APS Defence Conflict of Interest', {
            'fields': [
                'currently_aps',
                'aps_within_12_months',
                'aps_engagement_details',
                'aps_employment_from',
                'aps_employment_to',
                'aps_resignation_evidence'
            ],
            'classes': ['collapse']
        }),
        ('SERCAT Employment', {
            'fields': [
                'currently_sercat',
                'sercat_within_12_months',
                'sercat_engagement_details',
                'sercat_employment_from',
                'sercat_employment_to',
                'sercat_separation_evidence'
            ],
            'classes': ['collapse']
        }),
        ('Application Confirmation', {
            'fields': [
                'written_third_person',
                'cv_no_gaps',
                'cv_month_year_listed'
            ]
        }),
        ('Declaration', {
            'fields': [
                'declaration_complete_correct',
                'declaration_no_other_applications',
                'understand_false_info',
                'understand_additional_enquiries',
                'understand_waiver_approval'
            ]
        }),
        ('Files', {
            'fields': [
                'resume',
                'cover_letter'
            ]
        }),
        ('Signature', {
            'fields': [
                'electronic_signature',
                'signature_date'
            ]
        })
    ]
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return ['submission_date']
        return []


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = [
        'get_application_name',
        'rfqts_no', 
        'task_title', 
        'service_provider_name', 
        'total_price',
        'decline_to_bid',
        'created_at'
    ]
    list_filter = [
        'decline_to_bid',
        'conflict_of_interest',
        'executed_confidentiality_deed',
        'created_at'
    ]
    search_fields = [
        'rfqts_no', 
        'task_title', 
        'service_provider_name',
        'application__full_name'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = [
        ('QUOTATION HEADER', {
            'description': 'Under Defence Support Services (DSS) Standing Offer Deed',
            'fields': [
                'application',
            ],
            'classes': ['wide']
        }),
        ('BASIC QUOTATION DETAILS', {
            'fields': [
                'rfqts_no',
                'task_title', 
                'service_provider_name',
                'service_provider_abn',
                'service_provider_employee_count',
            ]
        }),
        ('LOCATION', {
            'fields': [
                'location'
            ]
        }),
        ('SPECIFIED PERSONNEL', {
            'description': 'Names of Specified Personnel proposed to provide Services and the roles that each will undertake',
            'fields': [
                'complies_clause_2_4',
                'personnel_cv_attached'
            ]
        }),
        ('SUBCONTRACTORS TO BE USED IN PROVIDING THE SERVICES', {
            'fields': [
                'subcontractor_cv_attached',
                'subcontractor_employee_count',
                'subcontractors_indigenous_enterprise'
            ]
        }),
        ('SECURITY REQUIREMENTS', {
            'fields': [
                'security_clearance_comments',
                'security_guidance_comments'
            ]
        }),
        ('KEY RESULT AREAS', {
            'fields': [
                'key_result_areas'
            ]
        }),
        ('CURRENCY OF INSURANCES DETAILED BELOW', {
            'fields': [
                'workers_compensation',
                'professional_indemnity',
                'public_liability',
                'other_insurance_details'
            ]
        }),
        ('SERVICES', {
            'fields': [
                'methodology',
                'plans_attached',
                'gfm',
                'third_party_ip',
                'confidential_info',
                'conflict_of_interest',
                'executed_confidentiality_deed',
                'other_services_comments'
            ]
        }),
        ('DELIVERY SCHEDULE AND PRICING DETAILS (GST Inclusive)', {
            'description': 'Note: Only the pricing data provided within this form will be taken into account in assessing the value for money of any Quotation.',
            'fields': [
                'time_materials_sub_total',
                'time_materials_allowances', 
                'time_materials_other_disbursements',
                'time_materials_total',
                'fixed_price_sub_total',
                'fixed_price_allowances',
                'fixed_price_other_disbursements', 
                'fixed_price_total',
            ]
        }),
        ('TOTAL PRICE OF CONTRACT', {
            'description': 'Note: All prices are GST inclusive',
            'fields': [
                'total_price'
            ],
            'classes': ['wide']
        }),
        ('DECLINE TO BID', {
            'description': 'This area must be filled out by the Service Provider when declining to bid.',
            'fields': [
                'decline_to_bid',
                'decline_no_personnel',
                'decline_full_capacity',
                'decline_unable_location',
                'decline_insufficient_time',
                'decline_conflict_interest',
                'decline_other',
                'decline_other_reason'
            ],
            'classes': ['collapse']
        }),
        ('QUOTATION AUTHORISED BY THE SERVICE PROVIDER', {
            'description': 'Name of Company representative authorising this quotation',
            'fields': [
                'rep_title',
                'rep_name',
                'rep_position',
                'rep_email',
                'rep_telephone',
                'address_line1',
                'address_line2',
                'suburb',
                'state',
                'postcode',
                'signature',
                'signature_date'
            ]
        }),
    ]
    
    inlines = [
        QuotationSkillRateInline,
        QuotationSpecifiedPersonnelInline,
        QuotationSubcontractorInline,
        QuotationTimeMaterialsItemInline,
        QuotationFixedPriceDeliverableInline,
    ]
    
    readonly_fields = [
        'time_materials_total', 
        'fixed_price_total', 
        'total_price'
    ]
    
    def get_application_name(self, obj):
        return obj.application.full_name
    get_application_name.short_description = 'Applicant Name'
    get_application_name.admin_order_field = 'application__full_name'
    
    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj:  # editing an existing object
            readonly.extend(['created_at', 'updated_at'])
        return readonly

    class Media:
        css = {
            'all': ('admin/css/quotation_admin.css',)
        }
        js = ('admin/js/quotation_admin.js',)


# ═════════════════════════════════════════════════════════════════════════════
# STANDALONE TABLE MODEL ADMINS (for individual management if needed)
# ═════════════════════════════════════════════════════════════════════════════

@admin.register(QuotationSkillRate)
class QuotationSkillRateAdmin(admin.ModelAdmin):
    list_display = [
        'quotation', 
        'skill_set', 
        'skill_level', 
        'short_term_rate', 
        'long_term_rate'
    ]
    list_filter = ['skill_level']
    search_fields = [
        'skill_set', 
        'quotation__service_provider_name'
    ]


@admin.register(QuotationSpecifiedPersonnel)
class QuotationSpecifiedPersonnelAdmin(admin.ModelAdmin):
    list_display = [
        'quotation', 
        'name', 
        'role'
    ]
    search_fields = [
        'name', 
        'role', 
        'quotation__service_provider_name'
    ]


@admin.register(QuotationSubcontractor)
class QuotationSubcontractorAdmin(admin.ModelAdmin):
    list_display = [
        'quotation', 
        'company_name', 
        'abn'
    ]
    search_fields = [
        'company_name', 
        'abn', 
        'quotation__service_provider_name'
    ]


@admin.register(QuotationTimeMaterialsItem)
class QuotationTimeMaterialsItemAdmin(admin.ModelAdmin):
    list_display = [
        'quotation', 
        'skill_set', 
        'skill_level', 
        'days', 
        'get_daily_rate', 
        'total_price'
    ]
    list_filter = ['skill_level']
    search_fields = [
        'skill_set', 
        'quotation__service_provider_name'
    ]
    readonly_fields = ['total_price']
    
    def get_daily_rate(self, obj):
        rate = obj.daily_rate_long_term if obj.daily_rate_long_term else obj.daily_rate_short_term
        return f"${rate}" if rate else "Not set"
    get_daily_rate.short_description = 'Daily Rate'


@admin.register(QuotationFixedPriceDeliverable)
class QuotationFixedPriceDeliverableAdmin(admin.ModelAdmin):
    list_display = [
        'quotation', 
        'get_deliverable_short', 
        'delivery_date', 
        'payment'
    ]
    list_filter = ['delivery_date']
    search_fields = [
        'deliverable', 
        'quotation__service_provider_name'
    ]
    date_hierarchy = 'delivery_date'
    
    def get_deliverable_short(self, obj):
        return obj.deliverable[:50] + "..." if len(obj.deliverable) > 50 else obj.deliverable
    get_deliverable_short.short_description = 'Deliverable'


# ═════════════════════════════════════════════════════════════════════════════
# ADMIN SITE CUSTOMIZATION
# ═════════════════════════════════════════════════════════════════════════════

admin.site.site_header = "Defence Support Services (DSS) Administration"
admin.site.site_title = "DSS Admin Portal"
admin.site.index_title = "Welcome to DSS Administration"

# Custom CSS for better visual organization
admin.site.enable_nav_sidebar = True