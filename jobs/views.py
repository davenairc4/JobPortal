from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import models
from django.utils import timezone

from .models import RFQTS, Job, Position, Advertisement, JobApplication
from .forms import RFQTSForm, JobForm, PositionForm, AdvertisementForm, JobApplicationForm


def home(request):
    featured_ads = Advertisement.objects.filter(
        status='Published',
        is_featured=True,
        expire_date__gte=timezone.now()
    ).select_related('job')[:5]
    recent_jobs = Job.objects.filter(
        is_active=True,
        closing_date__gte=timezone.now().date()
    ).select_related('rfqts', 'created_by')[:10]
    return render(request, 'jobs/home.html', {
        'featured_ads': featured_ads,
        'recent_jobs': recent_jobs
    })


def job_list(request):
    jobs = Job.objects.filter(is_active=True).select_related('rfqts', 'created_by').order_by('-submission_date')
    query = request.GET.get('q')
    if query:
        jobs = jobs.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(skills_sets__icontains=query)
        )
    location = request.GET.get('location')
    if location:
        jobs = jobs.filter(location=location)
    job_type = request.GET.get('type')
    if job_type:
        jobs = jobs.filter(job_type=job_type)
    clearance = request.GET.get('clearance')
    if clearance:
        jobs = jobs.filter(clearance=clearance)
    paginator = Paginator(jobs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'jobs/job_list.html', {
        'page_obj': page_obj,
        'query': query,
        'location': location,
        'job_type': job_type,
        'clearance': clearance,
        'locations': Job.LOCATIONS,
        'job_types': Job.JOB_TYPES,
        'clearance_levels': Job.CLEARANCE_LEVEL_CHOICES,
    })


def job_detail(request, job_id):
    job = get_object_or_404(Job.objects.select_related('rfqts', 'created_by').prefetch_related('positions'), id=job_id, is_active=True)
    if hasattr(job, 'advertisement') and job.advertisement.status == 'Published':
        job.advertisement.view_count += 1
        job.advertisement.save()
    has_applied = False
    user_application = None
    if request.user.is_authenticated:
        try:
            user_application = JobApplication.objects.select_related('user', 'job').get(job=job, user=request.user)
            has_applied = True
        except JobApplication.DoesNotExist:
            pass
    related_jobs = Job.objects.filter(
        is_active=True,
        location=job.location
    ).exclude(id=job.id).select_related('rfqts', 'created_by')[:5]
    return render(request, 'jobs/job_detail.html', {
        'job': job,
        'has_applied': has_applied,
        'user_application': user_application,
        'related_jobs': related_jobs,
    })


@login_required
def create_rfqts(request):
    if not request.user.is_employer and not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to create RFQTS.")
    if request.method == 'POST':
        form = RFQTSForm(request.POST, request.FILES)
        if form.is_valid():
            rfqts = form.save()
            messages.success(request, 'RFQTS created successfully!')
            return redirect('rfqts_detail', rfqts_id=rfqts.id)
    else:
        form = RFQTSForm()
    return render(request, 'jobs/rfqts_form.html', {'form': form})


@login_required
def rfqts_list(request):
    if not request.user.is_employer and not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to view RFQTS.")
    rfqts_list = RFQTS.objects.select_related().order_by('-created_at')
    query = request.GET.get('q')
    if query:
        rfqts_list = rfqts_list.filter(
            Q(rfqts_no__icontains=query) |
            Q(task_title__icontains=query) |
            Q(department__icontains=query)
        )
    paginator = Paginator(rfqts_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'jobs/rfqts_list.html', {
        'page_obj': page_obj,
        'query': query,
    })


@login_required
def rfqts_detail(request, rfqts_id):
    if not request.user.is_employer and not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to view RFQTS.")
    rfqts = get_object_or_404(RFQTS, id=rfqts_id)
    jobs = rfqts.jobs.select_related('created_by', 'rfqts').prefetch_related('positions')
    return render(request, 'jobs/rfqts_detail.html', {
        'rfqts': rfqts,
        'jobs': jobs,
    })


