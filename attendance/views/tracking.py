"""
tracking.py

This module handles GPS tracking views for attendance
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from attendance.models import AttendanceActivity, Attendance
from datetime import date, datetime, timedelta
from django.db.models import Q


@login_required
def tracking_view(request):
    """
    Display GPS tracking information for employees
    Shows currently clocked-in employees and their locations
    """
    # Get filter parameters
    selected_date = request.GET.get('date')
    employee_search = request.GET.get('employee', '').strip()
    
    # Parse selected date or use today
    if selected_date:
        try:
            filter_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except ValueError:
            filter_date = date.today()
    else:
        filter_date = date.today()
    
    # Base queryset for active check-ins
    active_checkins = AttendanceActivity.objects.filter(
        clock_out__isnull=True,
        attendance_date=filter_date
    ).select_related('employee_id', 'employee_id__employee_user_id')
    
    # Base queryset for completed activities
    completed_activities = AttendanceActivity.objects.filter(
        clock_out__isnull=False,
        attendance_date=filter_date
    ).select_related('employee_id', 'employee_id__employee_user_id')
    
    # Apply employee search filter
    if employee_search:
        active_checkins = active_checkins.filter(
            Q(employee_id__employee_user_id__username__icontains=employee_search) |
            Q(employee_id__employee_first_name__icontains=employee_search) |
            Q(employee_id__employee_last_name__icontains=employee_search)
        )
        completed_activities = completed_activities.filter(
            Q(employee_id__employee_user_id__username__icontains=employee_search) |
            Q(employee_id__employee_first_name__icontains=employee_search) |
            Q(employee_id__employee_last_name__icontains=employee_search)
        )
    
    # Order results
    active_checkins = active_checkins.order_by('-clock_in')
    completed_activities = completed_activities.order_by('-clock_out')
    
    # Calculate duration for each completed activity
    for activity in completed_activities:
        if activity.in_datetime and activity.out_datetime:
            duration = activity.out_datetime - activity.in_datetime
            total_seconds = duration.total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            activity.duration_display = f"{hours}h {minutes}m"
        else:
            activity.duration_display = "N/A"
    
    context = {
        'active_checkins': active_checkins,
        'completed_activities': completed_activities,
        'filter_date': filter_date,
        'today': date.today(),
        'employee_search': employee_search,
    }
    
    return render(request, 'attendance/tracking/tracking.html', context)