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


# New
class NewUserForm(UserCreationForm):
    first_name=forms.CharField(required=True, widget=forms.TextInput(attrs={
            "class":"form-control",
            "name":"firstname",
            "placeholder":"Enter the firstname",
        }))

    last_name=forms.CharField(required=True, widget=forms.TextInput(attrs={
            "class":"form-control",
            "name":"lastname",
            "placeholder":"Enter the lastname",
        }))

    email=forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        "class":"form-control",
        "name":"email",
        "placeholder":"Enter your email ID",
    }))
    
    username=forms.CharField(required=True, widget=forms.TextInput(attrs={
        "class":"form-control",
        "name":"username",
        "placeholder":"Enter the username",
    }))

    password1=forms.CharField(required=True, widget=forms.PasswordInput(attrs={
        "class":"form-control",
        "name":"password1",
        "placeholder":"Create password",
    }))

    password2=forms.CharField(required=True, widget=forms.PasswordInput(attrs={
        "class":"form-control",
        "name":"password2",
        "placeholder":"Confirm Password",
    }))

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