@login_required
def create_job(request, rfqts_id=None):
    if not request.user.is_employer and not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to create jobs.")
    rfqts = None
    if rfqts_id:
        rfqts = get_object_or_404(RFQTS, id=rfqts_id)
    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.created_by = request.user
            if rfqts:
                job.rfqts = rfqts
            job.save()
            messages.success(request, 'Job created successfully!')
            return redirect('job_detail', job_id=job.id)
    else:
        initial_data = {}
        if rfqts:
            initial_data = {
                'title': rfqts.task_title,
                'description': rfqts.scope_of_task,
                'skills_sets': rfqts.skills_sets,
                'skills_levels': rfqts.skills_levels,
                'location': rfqts.location,
                'commencement_date': rfqts.commencement_date_for_task,
                'completion_date': rfqts.completion_date_for_task,
                'closing_date': rfqts.closing_date_for_quotation,
                'clearance': rfqts.security_clearances_required_for_personnel,
            }
        form = JobForm(initial=initial_data)
    return render(request, 'jobs/job_form.html', {
        'form': form,
        'rfqts': rfqts
    })


@login_required
def edit_job(request, job_id):
    job = get_object_or_404(Job.objects.select_related('created_by', 'rfqts'), id=job_id)
    if job.created_by != request.user and not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to edit this job.")
    if request.method == 'POST':
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, 'Job updated successfully!')
            return redirect('job_detail', job_id=job.id)
    else:
        form = JobForm(instance=job)
    return render(request, 'jobs/job_form.html', {
        'form': form,
        'job': job
    })


@login_required
def manage_positions(request, job_id):
    job = get_object_or_404(Job.objects.select_related('created_by', 'rfqts'), id=job_id)
    if job.created_by != request.user and not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to manage positions for this job.")
    if request.method == 'POST':
        form = PositionForm(request.POST)
        if form.is_valid():
            position = form.save(commit=False)
            position.job = job
            position.save()
            messages.success(request, 'Position added successfully!')
            return redirect('manage_positions', job_id=job.id)
    else:
        form = PositionForm()
    positions = Position.objects.filter(job=job).select_related('job')
    return render(request, 'jobs/manage_positions.html', {
        'form': form,
        'job': job,
        'positions': positions
    })


@login_required
def create_advertisement(request, job_id):
    job = get_object_or_404(Job.objects.select_related('created_by', 'rfqts'), id=job_id)
    if job.created_by != request.user and not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to create an advertisement for this job.")
    if hasattr(job, 'advertisement'):
        return redirect('edit_advertisement', ad_id=job.advertisement.id)
    if request.method == 'POST':
        form = AdvertisementForm(request.POST)
        if form.is_valid():
            ad = form.save(commit=False)
            ad.job = job
            ad.save()
            messages.success(request, 'Advertisement created successfully!')
            return redirect('job_detail', job_id=job.id)
    else:
        form = AdvertisementForm()
    return render(request, 'jobs/advertisement_form.html', {
        'form': form,
        'job': job
    })


@login_required
def edit_advertisement(request, ad_id):
    ad = get_object_or_404(Advertisement.objects.select_related('job__created_by', 'job__rfqts'), id=ad_id)
    if ad.job.created_by != request.user and not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to edit this advertisement.")
    if request.method == 'POST':
        form = AdvertisementForm(request.POST, instance=ad)
        if form.is_valid():
            form.save()
            messages.success(request, 'Advertisement updated successfully!')
            return redirect('job_detail', job_id=ad.job.id)
    else:
        form = AdvertisementForm(instance=ad)
    return render(request, 'jobs/advertisement_form.html', {
        'form': form,
        'job': ad.job,
        'ad': ad
    })


