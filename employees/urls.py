from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    
    # Employees
    path('employees/', views.employees_list, name='employees_list'),
    path('employees/<int:pk>/', views.employee_detail, name='employee_detail'),
    path('employees/<int:pk>/edit/', views.employee_edit, name='employee_edit'),
    path('employees/<int:pk>/delete/', views.employee_delete, name='employee_delete'),
    
    # Properties
    path('properties/', views.properties_list, name='properties_list'),
    path('properties/add/', views.property_add, name='property_add'),
    path('properties/<int:pk>/edit/', views.property_edit, name='property_edit'),
    path('properties/<int:pk>/delete/', views.property_delete, name='property_delete'),
    
    # Leave
    path('leave/apply/', views.leave_apply, name='leave_apply'),
    path('leave/list/', views.leave_list, name='leave_list'),
    path('leave/approve/<int:leave_id>/', views.leave_approve, name='leave_approve'),
    
    # Salary
    path('salary/pay/<int:pk>/', views.salary_pay, name='salary_pay'),
    
    # Holidays
    path('holidays/', views.holiday_list, name='holiday_list'),
    path('holidays/add/', views.holiday_add, name='holiday_add'),
    path('holidays/<int:pk>/delete/', views.holiday_delete, name='holiday_delete'),
    
    # Leave Policy
    path('policy/edit/', views.policy_edit, name='policy_edit'),
    
    # Iqama & Reports
    path('iqama/', views.iqama_expiry, name='iqama_expiry'),
    path('reports/', views.reports, name='reports'),
]
