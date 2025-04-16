from django.contrib.auth.models import AbstractUser
from django.db import models

def user_profile_path(instance, filename):
    return f'profiles/user_{instance.id}/{filename}'

class CustomUser(AbstractUser):
    profile_picture = models.ImageField(upload_to=user_profile_path, blank=True, null=True)
    pass


class SocialToken(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    provider = models.CharField(max_length=50)  # e.g., 'facebook'
    access_token = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
