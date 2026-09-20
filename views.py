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


def loginUser(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("homeCRB")
    else:
        form = LoginForm()
    return render(request, 'CRB_app/login.html', {"form": form})


def logoutUser(request):
    logout(request)
    return redirect('loginUserCRB')

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

@never_cache
@login_required_no_next
def home(request):
    roomDetails = RoomDetails.objects.all().order_by("room_name")
    return render(request, "CRB_app/home.html", {"room_details": roomDetails})

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

# def removeRoom(request):
#     roomDetails=RoomDetails.object.all()
#     return render(request,'CRB_app/home.html',{'room_details':roomDetails})

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

def getSlotTimes(slot_idx, meridiem="AM"):
    base_minutes = 0 if meridiem == "AM" else 12 * 60
    total_start = base_minutes + (slot_idx * 30)
    total_end = total_start + 30

    start_t = time(total_start // 60, total_start % 60)
    if total_end == 1440:
        end_t = time(23, 59, 59)
    else:
        end_t = time(total_end // 60, total_end % 60)

    start_label = start_t.strftime("%I:%M").lstrip("0")
    end_label = "12:00" if total_end == 1440 else end_t.strftime("%I:%M").lstrip("0")

    return start_t, end_t, start_label, end_label


def roomBooking(request, room_id):
    room = get_object_or_404(RoomDetails, id=room_id)
    today_date = date.today().strftime('%Y-%m-%d')
    selected_date = request.GET.get('date', today_date)

    # Handle Form Submission
    if request.method == "POST":
        booking_date = request.POST.get('booking_date', selected_date)
        action_type = request.POST.get('action_type', 'book')
        slot_ids = request.POST.getlist('slots')  # Retrieves all selected slot IDs

        if slot_ids:
            # Sort IDs to find starting and ending slots
            slot_ids = sorted([int(sid) for sid in slot_ids])
            first_idx = slot_ids[0] - 1
            last_idx = slot_ids[-1] - 1

            # Convert slot indices to HH:MM format (0 = 00:00, 1 = 00:30, ...)
            start_hour = (first_idx * 30) // 60
            start_min = (first_idx * 30) % 60
            start_t = time(start_hour, start_min)

            end_minutes = (last_idx + 1) * 30
            if end_minutes >= 1440:
                end_t = time(23, 59, 59)
            else:
                end_t = time(end_minutes // 60, end_minutes % 60)

            is_maintenance = (action_type == 'maintenance')

            # Create the booking record
            BookingsDetails.objects.create(
                room_name=room.room_name,
                booked_by=request.user.username,
                date=booking_date,
                start_time=start_t,
                end_time=end_t,
                under_maintainance=is_maintenance
            )

            messages.success(request, f"Room {'marked for maintenance' if is_maintenance else 'booked'} successfully from {start_t.strftime('%I:%M %p').lstrip('0')} to {end_t.strftime('%I:%M %p').lstrip('0')}!")
            return redirect(f"/book-room/{room_id}/?date={booking_date}")

    # Fetch confirmed bookings for the day
    confirmed_bookings = BookingsDetails.objects.filter(
        room_name=room.room_name,
        date=selected_date
    )

    # 48 half-hour slots
    slots = []
    current_time = datetime.strptime("00:00", "%H:%M")
    end_limit = datetime.strptime("23:30", "%H:%M")
    slot_id = 1

    while True:
        next_time = current_time + timedelta(minutes=30)
        start_str = current_time.strftime("%H:%M")
        end_str = "24:00" if current_time.strftime("%H:%M") == "23:30" else next_time.strftime("%H:%M")

        start_display = current_time.strftime("%I:%M").lstrip("0")
        if start_display.startswith(":"):
            start_display = "12" + start_display
            
        time_label = f"{current_time.strftime('%I:%M %p').lstrip('0')} - {next_time.strftime('%I:%M %p').lstrip('0')}"

        slot_status = 'available'
        for b in confirmed_bookings:
            b_start = b.start_time.strftime("%H:%M")
            b_end = b.end_time.strftime("%H:%M")
            if start_str < b_end and end_str > b_start:
                slot_status = 'maintenance' if getattr(b, 'under_maintainance', False) else 'booked'
                break

        slots.append({
            'id': slot_id,
            'start': start_str,
            'end': end_str,
            'display_start': start_display,
            'label': time_label,
            'status': slot_status,
        })

        if current_time >= end_limit:
            break
        current_time = next_time
        slot_id += 1

    # 24 Hour headers
    hours = []
    h_time = datetime.strptime("00:00", "%H:%M")
    for _ in range(24):
        hours.append(h_time.strftime("%I %p").lstrip("0"))
        h_time += timedelta(hours=1)

    context = {
        'room': room,
        'slots': slots,
        'hours': hours,
        'selected_date': selected_date,
        'today_date': today_date,
    }
    return render(request, 'room_booking.html', context)

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