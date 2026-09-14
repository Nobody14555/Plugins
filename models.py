from django.db import models
from django.contrib.auth.models import AbstractBaseUser
from django.core.validators import RegexValidator
from django.core.validators import MinValueValidator

class RoomDetails(models.Model):
    room_name=models.CharField(max_length=30, null=False, unique=True)
    capacity=models.IntegerField(validators=[MinValueValidator(1)], null=False)
    amenities=models.CharField(max_length=50, null=False)
    room_image=models.ImageField(upload_to='room-images/')
    under_maintanance=models.BooleanField(default=False)
    created_on = models.DateTimeField(auto_now_add=True)
    is_hidden = models.BooleanField(default=False)
    
    def __str__(self):
        return self.room_name
    
class BookingsDetails(models.Model):
    room_name=models.CharField(max_length=30, null=False)
    date=models.DateField(null=False)
    start_time=models.TimeField(null=False)
    end_time=models.TimeField(null=False)
    booked_by=models.CharField(max_length=50, null=False)
    booked_on=models.DateTimeField(auto_now_add=True)
    under_maintainance = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.room_name} | {self.date} ({self.start_time} - {self.end_time})"


# from .validators import validate_room_image
# Create your models here.
# class User(AbstractBaseUser):
#     department=models.CharField(max_length=30, null=False)
