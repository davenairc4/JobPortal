from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from .models import Message
from .forms import MessageForm
from jobs.models import JobApplication, Job


@login_required
def message_list(request):
    received_messages = Message.objects.filter(recipient=request.user).order_by('-timestamp')
    sent_messages = Message.objects.filter(sender=request.user).order_by('-timestamp')
    return render(request, 'messaging/message_list.html', {
        'received_messages': received_messages,
        'sent_messages': sent_messages
    })


@login_required
def message_detail(request, message_id):
    message = get_object_or_404(Message, id=message_id)
    
    # Check permissions
    if message.recipient != request.user and message.sender != request.user:
        return HttpResponseForbidden("You don't have permission to view this message.")
    
    # Mark as read if recipient is viewing
    if message.recipient == request.user and not message.is_read:
        message.is_read = True
        message.save()
    
    return render(request, 'messaging/message_detail.html', {'message': message})


@login_required
def send_message(request, recipient_id, job_id=None, application_id=None):
    from users.models import CustomUser
    recipient = get_object_or_404(CustomUser, id=recipient_id)
    job = None
    application = None
    
    if job_id:
        job = get_object_or_404(Job, id=job_id)
    
    if application_id:
        application = get_object_or_404(JobApplication, id=application_id)
        job = application.job
        
        # Check permissions for application messages
        if application.user != request.user and application.job.created_by != request.user:
            return HttpResponseForbidden("You don't have permission to send messages for this application.")
    
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user
            message.recipient = recipient
            message.job = job
            message.application = application
            message.save()
            messages.success(request, 'Message sent successfully!')
            
            if application:
                return redirect('application_detail', application_id=application.id)
            return redirect('message_list')
    else:
        form = MessageForm()
    
    context = {
        'form': form,
        'recipient': recipient,
        'job': job,
        'application': application
    }
    return render(request, 'messaging/message_form.html', context)


@login_required
def reply_message(request, message_id):
    original_message = get_object_or_404(Message, id=message_id)
    
    # Check permissions
    if original_message.recipient != request.user and original_message.sender != request.user:
        return HttpResponseForbidden("You don't have permission to reply to this message.")
    
    # Set recipient to the other party
    recipient = original_message.sender if original_message.recipient == request.user else original_message.recipient
    
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user
            message.recipient = recipient
            message.job = original_message.job
            message.application = original_message.application
            message.save()
            messages.success(request, 'Reply sent successfully!')
            return redirect('message_detail', message_id=message.id)
    else:
        form = MessageForm()
    
    context = {
        'form': form,
        'original_message': original_message,
        'recipient': recipient
    }
    return render(request, 'messaging/reply_form.html', context)