@login_required
def apply_for_job(request, job_id):
    if not request.user.is_job_seeker:
        return HttpResponseForbidden("Only job seekers can apply for jobs.")
    
    job = get_object_or_404(Job.objects.select_related('created_by', 'rfqts'), id=job_id, is_active=True)
    
    # Check if closing date has passed
    if job.closing_date and job.closing_date < timezone.now().date():
        messages.error(request, 'The application deadline for this job has passed.')
        return redirect('job_detail', job_id=job.id)
    
    # Check if user has already applied
    if JobApplication.objects.filter(job=job, user=request.user).exists():
        messages.warning(request, 'You have already applied for this job.')
        return redirect('job_detail', job_id=job.id)
    
    # Get messages for this job - handle if Message model doesn't exist
    job_messages = []
    try:
        from messaging.models import Message
        # Get messages between the user and job creator about this job
        job_messages = Message.objects.filter(
            Q(sender=request.user, recipient=job.created_by) |
            Q(sender=job.created_by, recipient=request.user)
        ).select_related('sender', 'recipient').order_by('timestamp')
        
        # If Message model has a job field, filter by it
        if hasattr(Message, 'job'):
            job_messages = job_messages.filter(job=job)
    except ImportError:
        pass
    except Exception as e:
        print(f"Error loading messages: {e}")
    
    if request.method == 'POST':
        # Handle message sending
        if 'send_message' in request.POST:
            message_content = request.POST.get('message_content', '').strip()
            if message_content:
                try:
                    from messaging.models import Message
                    message_data = {
                        'sender': request.user,
                        'recipient': job.created_by,
                        'content': message_content
                    }
                    
                    # Add job field if it exists
                    if hasattr(Message, 'job'):
                        message_data['job'] = job
                    
                    message = Message.objects.create(**message_data)
                    
                    # If it's an AJAX request, return JSON response
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': True,
                            'sender_name': request.user.get_full_name() or request.user.email,
                            'timestamp': message.timestamp.strftime("%b %d, %Y %H:%M"),
                            'content': message.content
                        })
                    else:
                        messages.success(request, 'Message sent successfully.')
                        return redirect('apply_for_job', job_id=job.id)
                except Exception as e:
                    error_msg = f'Error sending message: {str(e)}'
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'error': error_msg})
                    else:
                        messages.error(request, error_msg)
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'Message cannot be empty.'})
        
        # Handle application submission
        elif 'submit_application' in request.POST:
            form = JobApplicationForm(request.POST, request.FILES)
            if form.is_valid():
                application = form.save(commit=False)
                application.user = request.user
                application.job = job
                application.save()
                
                # Send confirmation email (implement email functionality)
                messages.success(request, 
                    'Your job application has been submitted successfully! ' +
                    'You will receive a confirmation email shortly.')
                return redirect('my_applications')
            else:
                # Add specific error messages for debugging
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
        else:
            form = JobApplicationForm(request.POST, request.FILES)
    else:
        # Pre-fill form with user profile data if available
        initial = {
            'signature_date': timezone.now().date(),
        }
        
        # Try to get user profile data
        if hasattr(request.user, 'profile'):
            profile = request.user.profile
            initial.update({
                'full_name': f"{profile.first_name} {profile.last_name}",
                'current_clearance': getattr(profile, 'clearance_level', ''),
                'location_of_residence': getattr(profile, 'location', ''),
            })
        
        form = JobApplicationForm(initial=initial)
    
    return render(request, 'jobs/job_application_form.html', {
        'form': form, 
        'job': job,
        'job_messages': job_messages
    })

