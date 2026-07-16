# from django.contrib.auth.models import User
# from django.db import models

# class UserProfile(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)

#     # 👇 Add your custom columns here
#     phone = models.CharField(max_length=15, null=True, blank=True)
#     address = models.TextField(null=True, blank=True)
#     dob = models.DateField(null=True, blank=True)
#     profile_picture = models.ImageField(null=True, blank=True)
#     is_verified = models.BooleanField(default=False)
#     age = models.IntegerField(null=True, blank=True)
