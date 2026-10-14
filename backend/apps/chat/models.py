from django.db import models

class TopicMastery(models.Model):
    user = models.ForeignKey('users.UserProfile', on_delete=models.CASCADE)
    topic = models.CharField(max_length=100)
    mastery_level = models.FloatField(default=0.0)

    class Meta:
        unique_together = ('user', 'topic')

class Conversation(models.Model):
    user = models.ForeignKey('users.UserProfile', on_delete=models.CASCADE)

    FAMILIARITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    SELF_ASSESSMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('skipped', 'Skipped'),
    ]
        
    # User Inputs
    legal_situation = models.TextField(null=True, blank=True)
    prior_experience = models.TextField(null=True, blank=True)
    desired_outcome = models.TextField(null=True, blank=True)
    jurisdiction = models.CharField(max_length=100, null=True, blank=True)


    # LLM Populated
    chat_name = models.CharField(max_length=255)
    primary_topic = models.CharField(max_length=100, null=True, blank=True)
    legal_domain = models.CharField(max_length=100, null=True, blank=True)
    branch = models.CharField(max_length=100, null=True, blank=True)
    baseline_familiarity = models.CharField(max_length=10,choices=FAMILIARITY_CHOICES,null=True,blank=True)
    primary_intent = models.CharField(max_length=100, null=True, blank=True)
    self_assessment_status = models.CharField(max_length=20,choices=SELF_ASSESSMENT_STATUS_CHOICES,default='pending')
    example_text = models.TextField(null=True, blank=True)
    empty_template = models.JSONField(null=True, blank=True)
    conversation_summary = models.TextField(null=True, blank=True)
    last_summarized_message_id = models.CharField(max_length=100, null=True, blank=True)
    kb_content = models.JSONField(null=True, blank=True)
    fspr_profile = models.JSONField(null=True, blank=True)
    fspr_update_in_progress = models.BooleanField(default=False)
    document_context = models.JSONField(null=True, blank=True)

    MODE_CHOICES = [
        ('chat', 'Chat'),
        ('document', 'Document'),
    ]
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='chat')

    # Audit Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Message(models.Model):
    ROLE_CHOICES = [('user', 'User'), ('llm', 'LLM')]
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    document_paths = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class GeneratedDocument(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='documents')
    user = models.ForeignKey('users.UserProfile', on_delete=models.CASCADE)
    document_type = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    content_markdown = models.TextField()
    storage_path = models.CharField(max_length=500, null=True, blank=True)
    version = models.IntegerField(default=1)
    context_summary = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)