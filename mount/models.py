from django.db import models

# Create your models here.
class detail (models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    level= models.CharField()
    pics = models.ImageField(upload_to='images/', null=True, blank=True)
    active=models.BooleanField( help_text="are you active?")

    def __str__(self):
        return self.name
    
