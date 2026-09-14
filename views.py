from django.shortcuts import render,redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache

from .decorators import login_required_no_next

from .models import *
from .forms import *
# Create your views here.
import datetime
from django.contrib import messages

from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import RoomDetails, BookingsDetails


def loginUser(request):
    if request.method=="POST":
        form=LoginForm(request,data=request.POST)

        if form.is_valid():
            user=form.get_user()
            login(request,user)
            return redirect("homeCRB")
    else:
        form=LoginForm()
    return render(request, 'CRB_app/login.html',{"form":form})

def logoutUser(request):
    logout(request)
    return redirect('loginUserCRB')

@never_cache
@login_required_no_next
def home(request):
    roomDetails=RoomDetails.objects.all()
    return render(request, "CRB_app/home.html",{"room_details":roomDetails})

def adminPanel(request):
    if request.method=="POST":
        room_name=request.POST.get("room_name")
        capacity=request.POST.get("capacity")
        amenities=request.POST.getlist("amenities")
        amenities=", ".join(amenities)
        room_image=request.FILES.get("room_image")

        RoomDetails.objects.create(room_name=room_name, capacity=capacity, amenities=amenities, room_image=room_image)
        return redirect('adminpanelCRB')

    return render(request, 'CRB_app/add_room.html')

# def roomBooking(request):
#     return render(request, "room_booking.html")

def getSlotTimes(slot_idx, meridiem="AM"):
    """
    Maps slot indices (0 to 23) to 30-minute time intervals.
    0 = 12:00-12:30, 1 = 12:30-1:00, ..., 23 = 11:30-12:00
    """
    base_minutes = 0 if meridiem == "AM" else 12 * 60
    total_start = base_minutes + (slot_idx * 30)
    total_end = total_start + 30

    start_t = datetime.time(total_start // 60, total_start % 60)
    if total_end == 1440:
        end_t = datetime.time(23, 59, 59)
    else:
        end_t = datetime.time(total_end // 60, total_end % 60)

    start_label = start_t.strftime("%I:%M").lstrip("0")
    end_label = "12:00" if total_end == 1440 else end_t.strftime("%I:%M").lstrip("0")

    return start_t, end_t, start_label, end_label


def roomBooking(request, room_id):
    room = get_object_or_404(RoomDetails, id=room_id, is_hidden=False)

    # 1. Date and AM/PM parameters
    today_str = datetime.date.today().isoformat()
    selected_date_str = request.GET.get("date", today_str)
    
    # Fallback to today if an invalid date format is passed
    try:
        selected_date = datetime.date.fromisoformat(selected_date_str)
    except ValueError:
        selected_date = datetime.date.today()
        selected_date_str = today_str

    selected_meridiem = request.GET.get("meridiem", "AM")
    if selected_meridiem not in ["AM", "PM"]:
        selected_meridiem = "AM"

    # 2. Form Submission (POST)
    # 2. Form Submission (POST)
    if request.method == "POST":
        post_date_str = request.POST.get("booking_date", selected_date_str)
        try:
            booking_date = datetime.date.fromisoformat(post_date_str)
        except ValueError:
            booking_date = selected_date

        action_type = request.POST.get("action_type", "book")
        is_maintenance = (action_type == "maintenance")

        if room.under_maintanance:
            messages.error(request, f"{room.room_name} is currently under maintenance.")
            return redirect(f"{request.path}?date={booking_date}&meridiem={selected_meridiem}")

        selected_slot_ids = request.POST.getlist("slots")
        if not selected_slot_ids:
            messages.error(request, "Please select at least one time slot.")
            return redirect(f"{request.path}?date={booking_date}&meridiem={selected_meridiem}")

        sorted_ids = sorted([int(i) for i in selected_slot_ids])

        # Validate neighbor continuity
        for i in range(len(sorted_ids) - 1):
            if sorted_ids[i + 1] != sorted_ids[i] + 1:
                messages.error(request, "Selected slots must be continuous neighbors.")
                return redirect(f"{request.path}?date={booking_date}&meridiem={selected_meridiem}")

        start_t, _, _, _ = getSlotTimes(sorted_ids[0], selected_meridiem)
        _, end_t, _, _ = getSlotTimes(sorted_ids[-1], selected_meridiem)

        user_name = request.user.username if request.user.is_authenticated else "Guest User"

        # Check for slot overlap
        conflict = BookingsDetails.objects.filter(
            room_name=room.room_name,
            date=booking_date,
            start_time__lt=end_t,
            end_time__gt=start_t
        ).exists()

        if conflict:
            messages.error(request, "One or more selected slots are already booked or under maintenance.")
            return redirect(f"{request.path}?date={booking_date}&meridiem={selected_meridiem}")

        # Save to DB: sets under_maintainance=True if Admin clicked Mark Maintenance
        BookingsDetails.objects.create(
            room_name=room.room_name,
            date=booking_date,
            start_time=start_t,
            end_time=end_t,
            booked_by=user_name,
            under_maintainance=is_maintenance
        )

        if is_maintenance:
            messages.success(request, f"Slots from {start_t.strftime('%I:%M %p')} to {end_t.strftime('%I:%M %p')} marked under maintenance.")
        else:
            messages.success(request, f"Room booked successfully from {start_t.strftime('%I:%M %p')} to {end_t.strftime('%I:%M %p')}!")

        return redirect(f"{request.path}?date={booking_date}&meridiem={selected_meridiem}")

    # 3. GET Request: Fetch bookings on the selected date
    existing_bookings = BookingsDetails.objects.filter(
        room_name=room.room_name,
        date=selected_date
    )

    # 4. Construct 24 slot states
    slots = []
    for idx in range(24):
        start_t, end_t, start_lbl, end_lbl = getSlotTimes(idx, selected_meridiem)

        if room.under_maintanance:
            status = "maintenance"
        else:
            overlap = existing_bookings.filter(start_time__lt=end_t, end_time__gt=start_t).first()
            if overlap:
                status = "maintenance" if overlap.under_maintainance else "booked"
            else:
                status = "available"

        slots.append({
            "id": idx,
            "start": start_lbl,
            "end": end_lbl,
            "status": status
        })

    context = {
        "room": room,
        "slots": slots,
        "selected_date": selected_date_str,
        "today_date": today_str,
        "selected_meridiem": selected_meridiem,
    }
    return render(request, "room_booking.html", context)

# @require_login_and_filter(default_filter="today")
def myBookings(request,filter='today'):
    if request.method=="POST":
        room_id=request.POST.get("room_id")
        booking=BookingsDetails.objects.dele

    today=timezone.localdate()
    data=BookingsDetails.objects.filter(booked_by=request.user.username)

    if filter=="past":
        data=data.filter(date__lt=today).order_by('date', 'start_time')
    elif filter=="future":
        data=data.filter(date__gt=today).order_by('date', 'start_time')
    else:
        data=data.filter(date=today).order_by('start_time')
        filter="today"

    context={
        "data":data,
        "filter":filter
    }
    return render(request,"CRB_app/my_bookings.html",context)

@login_required_no_next
def cancelBooking(request):
    if request.method == "POST":
        booking_id = request.POST.get("booking_id")
        
        # Verify the booking exists and belongs to this user
        booking = get_object_or_404(
            BookingsDetails, 
            id=booking_id, 
            booked_by=request.user.username
        )
        
        booking.delete()  # Or update status: booking.status = 'cancelled'; booking.save()
        messages.success(request, "Booking cancelled successfully.")
        
    # Redirects back to the exact page/tab the user was on
    return redirect(request.META.get('HTTP_REFERER', 'my_bookings_default'))