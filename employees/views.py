from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db.models import Sum, Q
from .forms import EmployeeForm
from .models import Employee

def add_employee(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('/admin/employees/employee/')
    else:
        form = EmployeeForm()
    return render(request, 'employees/add_employee.html', {'form': form})

def dashboard(request):
    total_employees = Employee.objects.count()
    total_revenue = Employee.objects.aggregate(Sum('receiving_amount'))['receiving_amount__sum'] or 0
    total_salary = Employee.objects.aggregate(Sum('basic_salary'))['basic_salary__sum'] or 0
    net_margin = total_revenue - total_salary

    context = {
        'total_employees': total_employees,
        'total_revenue': total_revenue,
        'net_margin': net_margin,
    }
    return render(request, 'employees/dashboard.html', context)

def search_employees(request):
    query = request.GET.get('q', '')
    if len(query) >= 2:
        results = list(Employee.objects.filter(Q(name__icontains=query) | Q(iqama_number__icontains=query)).values('id', 'name', 'iqama_number'))
        return JsonResponse(results, safe=False)
    return JsonResponse([], safe=False)
