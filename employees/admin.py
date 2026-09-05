from django.contrib import admin
from .models import Company, Employee, Property, EmployeeProperty, LeavePolicy, LeaveBalance, LeaveRequest, Holiday, Notification

admin.site.register(Company)
admin.site.register(Employee)
admin.site.register(Property)
admin.site.register(EmployeeProperty)
admin.site.register(LeavePolicy)
admin.site.register(LeaveBalance)
admin.site.register(LeaveRequest)
admin.site.register(Holiday)
admin.site.register(Notification)
