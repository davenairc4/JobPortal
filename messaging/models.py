from django.db import models
from users.models import CustomUser
from jobs.models import Job, JobApplication


class Message(models.Model):
    """
    Messages between users about job applications
    """
    sender = models.ForeignKey(CustomUser, related_name='sent_messages', on_delete=models.CASCADE)
    recipient = models.ForeignKey(CustomUser, related_name='received_messages', on_delete=models.CASCADE)
    job = models.ForeignKey(Job, related_name='messages', on_delete=models.CASCADE, null=True, blank=True)
    application = models.ForeignKey(JobApplication, related_name='messages', on_delete=models.CASCADE, null=True, blank=True)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Message from {self.sender} to {self.recipient} for job {self.job.title if self.job else 'General'}"