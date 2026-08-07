from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.client_login, name='login'),
    path('logout/', views.client_logout, name='logout'),
    path('add/', views.add_employee, name='add_employee'),
    path('add-company/', views.add_company, name='add_company'),
    path('companies/', views.company_list, name='company_list'),
    path('delete-company/<int:id>/', views.delete_company, name='delete_company'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('list/', views.all_employees, name='all_employees'),
    path('search/', views.search_employees, name='search_employees'),
    path('profile/<int:id>/', views.employee_profile, name='employee_profile'),
    path('delete/<int:id>/', views.delete_employee, name='delete_employee'),
]
