from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Message(models.Model):
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    recipient = models.ForeignKey(User, related_name='received_messages', on_delete=models.CASCADE)
    
    # Optional relationships
    application = models.ForeignKey(
        'jobs.JobApplication', 
        related_name='messages', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    job = models.ForeignKey(
        'jobs.Job', 
        related_name='messages', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['timestamp']
        
    def __str__(self):
        return f"Message from {self.sender} to {self.recipient} - {self.timestamp}"
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.save()


class Conversation(models.Model):
    """Track conversations between users"""
    participants = models.ManyToManyField(User, related_name='conversations')
    job = models.ForeignKey(
        'jobs.Job', 
        related_name='conversations', 
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    application = models.ForeignKey(
        'jobs.JobApplication',
        related_name='conversations',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        participants_str = ", ".join([p.email for p in self.participants.all()])
        return f"Conversation between {participants_str}"
    
    def get_messages(self):
        return Message.objects.filter(
            sender__in=self.participants.all(),
            recipient__in=self.participants.all()
        ).order_by('timestamp')
    
    def get_last_message(self):
        return self.get_messages().last()
    
    def get_unread_count_for_user(self, user):
        return Message.objects.filter(
            recipient=user,
            sender__in=self.participants.all(),
            is_read=False
        ).count()