@login_required
def my_applications(request):
    if not request.user.is_job_seeker:
        return HttpResponseForbidden("Only job seekers can view applications.")

    # all applications for counters
    all_apps = JobApplication.objects.filter(
        user=request.user
    ).select_related('job__created_by', 'job__rfqts')

    # status filter for the list itself
    status = request.GET.get('status')
    applications = all_apps
    if status:
        applications = applications.filter(status=status)

    paginator = Paginator(applications.order_by('-submission_date'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'jobs/my_applications.html', {
        'page_obj': page_obj,
        'status_choices': JobApplication.APPLICATION_STATUS,
        'current_status': status,
        'pending_count': all_apps.filter(status='Pending').count(),
        'accepted_count': all_apps.filter(status='Accepted').count(),
        'rejected_count': all_apps.filter(status='Rejected').count(),
    })


@login_required
def view_applications(request, job_id):
    job = get_object_or_404(Job.objects.select_related('created_by', 'rfqts'), id=job_id)
    
    if job.created_by != request.user and not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to view applications for this job.")
    
    applications = JobApplication.objects.filter(job=job).select_related('user', 'job')
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        applications = applications.filter(status=status)
    
    # Search by applicant name
    search = request.GET.get('search')
    if search:
        applications = applications.filter(
            Q(full_name__icontains=search) |
            Q(user__email__icontains=search)
        )
    
    applications = applications.order_by('-submission_date')
    
    paginator = Paginator(applications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get application statistics
    stats = {
        'total': applications.count(),
        'pending': applications.filter(status='Pending').count(),
        'reviewing': applications.filter(status='Reviewing').count(),
        'interviewed': applications.filter(status='Interviewed').count(),
        'accepted': applications.filter(status='Accepted').count(),
        'rejected': applications.filter(status='Rejected').count(),
    }
    
    return render(request, 'jobs/view_applications.html', {
        'job': job, 
        'page_obj': page_obj,
        'stats': stats,
        'status_choices': JobApplication.APPLICATION_STATUS,
        'current_status': status,
        'search_query': search,
    })


@login_required
def application_detail(request, application_id):
    application = get_object_or_404(JobApplication.objects.select_related('user', 'job__created_by', 'job__rfqts'), id=application_id)
    
    # Check permissions
    is_applicant = application.user == request.user
    is_employer = application.job.created_by == request.user
    is_staff = request.user.is_staff
    
    if not (is_applicant or is_employer or is_staff):
        return HttpResponseForbidden("You don't have permission to view this application.")
    
    # Check for conflicts that require waiver
    requires_waiver = any([
        application.currently_aps,
        application.aps_within_12_months,
        application.currently_sercat,
        application.sercat_within_12_months
    ])
    
    context = {
        'application': application,
        'is_applicant': is_applicant,
        'is_employer': is_employer,
        'requires_waiver': requires_waiver,
    }
    
    return render(request, 'jobs/application_detail.html', context)


@login_required
def update_application_status(request, application_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    application = get_object_or_404(JobApplication.objects.select_related('job__created_by'), id=application_id)
    
    # Check permissions
    if application.job.created_by != request.user and not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    new_status = request.POST.get('status')
    if new_status not in [s[0] for s in JobApplication.APPLICATION_STATUS]:
        return JsonResponse({'error': 'Invalid status'}, status=400)
    
    old_status = application.status
    application.status = new_status
    application.save()
    
    # Log status change (implement logging if needed)
    
    # Send notification to applicant (implement email functionality)
    
    messages.success(request, f'Application status updated from {old_status} to {new_status}.')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'new_status': new_status})
    
    return redirect('application_detail', application_id=application.id)


@login_required
def download_application(request, application_id):
    """Export application as PDF or Word document"""
    application = get_object_or_404(JobApplication.objects.select_related('user', 'job__created_by'), id=application_id)
    
    # Check permissions
    if (application.job.created_by != request.user and 
        application.user != request.user and 
        not request.user.is_staff):
        return HttpResponseForbidden("You don't have permission to download this application.")
    
    # Implement PDF/Word generation here
    # For now, redirect to detail page
    messages.info(request, 'Document export feature coming soon.')
    return redirect('application_detail', application_id=application_id)


@login_required
def employer_dashboard(request):
    """Dashboard for employers to manage jobs and applications"""
    if not request.user.is_employer and not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to access the employer dashboard.")
    
    # Get employer's jobs
    jobs = Job.objects.filter(created_by=request.user).select_related('rfqts').prefetch_related('jobapplication_set').order_by('-submission_date')
    
    # Get recent applications
    recent_applications = JobApplication.objects.filter(
        job__created_by=request.user
    ).select_related('job', 'user').order_by('-submission_date')[:10]
    
    # Get statistics
    total_jobs = jobs.count()
    active_jobs = jobs.filter(is_active=True).count()
    total_applications = JobApplication.objects.filter(job__created_by=request.user).count()
    pending_applications = JobApplication.objects.filter(
        job__created_by=request.user,
        status='Pending'
    ).count()
    
    context = {
        'jobs': jobs[:10],  # Latest 10 jobs
        'recent_applications': recent_applications,
        'stats': {
            'total_jobs': total_jobs,
            'active_jobs': active_jobs,
            'total_applications': total_applications,
            'pending_applications': pending_applications,
        }
    }
    
    return render(request, 'jobs/employer_dashboard.html', context)