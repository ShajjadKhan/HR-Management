from django.contrib import admin
from .models import (
    Company, Employee, Property, EmployeeProperty, LeavePolicy, 
    LeaveBalance, LeaveRequest, Holiday, Notification, EmployeeExpense, ClientCompany
)

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'cr_number', 'contact_person', 'email', 'phone', 'admin_account', 'plan', 'max_employees', 'is_active', 'subscription_expiry')
    list_filter = ('is_active', 'plan')
    search_fields = ('name', 'cr_number', 'contact_person', 'email', 'phone')
    list_editable = ('is_active',)

@admin.register(ClientCompany)
class ClientCompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'contact_person', 'phone', 'project_name', 'project_location', 'status', 'created_at')
    list_filter = ('company', 'status')
    search_fields = ('name', 'contact_person', 'project_name', 'project_location')

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('name', 'iqama_number', 'client_company', 'assigned_client', 'deployment_status', 'position', 'basic_salary', 'receiving_amount', 'iqama_expiry', 'visa_status')
    list_filter = ('client_company', 'assigned_client', 'deployment_status', 'visa_status')
    search_fields = ('name', 'iqama_number', 'passport_number', 'kafeel_name')

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('property_name', 'company', 'housing_type', 'cost_to_company', 'charge_to_client', 'worker_deduction', 'capacity', 'created_at')
    list_filter = ('company', 'housing_type')
    search_fields = ('property_name', 'location')

@admin.register(EmployeeExpense)
class EmployeeExpenseAdmin(admin.ModelAdmin):
    list_display = ('employee', 'company', 'expense_type', 'amount', 'expense_date', 'deduct_from_salary', 'is_settled')
    list_filter = ('company', 'expense_type', 'deduct_from_salary', 'is_settled')
    search_fields = ('employee__name', 'notes')

@admin.register(EmployeeProperty)
class EmployeePropertyAdmin(admin.ModelAdmin):
    list_display = ('employee', 'property', 'assigned_at')
    search_fields = ('employee__name', 'property__property_name')

@admin.register(LeavePolicy)
class LeavePolicyAdmin(admin.ModelAdmin):
    list_display = ('company', 'yearly_leave', 'carry_forward_limit', 'sick_leave_per_year', 'emergency_leave_per_year')

@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'year', 'accrued_balance', 'used_balance', 'negative_balance')
    list_filter = ('year',)

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('employee', 'leave_type', 'start_date', 'end_date', 'status', 'approved_by')
    list_filter = ('status', 'leave_type')

@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ('name', 'holiday_date', 'company')
    list_filter = ('company',)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'is_read', 'created_at')

