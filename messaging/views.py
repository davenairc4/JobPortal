# messaging/views.py
from django.contrib import messages as flash
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from users.models import CustomUser
from jobs.models import Job, JobApplication
from .models import Message
from .forms import MessageForm


@login_required
def send_message(request, recipient_id, job_id=None, application_id=None):
    recipient = get_object_or_404(CustomUser, id=recipient_id)
    job = get_object_or_404(Job, id=job_id) if job_id else None
    application = get_object_or_404(JobApplication, id=application_id) if application_id else None
    if application:
        job = application.job
        if application.user != request.user and application.job.created_by != request.user:
            return HttpResponseForbidden("No permission to message on that application.")

    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            m = form.save(commit=False)
            m.sender = request.user
            m.recipient = recipient
            m.job = job
            m.application = application
            m.save()
            flash.success(request, "Message sent successfully.")
            if application:
                return redirect("application_detail", application.id)
            if job:
                return redirect("job_detail", job.id)
            return redirect("message_list")
    else:
        form = MessageForm()

    return render(request, "messaging/message_form.html",
                  {"form": form, "recipient": recipient, "job": job, "application": application})


@login_required
def message_list(request):
    received = Message.objects.filter(recipient=request.user).select_related("sender").order_by("-timestamp")
    sent     = Message.objects.filter(sender=request.user).select_related("recipient").order_by("-timestamp")
    return render(request, "messaging/message_list.html",
                  {"received_messages": received, "sent_messages": sent})


@login_required
def message_detail(request, message_id):
    anchor = get_object_or_404(Message, id=message_id)
    if request.user not in (anchor.sender, anchor.recipient):
        return HttpResponseForbidden()

    convo = Message.objects.filter(
        Q(sender=request.user, recipient=anchor.sender) |
        Q(sender=anchor.sender, recipient=request.user),
        job=anchor.job, application=anchor.application
    ).order_by("timestamp")
    convo.filter(recipient=request.user, is_read=False).update(is_read=True)

    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            m = form.save(commit=False)
            m.sender = request.user
            m.recipient = anchor.sender if anchor.sender != request.user else anchor.recipient
            m.job = anchor.job
            m.application = anchor.application
            m.save()
            return redirect("message_detail", m.id)
    else:
        form = MessageForm()

    return render(request, "messaging/message_detail.html",
                  {"conversation": convo, "form": form})


@login_required
@require_POST
def delete_message(request, message_id):
    m = get_object_or_404(Message, id=message_id)
    if request.user not in (m.sender, m.recipient):
        return HttpResponseForbidden()
    m.delete()
    flash.success(request, "Message deleted.")
    return redirect("message_list")

@login_required
def fetch_job_messages(request, job_id):
    """Return messages sent **after** a given message id for this job."""
    if request.headers.get('x-requested-with') != 'XMLHttpRequest':
        return HttpResponseForbidden()

    last_id = request.GET.get('after')
    try:
        last_id_int = int(last_id)
    except (TypeError, ValueError):
        last_id_int = 0


    qs = Message.objects.filter(job_id=job_id).order_by('timestamp')
    if last_id:
        qs = qs.filter(id__gt=last_id_int)

    messages_payload = []
    for m in qs:
        if request.user not in (m.sender, m.recipient):
            continue
        messages_payload.append({
            "id": m.id,
            "sender_is_me": m.sender_id == request.user.id,
            "sender_name": m.sender.get_full_name() or m.sender.email,
            "timestamp": m.timestamp.strftime("%d %b %Y %H:%M"),
            "content": m.content.replace('\n', '<br>'),
        })

    return JsonResponse({ "messages": messages_payload })