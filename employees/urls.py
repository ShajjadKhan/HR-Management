from django.urls import path
from . import views

urlpatterns = [
    path('add/', views.add_employee, name='add_employee'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('search/', views.search_employees, name='search_employees'),
]
