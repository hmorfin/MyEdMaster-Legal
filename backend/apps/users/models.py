from django.db import models

class UserProfile(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    dob = models.DateField(null=True, blank=True)
    location = models.JSONField(default=dict)
    user_attributes = models.JSONField(default=dict, blank=True)
    onboarded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
