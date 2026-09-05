from django import forms
from .models import LeaveRequest, Employee, Property, Holiday, LeavePolicy

class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['leave_type', 'start_date', 'end_date', 'is_half_day', 'reason', 'attachment']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        exclude = ['user', 'payment_history', 'salary_paid']
        widgets = {
            'joining_date': forms.DateInput(attrs={'type': 'date'}),
            'iqama_expiry': forms.DateInput(attrs={'type': 'date'}),
            'transfer_dates': forms.DateInput(attrs={'type': 'date'}),
        }

class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = ['property_name', 'charge_amount']  # employee_salary বাদ

class HolidayForm(forms.ModelForm):
    class Meta:
        model = Holiday
        fields = ['holiday_date', 'name']
        widgets = {
            'holiday_date': forms.DateInput(attrs={'type': 'date'}),
        }

class LeavePolicyForm(forms.ModelForm):
    class Meta:
        model = LeavePolicy
        fields = ['yearly_leave', 'carry_forward_limit', 'sick_leave_per_year', 'emergency_leave_per_year', 'allow_negative', 'negative_limit']
