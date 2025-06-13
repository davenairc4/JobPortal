from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.contrib import messages
from django.contrib.admin import SimpleListFilter
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from .models import (
    RFQTS, Job, Position, Advertisement, JobApplication, 
    Quotation, QuotationSkillRate, QuotationSpecifiedPersonnel, 
    QuotationSubcontractor, QuotationTimeMaterialsItem, 
    QuotationFixedPriceDeliverable, C4CostingSheet, PreSubmissionAssessment, 
    AssessmentQuestionTemplate, ServiceProvider, PayrollTaxRate
)


# ═════════════════════════════════════════════════════════════════════════════
# CUSTOM FILTERS FOR BETTER MANAGEMENT
# ═════════════════════════════════════════════════════════════════════════════

class RiskLevelFilter(SimpleListFilter):
    title = 'Risk Level'
    parameter_name = 'risk_level'

    def lookups(self, request, model_admin):
        return [
            ('low', 'Low Risk'),
            ('medium', 'Medium Risk'),
            ('high', 'High Risk'),
            ('no_assessment', 'No Assessment'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'low':
            return queryset.filter(risk_assessment__overall_risk_level='Low')
        elif self.value() == 'medium':
            return queryset.filter(risk_assessment__overall_risk_level='Medium')
        elif self.value() == 'high':
            return queryset.filter(risk_assessment__overall_risk_level='High')
        elif self.value() == 'no_assessment':
            return queryset.filter(risk_assessment__isnull=True)


class SubmissionReadinessFilter(SimpleListFilter):
    title = 'Submission Status'
    parameter_name = 'submission_status'

    def lookups(self, request, model_admin):
        return [
            ('ready', 'Ready for Submission'),
            ('not_ready', 'Not Ready'),
            ('submitted', 'Already Submitted'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'ready':
            return queryset.filter(risk_assessment__ready_for_submission=True, risk_assessment__submitted_to_client=False)
        elif self.value() == 'not_ready':
            return queryset.filter(risk_assessment__ready_for_submission=False)
        elif self.value() == 'submitted':
            return queryset.filter(risk_assessment__submitted_to_client=True)


class MarginRangeFilter(SimpleListFilter):
    title = 'Margin Range'
    parameter_name = 'margin_range'

    def lookups(self, request, model_admin):
        return [
            ('negative', 'Negative Margin'),
            ('0_10', '0-10%'),
            ('10_20', '10-20%'),
            ('20_30', '20-30%'),
            ('30_plus', '30%+'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'negative':
            return queryset.filter(c4_costing__margin_percentage__lt=0)
        elif self.value() == '0_10':
            return queryset.filter(c4_costing__margin_percentage__gte=0, c4_costing__margin_percentage__lt=10)
        elif self.value() == '10_20':
            return queryset.filter(c4_costing__margin_percentage__gte=10, c4_costing__margin_percentage__lt=20)
        elif self.value() == '20_30':
            return queryset.filter(c4_costing__margin_percentage__gte=20, c4_costing__margin_percentage__lt=30)
        elif self.value() == '30_plus':
            return queryset.filter(c4_costing__margin_percentage__gte=30)


# ═════════════════════════════════════════════════════════════════════════════
# INLINE ADMIN CLASSES FOR C4 COSTING AND RISK ASSESSMENT
# ═════════════════════════════════════════════════════════════════════════════

class C4CostingSheetInline(admin.StackedInline):
    """Inline C4 costing sheet based on spreadsheet structure"""
    model = C4CostingSheet
    extra = 0
    
    fieldsets = [
        ('KEY VARIABLES (Administration Editable)', {
            'fields': [
                'use_gateway_servegate',
                'payroll_tax_applicable',
                'management_fee_percentage',
                'payroll_tax_percentage',
            ],
            'classes': ['wide'],
            'description': format_html('<strong style="color: red;">C4 Administration: Edit these key variables to control all calculations</strong>')
        }),
        ('SERVICE PROVIDER SELECTION', {
            'fields': [
                'service_provider',
            ],
            'description': format_html('<strong style="color: blue;">Choose service provider (SME Gateway, ServeGate, etc.)</strong>')
        }),
        ('CUSTOMER CEILING RATE', {
            'fields': [
                'customer_ceiling_rate_gst_inc',
                'customer_ceiling_rate_gst_ex',
                'ceiling_rate_saving_percentage',
            ],
            'classes': ['wide'],
        }),
        ('CANDIDATE NEEDS', {
            'fields': [
                'equipment_cost_gst_inc',
                'training_memberships_cost_gst_inc',
            ]
        }),
        ('CALCULATOR (Core Charges)', {
            'fields': [
                'charge_to_c4_client_gst_inc',
                'charge_to_c4_client_gst_ex',
                'charge_to_c4_client_gst',
            ],
            'description': 'Primary client charge rates'
        }),
        ('GATEWAY & TAX CALCULATIONS', {
            'fields': [
                'gateway_fee_gst_inc',
                'gateway_fee_gst_ex', 
                'gateway_fee_gst',
                'payroll_tax_amount',
                'gst_difference_to_ato',
            ],
            'classes': ['collapse'],
        }),
        ('PAYMENT BREAKDOWN', {
            'fields': [
                'subtotal_payment_to_c4_gst_inc',
                'subtotal_payment_to_c4_gst_ex',
                'subtotal_payment_to_c4_gst',
                'payment_to_service_provider',
                'net_payment_to_c4_gst_inc',
                'net_payment_to_c4_gst_ex',
            ],
            'classes': ['collapse'],
        }),
        ('CANDIDATE COST CALCULATION', {
            'fields': [
                'candidate_cost_to_c4_gst_inc',
                'candidate_cost_to_c4_gst_ex',
                'hourly_rate_gst_inc',
                'hourly_rate_gst_ex',
                'superannuation_percentage',
            ]
        }),
        ('MARGIN ANALYSIS', {
            'fields': [
                'margin_amount',
                'margin_percentage',
            ],
            'classes': ['wide'],
        }),
        ('PROJECT TOTALS', {
            'fields': [
                'project_days',
                'project_total_cost',
                'travel_costs',
                'project_grand_total',
            ],
            'classes': ['wide'],
        }),
        ('ANNUAL PACKAGE EQUIVALENT', {
            'fields': [
                'equivalent_annual_package',
                'standard_annual_salary',
            ]
        }),
        ('WORKING DAYS CALCULATION', {
            'fields': [
                'days_per_week',
                'weekdays_in_year',
                'public_holidays',
                'annual_leave_days',
                'sick_leave_days',
                'net_days_worked',
                'calculation_year',
            ],
            'classes': ['collapse'],
        }),
        ('CONTROLS & NOTES', {
            'fields': [
                'manual_override',
                'notes',
                'calculated_by',
                'last_calculated',
            ],
            'classes': ['collapse'],
        }),
    ]
    
    readonly_fields = [
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
        'equivalent_annual_package', 'standard_annual_salary',
        'net_days_worked',
        'last_calculated', 'calculated_by'
    ]
    
    def save_model(self, request, obj, form, change):
        obj.calculated_by = request.user
        super().save_model(request, obj, form, change)


class PreSubmissionAssessmentInline(admin.StackedInline):
    """Inline risk assessment for job applications"""
    model = PreSubmissionAssessment
    extra = 0
    
    fieldsets = [
        ('Assessment Template Selection', {
            'fields': [
                'assessment_template',
            ],
            'classes': ['wide'],
            'description': format_html('<strong style="color: blue;">Select a template to load custom assessment questions</strong>')
        }),
        ('Standard Risk Assessment Checklist', {
            'fields': [
                'all_responses_checked',
                'clearance_verified',
                'cv_reviewed',
                'references_contacted',
                'costing_approved',
                'conflict_assessed',
                'waiver_processed',
                'client_requirements_met',
            ],
            'classes': ['wide'],
            'description': 'Complete all checks before marking as ready for submission'
        }),
        ('Custom Assessment Questions', {
            'fields': [
                'custom_assessment_display',
            ],
            'classes': ['wide'],
            'description': 'Additional assessment questions from selected template'
        }),
        ('Assessment Results', {
            'fields': [
                'overall_risk_level',
                'ready_for_submission',
                'risk_notes',
            ],
            'classes': ['wide'],
        }),
        ('Submission Tracking', {
            'fields': [
                'submitted_to_client',
                'submission_date',
                'submitted_by',
            ],
            'classes': ['collapse'],
        }),
        ('Assessment Metadata', {
            'fields': [
                'assessed_by',
                'assessed_at',
            ],
            'classes': ['collapse'],
        }),
    ]
    
    readonly_fields = ['assessed_at', 'assessed_by', 'custom_assessment_display']
    
    def custom_assessment_display(self, obj):
        """Display custom assessment questions for editing"""
        if not obj or not obj.assessment_template:
            return format_html('<p style="color: gray;">Select an assessment template above to load custom questions.</p>')
        
        questions = obj.get_template_questions()
        if not questions:
            return format_html('<p style="color: gray;">No questions found in selected template.</p>')
        
        html_parts = []
        for i, question in enumerate(questions):
            question_html = f"""
            <div style="margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 4px;">
                <label style="font-weight: bold; display: block; margin-bottom: 5px;">
                    Q{i+1}: {question['question']}
                    {'<span style="color: red;">*</span>' if question['required'] else ''}
                </label>
            """
            
            if question['type'] == 'boolean':
                checked = 'checked' if question['answer'] in ['true', 'True', True] else ''
                question_html += f"""
                <div>
                    <input type="checkbox" name="custom_q_{question['id']}" {checked} disabled>
                    <span style="margin-left: 5px;">Yes</span>
                </div>
                """
            else:
                question_html += f"""
                <textarea name="custom_q_{question['id']}" rows="2" style="width: 100%; padding: 5px;" readonly>{question['answer']}</textarea>
                """
            
            question_html += "</div>"
            html_parts.append(question_html)
        
        # Add note about editing custom questions
        note = """
        <div style="background: #e8f4f8; padding: 10px; border-radius: 4px; margin-top: 15px;">
            <strong>Note:</strong> To edit custom assessment responses, go to the standalone Pre-Submission Risk Assessment admin.
        </div>
        """
        
        return format_html(''.join(html_parts) + note)
    
    custom_assessment_display.short_description = 'Custom Assessment Questions'
    
    def save_model(self, request, obj, form, change):
        obj.assessed_by = request.user
        super().save_model(request, obj, form, change)


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
        'created_at',
        'pdf_status'
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
                'statement_of_duties',
                'deliverables',
                'location'
            ]
        }),
        ('Dates', {
            'fields': [
                'date_rfqts_received',
                'commencement_date_for_task',
                'completion_date_for_task',
                'closing_date_for_quotation'
            ]
        }),
        ('Requirements', {
            'fields': [
                'skills_sets',
                'skills_levels',
                'max_rate_per_day',
                'max_cvs',
                'specified_personnel',
                'security_clearances_required_for_personnel',
                'security_guidance'
            ]
        }),
        ('Additional Information', {
            'fields': [
                'evaluation_criteria',
                'key_result_areas',
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
            ],
            'description': mark_safe('<strong>Upload a PDF file to automatically extract and populate form fields.</strong><br>Supported format: RFQTS PDF documents')
        })
    ]

    def pdf_status(self, obj):
        """Display PDF upload status"""
        if obj.rfq_file:
            return format_html(
                '<span style="color: green;">✓ PDF Uploaded</span>'
            )
        return format_html(
            '<span style="color: gray;">− No PDF</span>'
        )
    pdf_status.short_description = 'PDF Status'

    def save_model(self, request, obj, form, change):
        """Override save to trigger PDF extraction when file is uploaded"""
        # Store original values to check what was extracted
        original_values = {}
        if change and obj.rfq_file:
            for field in obj._meta.fields:
                if hasattr(obj, field.name):
                    original_values[field.name] = getattr(obj, field.name)
        
        # Check if this is an update and if a new file was uploaded
        if change and 'rfq_file' in form.changed_data and obj.rfq_file:
            # Save first to ensure file is properly stored
            super().save_model(request, obj, form, change)
            
            # Extract data from PDF
            extraction_successful = obj.extract_pdf_data()
            
            if extraction_successful:
                # Save again with extracted data
                obj.save()
                
                # Build list of extracted fields
                extracted_fields = []
                for field_name, original_value in original_values.items():
                    new_value = getattr(obj, field_name)
                    if str(original_value) != str(new_value) and new_value:
                        field = obj._meta.get_field(field_name)
                        verbose_name = field.verbose_name if hasattr(field, 'verbose_name') else field_name
                        extracted_fields.append(verbose_name)
                
                if extracted_fields:
                    fields_list = ', '.join(extracted_fields[:5])
                    if len(extracted_fields) > 5:
                        fields_list += f' and {len(extracted_fields) - 5} more fields'
                    
                    messages.success(
                        request, 
                        format_html(
                            'PDF data extracted successfully from <strong>{}</strong>!<br>'
                            'Populated fields: {}',
                            obj.rfq_file.name,
                            fields_list
                        )
                    )
                else:
                    messages.info(
                        request,
                        f'PDF "{obj.rfq_file.name}" processed but no new data was extracted. The document may not contain recognizable RFQTS fields.'
                    )
            else:
                messages.warning(
                    request,
                    format_html(
                        'PDF "<strong>{}</strong>" uploaded but data extraction failed. '
                        'Please check the file format and ensure it\'s a valid RFQTS document, '
                        'or fill fields manually.',
                        obj.rfq_file.name
                    )
                )
        elif not change and obj.rfq_file:
            # New object with PDF file
            # Save first to get the file properly stored
            super().save_model(request, obj, form, change)
            
            # Then extract data
            extraction_successful = obj.extract_pdf_data()
            
            if extraction_successful:
                # Save again with extracted data
                obj.save()
                messages.success(
                    request, 
                    format_html(
                        'PDF data extracted successfully from <strong>{}</strong>! '
                        'Please review all populated fields.',
                        obj.rfq_file.name
                    )
                )
            else:
                messages.warning(
                    request,
                    format_html(
                        'PDF "<strong>{}</strong>" uploaded but data extraction failed. '
                        'Please check the file format and ensure it\'s a valid RFQTS document, '
                        'or fill fields manually.',
                        obj.rfq_file.name
                    )
                )
        else:
            # Normal save without PDF upload
            super().save_model(request, obj, form, change)


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


# ═════════════════════════════════════════════════════════════════════════════
# ENHANCED JOB APPLICATION ADMIN WITH C4 COSTING MANAGEMENT
# ═════════════════════════════════════════════════════════════════════════════

@admin.register(JobApplication)
class EnhancedJobApplicationAdmin(admin.ModelAdmin):
    list_display = [
        'full_name', 
        'job', 
        'status_badge',
        'risk_level_badge',
        'submission_readiness',
        'client_charge_rate_display',
        'margin_display',
        'submission_date'
    ]
    
    list_filter = [
        'status', 
        RiskLevelFilter,
        SubmissionReadinessFilter,
        MarginRangeFilter,
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
    
    # Prominent status editing at the top
    fieldsets = [
        ('APPLICATION STATUS & MANAGEMENT', {
            'fields': [
                'status',
                'job',
                'user',
            ],
            'classes': ['wide'],
            'description': format_html('<strong style="color: red;">C4 Administration: Edit status and review application details</strong>')
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
        ('Experience (Administration Editable)', {
            'fields': [
                'industry_engagement_experience',
                'project_expectations',
                'qualifications_certifications'
            ],
            'classes': ['wide'],
            'description': format_html('<strong style="color: blue;">C4 Administration can modify candidate responses here</strong>')
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
        ('Conflict of Interest', {
            'fields': [
                'worked_on_project',
                'worked_on_requirement',
                'involved_in_selection',
                'potential_conflict'
            ],
            'classes': ['collapse']
        }),
        ('APS Defence Conflict', {
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
        ('Additional Information', {
            'fields': [
                'additional_materials',
                'unique_skills'
            ],
            'classes': ['collapse']
        }),
        ('Files', {
            'fields': [
                'resume',
                'cover_letter'
            ]
        }),
        ('Declaration & Signature', {
            'fields': [
                'declaration_complete_correct',
                'declaration_no_other_applications',
                'understand_false_info',
                'understand_additional_enquiries',
                'understand_waiver_approval',
                'electronic_signature',
                'signature_date'
            ]
        })
    ]
    
    inlines = [
        C4CostingSheetInline,
        PreSubmissionAssessmentInline,
    ]
    
    actions = [
        'mark_ready_for_submission',
        'mark_submitted_to_client',
        'recalculate_c4_costing',
        'bulk_update_payroll_tax',
        'bulk_update_margin',
    ]
    
    def status_badge(self, obj):
        colors = {
            'Pending': 'orange',
            'Reviewing': 'blue',
            'Interviewed': 'purple',
            'Accepted': 'green',
            'Rejected': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.status
        )
    status_badge.short_description = 'Status'
    
    def risk_level_badge(self, obj):
        if hasattr(obj, 'risk_assessment'):
            level = obj.risk_assessment.overall_risk_level
            colors = {'Low': 'green', 'Medium': 'orange', 'High': 'red'}
            color = colors.get(level, 'gray')
            return format_html(
                '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
                color, level
            )
        return format_html('<span style="color: gray;">No Assessment</span>')
    risk_level_badge.short_description = 'Risk Level'
    
    def submission_readiness(self, obj):
        if hasattr(obj, 'risk_assessment'):
            if obj.risk_assessment.submitted_to_client:
                return format_html('<span style="color: green;">✅ Submitted</span>')
            elif obj.risk_assessment.ready_for_submission:
                return format_html('<span style="color: blue;">Ready</span>')
            else:
                completion = obj.risk_assessment.completion_percentage
                return format_html('<span style="color: orange;">⏳ {}%</span>', int(completion))
        return format_html('<span style="color: gray;">❌ No Assessment</span>')
    submission_readiness.short_description = 'Submission Status'
    
    def client_charge_rate_display(self, obj):
        if hasattr(obj, 'c4_costing') and obj.c4_costing.charge_to_c4_client_gst_inc:
            return format_html('<strong>${}/day</strong>', obj.c4_costing.charge_to_c4_client_gst_inc)
        return format_html('<span style="color: gray;">Not calculated</span>')
    client_charge_rate_display.short_description = 'Client Rate'
    
    def margin_display(self, obj):
        if hasattr(obj, 'c4_costing') and obj.c4_costing.margin_percentage is not None:
            margin = obj.c4_costing.margin_percentage
            if margin < 0:
                color = 'red'
            elif margin < 10:
                color = 'orange'
            else:
                color = 'green'
            return format_html('<span style="color: {};">{}%</span>', color, margin)
        return format_html('<span style="color: gray;">Not calculated</span>')
    margin_display.short_description = 'Margin'
    
    def mark_ready_for_submission(self, request, queryset):
        count = 0
        for application in queryset:
            if hasattr(application, 'risk_assessment'):
                application.risk_assessment.ready_for_submission = True
                application.risk_assessment.save()
                count += 1
        self.message_user(request, f'{count} applications marked as ready for submission.')
    mark_ready_for_submission.short_description = "Mark as ready for submission"
    
    def mark_submitted_to_client(self, request, queryset):
        count = 0
        for application in queryset:
            if hasattr(application, 'risk_assessment'):
                application.risk_assessment.submitted_to_client = True
                application.risk_assessment.submission_date = timezone.now()
                application.risk_assessment.submitted_by = request.user
                application.risk_assessment.save()
                count += 1
        self.message_user(request, f'{count} applications marked as submitted to client.')
    mark_submitted_to_client.short_description = "Mark as submitted to client"
    
    def recalculate_c4_costing(self, request, queryset):
        count = 0
        for application in queryset:
            if hasattr(application, 'c4_costing'):
                application.c4_costing.calculate_all()
                count += 1
        self.message_user(request, f'Recalculated C4 costing for {count} applications.')
    recalculate_c4_costing.short_description = "Recalculate C4 costing"
    
    def bulk_update_payroll_tax(self, request, queryset):
        count = 0
        for application in queryset:
            if hasattr(application, 'c4_costing'):
                # Update payroll tax based on job location
                if application.job.location:
                    from .models import PayrollTaxRate
                    tax_rate_obj = PayrollTaxRate.objects.filter(
                        state=application.job.location, 
                        is_active=True
                    ).first()
                    if tax_rate_obj:
                        application.c4_costing.payroll_tax_percentage = tax_rate_obj.rate_percentage
                        application.c4_costing.calculate_all()
                        count += 1
        self.message_user(request, f'Updated payroll tax rates for {count} applications based on location.')
    bulk_update_payroll_tax.short_description = "Update payroll tax rates by location"
    
    def bulk_update_margin(self, request, queryset):
        # This would be implemented as a custom admin view with a form
        # For now, just show a message
        self.message_user(request, 'Bulk margin update: Use individual costing sheets to modify margins.')
    bulk_update_margin.short_description = "Bulk update margin settings"

    def get_readonly_fields(self, request, obj=None):
        readonly = ['submission_date']
        if obj:  # editing an existing object
            readonly.extend([])
        return readonly


# ═════════════════════════════════════════════════════════════════════════════
# COSTING MANAGEMENT ADMIN CLASSES
# ═════════════════════════════════════════════════════════════════════════════

@admin.register(ServiceProvider)
class ServiceProviderAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'fee_percentage',
        'fee_fixed_amount',
        'is_active',
        'is_default',
        'updated_at'
    ]
    
    list_filter = [
        'is_active',
        'is_default',
        'created_at'
    ]
    
    search_fields = ['name']
    
    fieldsets = [
        ('Provider Information', {
            'fields': [
                'name',
                'is_active',
                'is_default'
            ]
        }),
        ('Fee Structure', {
            'fields': [
                'fee_percentage',
                'fee_fixed_amount'
            ],
            'description': 'Configure the fee structure for this service provider'
        }),
        ('Metadata', {
            'fields': [
                'created_at',
                'updated_at'
            ]
        })
    ]
    
    readonly_fields = ['created_at', 'updated_at']
    
    actions = ['make_default_provider']
    
    def make_default_provider(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, 'Please select exactly one provider to make default.', level=messages.ERROR)
            return
        
        provider = queryset.first()
        # Clear existing default
        ServiceProvider.objects.update(is_default=False)
        # Set new default
        provider.is_default = True
        provider.save()
        
        self.message_user(request, f'{provider.name} is now the default service provider.')
    make_default_provider.short_description = "Make selected provider the default"


@admin.register(PayrollTaxRate)
class PayrollTaxRateAdmin(admin.ModelAdmin):
    list_display = [
        'state',
        'rate_percentage',
        'effective_from',
        'is_active',
        'updated_at'
    ]
    
    list_filter = [
        'is_active',
        'effective_from',
        'state'
    ]
    
    search_fields = ['state']
    
    fieldsets = [
        ('Tax Rate Information', {
            'fields': [
                'state',
                'rate_percentage',
                'effective_from',
                'is_active'
            ]
        }),
        ('Metadata', {
            'fields': [
                'created_at',
                'updated_at'
            ]
        })
    ]
    
    readonly_fields = ['created_at', 'updated_at']
    
    actions = ['activate_selected', 'deactivate_selected']
    
    def activate_selected(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} tax rates activated.')
    activate_selected.short_description = "Activate selected tax rates"
    
    def deactivate_selected(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} tax rates deactivated.')
    deactivate_selected.short_description = "Deactivate selected tax rates"


@admin.register(C4CostingSheet)
class C4CostingSheetAdmin(admin.ModelAdmin):
    list_display = [
        'application',
        'charge_to_c4_client_gst_inc',
        'candidate_cost_display',
        'margin_display',
        'service_provider',
        'payroll_tax_percentage',
        'last_calculated'
    ]
    
    list_filter = [
        'service_provider',
        'use_gateway_servegate',
        'payroll_tax_applicable',
        'manual_override',
        'last_calculated'
    ]
    
    search_fields = [
        'application__full_name',
        'application__job__title'
    ]
    
    fieldsets = [
        ('Application Link', {
            'fields': ['application']
        }),
        ('KEY VARIABLES (Administration Editable)', {
            'fields': [
                'use_gateway_servegate',
                'payroll_tax_applicable',
                'management_fee_percentage',
                'payroll_tax_percentage',
            ],
            'classes': ['wide'],
            'description': format_html('<strong style="color: red;">C4 Administration: Edit these key variables to control all calculations</strong>')
        }),
        ('SERVICE PROVIDER', {
            'fields': [
                'service_provider',
            ]
        }),
        ('CUSTOMER CEILING RATE', {
            'fields': [
                'customer_ceiling_rate_gst_inc',
                'customer_ceiling_rate_gst_ex',
                'ceiling_rate_saving_percentage',
            ]
        }),
        ('CANDIDATE NEEDS', {
            'fields': [
                'equipment_cost_gst_inc',
                'training_memberships_cost_gst_inc',
            ]
        }),
        ('CORE CALCULATIONS', {
            'fields': [
                'charge_to_c4_client_gst_inc',
                'charge_to_c4_client_gst_ex',
                'charge_to_c4_client_gst',
                'gateway_fee_gst_inc',
                'gateway_fee_gst_ex', 
                'gateway_fee_gst',
                'payroll_tax_amount',
                'gst_difference_to_ato',
            ],
            'classes': ['wide']
        }),
        ('PAYMENT CALCULATIONS', {
            'fields': [
                'subtotal_payment_to_c4_gst_inc',
                'subtotal_payment_to_c4_gst_ex',
                'subtotal_payment_to_c4_gst',
                'payment_to_service_provider',
                'net_payment_to_c4_gst_inc',
                'net_payment_to_c4_gst_ex',
            ]
        }),
        ('CANDIDATE CALCULATIONS', {
            'fields': [
                'candidate_cost_to_c4_gst_inc',
                'candidate_cost_to_c4_gst_ex',
                'hourly_rate_gst_inc',
                'hourly_rate_gst_ex',
                'superannuation_percentage',
            ]
        }),
        ('MARGIN & PROFITABILITY', {
            'fields': [
                'margin_amount',
                'margin_percentage',
            ]
        }),
        ('PROJECT TOTALS', {
            'fields': [
                'project_days',
                'project_total_cost',
                'travel_costs',
                'project_grand_total',
            ]
        }),
        ('ANNUAL EQUIVALENTS', {
            'fields': [
                'equivalent_annual_package',
                'standard_annual_salary',
                'days_per_week',
                'weekdays_in_year',
                'public_holidays',
                'annual_leave_days',
                'sick_leave_days',
                'net_days_worked',
            ]
        }),
        ('CONTROLS', {
            'fields': [
                'manual_override',
                'calculation_year',
                'notes',
                'calculated_by',
                'last_calculated'
            ]
        })
    ]
    
    readonly_fields = [
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
        'equivalent_annual_package', 'standard_annual_salary', 'net_days_worked',
        'last_calculated', 'calculated_by'
    ]
    
    actions = ['recalculate_selected_costings', 'apply_standard_rates']
    
    def candidate_cost_display(self, obj):
        if obj.candidate_cost_to_c4_gst_inc:
            return format_html('<strong>${}/day</strong>', obj.candidate_cost_to_c4_gst_inc)
        return format_html('<span style="color: gray;">Not calculated</span>')
    candidate_cost_display.short_description = 'Candidate Cost'
    
    def margin_display(self, obj):
        if obj.margin_percentage is not None:
            margin = obj.margin_percentage
            if margin < 0:
                color = 'red'
            elif margin < 10:
                color = 'orange'
            else:
                color = 'green'
            return format_html('<span style="color: {};">{}%</span>', color, margin)
        return format_html('<span style="color: gray;">Not calculated</span>')
    margin_display.short_description = 'Margin'
    
    def recalculate_selected_costings(self, request, queryset):
        count = 0
        for costing in queryset:
            costing.calculate_all()
            count += 1
        self.message_user(request, f'Recalculated {count} costing sheets.')
    recalculate_selected_costings.short_description = "Recalculate selected costings"
    
    def apply_standard_rates(self, request, queryset):
        count = 0
        for costing in queryset:
            # Apply standard rates based on location
            if costing.application.job.location:
                tax_rate_obj = PayrollTaxRate.objects.filter(
                    state=costing.application.job.location, 
                    is_active=True
                ).first()
                if tax_rate_obj:
                    costing.payroll_tax_percentage = tax_rate_obj.rate_percentage
            
            # Apply default service provider
            default_provider = ServiceProvider.objects.filter(is_default=True).first()
            if default_provider:
                costing.service_provider = default_provider
                costing.management_fee_percentage = default_provider.fee_percentage
            
            costing.calculate_all()
            count += 1
        self.message_user(request, f'Applied standard rates to {count} costing sheets.')
    apply_standard_rates.short_description = "Apply standard rates and providers"
    
    def save_model(self, request, obj, form, change):
        obj.calculated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(PreSubmissionAssessment)
class PreSubmissionAssessmentAdmin(admin.ModelAdmin):
    list_display = [
        'application',
        'completion_badge',
        'template_used',
        'overall_risk_level',
        'ready_for_submission',
        'submitted_to_client',
        'assessed_at'
    ]
    
    list_filter = [
        'assessment_template',
        'overall_risk_level',
        'ready_for_submission',
        'submitted_to_client',
        'assessed_at'
    ]
    
    search_fields = [
        'application__full_name',
        'application__job__title'
    ]
    
    fieldsets = [
        ('Application Link', {
            'fields': ['application']
        }),
        ('Assessment Template', {
            'fields': [
                'assessment_template',
                'template_questions_display',
            ],
            'classes': ['wide'],
            'description': 'Select and configure assessment template'
        }),
        ('Risk Assessment Checklist', {
            'fields': [
                'all_responses_checked',
                'clearance_verified',
                'cv_reviewed',
                'references_contacted',
                'costing_approved',
                'conflict_assessed',
                'waiver_processed',
                'client_requirements_met'
            ],
            'classes': ['wide'],
            'description': 'Complete all checks before marking as ready for submission'
        }),
        ('Custom Assessment Questions', {
            'fields': [
                'custom_assessment_editor',
            ],
            'classes': ['wide'],
            'description': 'Answer custom questions from selected template'
        }),
        ('Assessment Results', {
            'fields': [
                'overall_risk_level',
                'ready_for_submission',
                'risk_notes'
            ],
            'classes': ['wide']
        }),
        ('Submission Management', {
            'fields': [
                'submitted_to_client',
                'submission_date',
                'submitted_by'
            ]
        }),
        ('Metadata', {
            'fields': [
                'assessed_by',
                'assessed_at'
            ]
        })
    ]
    
    readonly_fields = ['assessed_at', 'assessed_by', 'template_questions_display', 'custom_assessment_editor']
    
    actions = ['mark_ready_for_submission', 'mark_submitted', 'load_default_template']
    
    def template_used(self, obj):
        """Display which template is being used"""
        if obj.assessment_template:
            return format_html(
                '<span style="color: green;">{}</span>',
                obj.assessment_template.name
            )
        return format_html('<span style="color: gray;">No template</span>')
    template_used.short_description = 'Template'
    
    def template_questions_display(self, obj):
        """Display questions from selected template"""
        if not obj.assessment_template:
            return format_html('<p style="color: gray;">No template selected</p>')
        
        questions = obj.assessment_template.questions
        if not questions:
            return format_html('<p style="color: gray;">No questions in template</p>')
        
        html_parts = ['<div style="background: #f9f9f9; padding: 10px; border-radius: 4px;">']
        html_parts.append(f'<h4>Template: {obj.assessment_template.name}</h4>')
        html_parts.append('<ul>')
        
        for i, q in enumerate(questions, 1):
            required = ' <span style="color: red;">*</span>' if q.get('required') else ''
            q_type = q.get('type', 'text').title()
            html_parts.append(f'<li><strong>Q{i}:</strong> {q.get("question", "")}{required} <em>({q_type})</em></li>')
        
        html_parts.append('</ul></div>')
        return format_html(''.join(html_parts))
    
    template_questions_display.short_description = 'Template Questions'
    
    def custom_assessment_editor(self, obj):
        """Custom editor for assessment questions"""
        if not obj.assessment_template:
            return format_html(
                '<p style="color: orange; font-weight: bold;">Select an assessment template above and save to load custom questions.</p>'
            )
        
        questions = obj.get_template_questions()
        if not questions:
            return format_html('<p style="color: gray;">No questions available.</p>')
        
        html_parts = ['<div id="custom-assessment-editor">']
        
        for question in questions:
            # Create a unique field name for each question
            field_name = f"custom_assessment_{question['id']}"
            
            html_parts.append(f'''
            <div style="margin: 15px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; background: #fafafa;">
                <label style="font-weight: bold; display: block; margin-bottom: 8px;">
                    {question['question']}
                    {'<span style="color: red; margin-left: 5px;">*Required</span>' if question['required'] else ''}
                </label>
            ''')
            
            if question['type'] == 'boolean':
                checked = 'checked' if str(question['answer']).lower() in ['true', '1', 'yes'] else ''
                html_parts.append(f'''
                <div>
                    <input type="checkbox" id="{field_name}" {checked} style="margin-right: 8px;" disabled>
                    <label for="{field_name}">Yes</label>
                    <p style="font-size: 12px; color: #666; margin-top: 5px;">
                        Current answer: {'Yes' if checked else 'No'}
                    </p>
                </div>
                ''')
            else:
                html_parts.append(f'''
                <textarea id="{field_name}" rows="3" style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 3px;" readonly>{question['answer']}</textarea>
                ''')
            
            html_parts.append('</div>')
        
        html_parts.append('''
        </div>
        <div style="background: #e8f4f8; padding: 10px; border-radius: 4px; margin-top: 15px;">
            <strong>Note:</strong> Custom assessment answers are stored in the JSON field. 
            To edit responses programmatically, modify the custom_assessment_data field directly.
            This interface shows current responses for review purposes.
        </div>
        ''')
        
        return format_html(''.join(html_parts))
    
    custom_assessment_editor.short_description = 'Custom Questions'
    
    def completion_badge(self, obj):
        percentage = obj.completion_percentage
        if percentage == 100:
            color = 'green'
        elif percentage >= 75:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<span style="color: {};">{}%</span>',
            color, int(percentage)
        )
    completion_badge.short_description = 'Completion'
    
    def mark_ready_for_submission(self, request, queryset):
        count = queryset.update(ready_for_submission=True)
        self.message_user(request, f'{count} assessments marked as ready for submission.')
    mark_ready_for_submission.short_description = "Mark as ready for submission"
    
    def mark_submitted(self, request, queryset):
        count = 0
        for assessment in queryset:
            assessment.submitted_to_client = True
            assessment.submission_date = timezone.now()
            assessment.submitted_by = request.user
            assessment.save()
            count += 1
        self.message_user(request, f'{count} assessments marked as submitted.')
    mark_submitted.short_description = "Mark as submitted to client"
    
    def load_default_template(self, request, queryset):
        """Load default template for selected assessments"""
        default_template = AssessmentQuestionTemplate.objects.filter(is_active=True).first()
        if not default_template:
            self.message_user(request, 'No active assessment templates found. Please create one first.', level=messages.WARNING)
            return
        
        count = 0
        for assessment in queryset:
            if not assessment.assessment_template:
                assessment.assessment_template = default_template
                assessment.save()  # This will trigger load_template_questions
                count += 1
        
        if count > 0:
            self.message_user(request, f'Loaded "{default_template.name}" template for {count} assessments.')
        else:
            self.message_user(request, 'No assessments needed template loading (all already have templates).')
    load_default_template.short_description = "Load default assessment template"
    
    def save_model(self, request, obj, form, change):
        obj.assessed_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(AssessmentQuestionTemplate)
class AssessmentQuestionTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'description',
        'question_count',
        'is_active',
        'updated_at'
    ]
    
    list_filter = [
        'is_active',
        'created_at'
    ]
    
    search_fields = ['name', 'description']
    
    fieldsets = [
        ('Template Information', {
            'fields': [
                'name',
                'description',
                'is_active'
            ]
        }),
        ('Questions Configuration', {
            'fields': ['questions'],
            'classes': ['wide'],
            'description': 'JSON format: [{"question": "text", "type": "boolean/text", "required": true}]'
        }),
        ('Metadata', {
            'fields': [
                'created_at',
                'updated_at'
            ]
        })
    ]
    
    readonly_fields = ['created_at', 'updated_at']
    
    def question_count(self, obj):
        return len(obj.questions) if obj.questions else 0
    question_count.short_description = 'Questions'


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
# ADMIN SITE CONFIGURATION
# ═════════════════════════════════════════════════════════════════════════════

admin.site.site_header = "C4 Defence Administration - Complete Costing Management"
admin.site.site_title = "C4D Complete Admin"
admin.site.index_title = "C4D Administration Portal - Applications, Advanced Costing & Risk Assessment"

admin.site.enable_nav_sidebar = True