from django.contrib import admin
from .models import Employee

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('name', 'iqama_number', 'company_name', 'basic_salary', 'iqama_expiry')
    search_fields = ('name', 'iqama_number', 'passport_number')
    list_filter = ('company_name', 'salary_paid')
