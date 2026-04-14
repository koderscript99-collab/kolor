from django.db import models

# Create your models here.
class detail (models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    level= models.CharField()
    description=models.TextField()

    def __str__(self):
        return self.name
    
class course (models.Model):
    course_choices=[
        ('', 'course'),
        ( 'science', 'Science'),
        ('act',"Act"),
    ]