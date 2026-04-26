
from django.db import models
from django.contrib.auth.models import User

class Detail(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    level = models.CharField(max_length=50)

    pics = models.ImageField(upload_to='images/', null=True, blank=True)
    active = models.BooleanField(help_text="are you active?")
    def __str__(self):
        return self.name    