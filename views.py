from datetime import datetime, date, timedelta, time
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.utils import timezone

from .decorators import login_required_no_next
from .models import RoomDetails, BookingsDetails
from .forms import LoginForm, NewUserForm

from django.http import JsonResponse

def addUser(request):
    if request.method=="POST":
        form=NewUserForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "User created successfully!")
            return redirect('adminPanelCRB')
    else:
        form=NewUserForm()
    return render(request,'CRB_app/addUser.html',{'form':form})


def removeRoom(request):
    if request.method == "POST":
        room_id = request.POST.get('room_id')
        
        if request.user.username == "Admin" or request.user.is_staff:
            room = get_object_or_404(RoomDetails, id=room_id)
            room_name = room.room_name
            room.delete()
            messages.success(request, f'"{room_name}" removed successfully!')
        else:
            messages.error(request, "Permission denied.")
            
        return redirect('homeCRB') #it has an issue, if i go back to the previos page it still shows the remover room in the list. which may cause error
        # return redirect('removeRoomCRB')

    roomDetails = RoomDetails.objects.all().order_by("room_name")
    return render(request, "CRB_app/removeRoom.html", {"room_details": roomDetails})


def adminPanel(request):
    #add authentication
    return render(request,'CRB_app/adminPanel.html')

def addRoom(request):
    if request.method == "POST":
        name = request.POST.get("room_name")
        capacity = request.POST.get("capacity")
        amenities = request.POST.getlist("amenities")
        image = request.FILES.get("room_image")

        if not name or not capacity or not image:
            messages.error(request,'Some inputs are missing')
            return redirect('addRoomCRB')
        try:
            RoomDetails.objects.create(
                room_name=name,
                capacity=int(capacity),
                amenities=", ".join(amenities),
                room_image=image
            )
            messages.success(request, f'Room "{name}" was added successfully!')
            return redirect('homeCRB')
        except Exception as e:
            messages.error(request, f'Failed to add room: {str(e)}')
            return redirect('addRoomCRB')
        
    return render(request, 'CRB_app/add_room.html')
    

def allBookings(request, filter="today"):
    today = timezone.localdate()

    # Read query parameters
    filter_type = request.GET.get('filter', filter)
    selected_date = request.GET.get('date', None)
    format_type = request.GET.get('format', '')

    data = BookingsDetails.objects.all()

    # 1. Apply Filtering
    if selected_date:
        data = data.filter(date=selected_date).order_by('start_time')
    elif filter_type == "past":
        data = data.filter(date__lt=today).order_by('-date', 'start_time')
    elif filter_type == "future":
        data = data.filter(date__gt=today).order_by('date', 'start_time')
    elif filter_type == "all":
        data = data.order_by('-date', 'start_time')
    else:  # default "today"
        data = data.filter(date=today).order_by('start_time')
        filter_type = "today"

    # 2. Check for Fetch / AJAX request
    is_ajax = (
        format_type == 'json' or 
        request.headers.get('x-requested-with') == 'XMLHttpRequest' or
        'application/json' in request.headers.get('Accept', '')
    )

    if is_ajax:
        bookings_list = []
        for b in data:
            # Handle room name whether it's a string, ForeignKey, or property
            if hasattr(b, 'room_name'):
                room_display = str(b.room_name)
            elif hasattr(b, 'room'):
                room_display = str(b.room)
            else:
                room_display = f"Room #{b.id}"

            # Format start and end times safely
            start_str = b.start_time.strftime('%I:%M %p') if getattr(b, 'start_time', None) else ''
            end_str = b.end_time.strftime('%I:%M %p') if getattr(b, 'end_time', None) else ''
            date_str = b.date.strftime('%A, %d %b %Y') if getattr(b, 'date', None) else ''
            
            # Format booked_on safely
            booked_on_val = getattr(b, 'booked_on', None)
            booked_on_str = booked_on_val.strftime('%d %b %Y, %I:%M %p') if booked_on_val else ''

            is_past = bool(b.date and b.date < today)

            bookings_list.append({
                'id': b.id,
                'room_name': room_display,
                'date': date_str,
                'start_time': start_str,
                'end_time': end_str,
                'booked_on': booked_on_str,
                'is_past': is_past,
            })
        return JsonResponse({'bookings': bookings_list})

    # 3. Standard initial server-side render
    context = {
        "data": data,
        "filter": filter_type,
        "today": today
    }
    return render(request, 'CRB_app/all_bookings.html', context)


def myBookings(request, filter='today'):
    today = timezone.localdate()
    data = BookingsDetails.objects.filter(booked_by=request.user.username)

    if filter == "past":
        data = data.filter(date__lt=today).order_by('date', 'start_time')
    elif filter == "future":
        data = data.filter(date__gt=today).order_by('date', 'start_time')
    else:
        data = data.filter(date=today).order_by('start_time')
        filter = "today"

    context = {
        "data": data,
        "filter": filter
    }
    return render(request, "CRB_app/my_bookings.html", context)


@login_required_no_next
def cancelBooking(request):
    if request.method == "POST":
        booking_id = request.POST.get("booking_id")
        
        # In admin panel you might want to allow canceling any booking;
        # if this is for users, keep booked_by check:
        booking = get_object_or_404(
            BookingsDetails, 
            id=booking_id
        )
        
        booking.delete()

        # Check if the request was sent by fetch/JS
        is_ajax = (
            request.headers.get('x-requested-with') == 'XMLHttpRequest' or
            request.POST.get('format') == 'json'
        )

        if is_ajax:
            return JsonResponse({'status': 'success', 'booking_id': booking_id})

        messages.success(request, "Booking cancelled successfully.")
        return redirect(request.META.get('HTTP_REFERER', 'my_bookings_default'))

    return redirect('allBookingsCRB')
