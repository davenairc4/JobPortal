from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from .models import RFQTS, Job, Position, Advertisement, JobApplication
from .forms import RFQTSForm, JobForm, PositionForm, AdvertisementForm, JobApplicationForm


def home(request):
    featured_ads = Advertisement.objects.filter(status='Published', is_featured=True)[:5]
    recent_jobs = Job.objects.filter(is_active=True)[:10]
    return render(request, 'jobs/home.html', {'featured_ads': featured_ads, 'recent_jobs': recent_jobs})


def job_list(request):
    jobs = Job.objects.filter(is_active=True)
    return render(request, 'jobs/job_list.html', {'jobs': jobs})


def job_detail(request, job_id):
    job = get_object_or_404(Job, id=job_id, is_active=True)
    if job.advertisement and job.advertisement.status == 'Published':
        # Increment the view count
        job.advertisement.view_count += 1
        job.advertisement.save()
    
    # Check if user has applied
    has_applied = False
    if request.user.is_authenticated:
        has_applied = JobApplication.objects.filter(job=job, user=request.user).exists()
    
    return render(request, 'jobs/job_detail.html', {'job': job, 'has_applied': has_applied})


@login_required
def create_rfqts(request):
    if not request.user.is_employer and not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to create RFQTS.")
        
    if request.method == 'POST':
        form = RFQTSForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'RFQTS created successfully!')
            return redirect('rfqts_list')
    else:
        form = RFQTSForm()
    
    return render(request, 'jobs/rfqts_form.html', {'form': form})


@login_required
def rfqts_list(request):
    rfqts_list = RFQTS.objects.all().order_by('-created_at')
    return render(request, 'jobs/rfqts_list.html', {'rfqts_list': rfqts_list})


@login_required
def rfqts_detail(request, rfqts_id):
    rfqts = get_object_or_404(RFQTS, id=rfqts_id)
    return render(request, 'jobs/rfqts_detail.html', {'rfqts': rfqts})


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
            }
        form = JobForm(initial=initial_data)
    
    return render(request, 'jobs/job_form.html', {'form': form, 'rfqts': rfqts})


@login_required
def manage_positions(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    # Check permissions
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
    
    positions = Position.objects.filter(job=job)
    return render(request, 'jobs/manage_positions.html', {
        'form': form,
        'job': job,
        'positions': positions
    })


@login_required
def create_advertisement(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    # Check permissions
    if job.created_by != request.user and not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to create an advertisement for this job.")
    
    # Check if advertisement already exists
    try:
        ad = Advertisement.objects.get(job=job)
        return redirect('edit_advertisement', ad_id=ad.id)
    except Advertisement.DoesNotExist:
        pass
    
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
    
    return render(request, 'jobs/advertisement_form.html', {'form': form, 'job': job})


@login_required
def edit_advertisement(request, ad_id):
    ad = get_object_or_404(Advertisement, id=ad_id)
    
    # Check permissions
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
    
    return render(request, 'jobs/advertisement_form.html', {'form': form, 'job': ad.job, 'ad': ad})


@login_required
def apply_for_job(request, job_id):
    if not request.user.is_job_seeker:
        return HttpResponseForbidden("Only job seekers can apply for jobs.")
    
    job = get_object_or_404(Job, id=job_id, is_active=True)
    
    # Check if user has already applied
    if JobApplication.objects.filter(job=job, user=request.user).exists():
        messages.warning(request, 'You have already applied for this job.')
        return redirect('job_detail', job_id=job.id)
    
    if request.method == 'POST':
        form = JobApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save(commit=False)
            application.user = request.user
            application.job = job
            application.save()
            messages.success(request, 'Your job application has been submitted successfully!')
            return redirect('my_applications')
    else:
        # Pre-fill form with user profile data if available
        initial = {}
        try:
            profile = request.user.profile
            initial = {
                'full_name': f"{profile.first_name} {profile.last_name}",
                'resume': profile.resume
            }
        except:
            pass
        form = JobApplicationForm(initial=initial)
    
    return render(request, 'jobs/job_application_form.html', {'form': form, 'job': job})


@login_required
def my_applications(request):
    applications = JobApplication.objects.filter(user=request.user).order_by('-submission_date')
    return render(request, 'jobs/my_applications.html', {'applications': applications})


@login_required
def view_applications(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    # Check permissions
    if job.created_by != request.user and not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to view applications for this job.")
    
    applications = JobApplication.objects.filter(job=job).order_by('-submission_date')
    return render(request, 'jobs/view_applications.html', {'job': job, 'applications': applications})


@login_required
def application_detail(request, application_id):
    application = get_object_or_404(JobApplication, id=application_id)
    
    # Check permissions
    if application.user != request.user and application.job.created_by != request.user and not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to view this application.")
    
    return render(request, 'jobs/application_detail.html', {'application': application})


@login_required
def update_application_status(request, application_id, status):
    application = get_object_or_404(JobApplication, id=application_id)
    
    # Check permissions
    if application.job.created_by != request.user and not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to update this application's status.")
    
    if status in [s[0] for s in JobApplication.APPLICATION_STATUS]:
        application.status = status
        application.save()
        messages.success(request, f'Application status updated to {status}.')
    else:
        messages.error(request, 'Invalid status provided.')
    
    return redirect('application_detail', application_id=application.id)