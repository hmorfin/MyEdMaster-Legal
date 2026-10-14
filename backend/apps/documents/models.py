from django.db import models
from apps.users.models import UserProfile

class UserDocument(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='documents')
    message = models.ForeignKey('chat.Message', on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    file_name = models.CharField(max_length=255)
    storage_path = models.CharField(max_length=512) # Path inside the S3 bucket
    file_size = models.IntegerField() # In bytes
    upload_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20, 
        default='uploaded', 
        choices=[('uploaded', 'Uploaded'), ('processing', 'Processing'), ('indexed', 'Indexed')]
    )
    class Meta:
        ordering = ['-upload_date']
