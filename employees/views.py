from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Sum, Q
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from .forms import EmployeeForm
from .models import Employee, Company

def client_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('dashboard')
    else: form = AuthenticationForm()
    return render(request, 'employees/login.html', {'form': form})

def client_logout(request):
    logout(request)
    return redirect('login')

@login_required(login_url='/employees/login/')
def add_company(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name: Company.objects.create(name=name); return redirect('dashboard')
    return render(request, 'employees/add_company.html')

@login_required(login_url='/employees/login/')
def add_employee(request):
    try: company = Company.objects.get(admin_account=request.user)
    except: company = None
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES)
        if form.is_valid():
            emp = form.save(commit=False)
            if company and not request.user.is_superuser:
                emp.client_company = company
            emp.save()
            return redirect('dashboard')
    else: form = EmployeeForm()
    return render(request, 'employees/add_employee.html', {'form': form})

@login_required(login_url='/employees/login/')
def dashboard(request):
    if request.user.is_superuser: emps = Employee.objects.all()
    else:
        try:
            company = Company.objects.get(admin_account=request.user)
            emps = Employee.objects.filter(client_company=company)
        except: return redirect('login')

    total_revenue = emps.aggregate(Sum('receiving_amount'))['receiving_amount__sum'] or 0
    total_salary = emps.aggregate(Sum('basic_salary'))['basic_salary__sum'] or 0
    thirty_days = timezone.now().date() + timedelta(days=30)
    expiring = emps.filter(iqama_expiry__range=[timezone.now().date(), thirty_days])

    context = {
        'total_employees': emps.count(), 'total_revenue': total_revenue,
        'net_margin': total_revenue - total_salary, 'expiring_count': expiring.count(),
        'employees': emps, 'today': timezone.now().date(), 'thirty_days': thirty_days
    }
    return render(request, 'employees/dashboard.html', context)

@login_required(login_url='/employees/login/')
def all_employees(request):
    if request.user.is_superuser: emps = Employee.objects.all()
    else:
        try:
            company = Company.objects.get(admin_account=request.user)
            emps = Employee.objects.filter(client_company=company)
        except: return redirect('login')

    thirty_days = timezone.now().date() + timedelta(days=30)
    return render(request, 'employees/all_employees.html', {
        'employees': emps, 'today': timezone.now().date(), 'thirty_days': thirty_days
    })

@login_required(login_url='/employees/login/')
def search_employees(request):
    if request.user.is_superuser: emps = Employee.objects.all()
    else:
        try:
            company = Company.objects.get(admin_account=request.user)
            emps = Employee.objects.filter(client_company=company)
        except: return JsonResponse([], safe=False)
    q = request.GET.get('q', '')
    if len(q) >= 2:
        results = list(emps.filter(Q(name__icontains=q) | Q(iqama_number__icontains=q)).values('id', 'name', 'iqama_number', 'position'))
        return JsonResponse(results, safe=False)
    return JsonResponse([], safe=False)

@login_required(login_url='/employees/login/')
def employee_profile(request, id):
    if request.user.is_superuser: employee = get_object_or_404(Employee, id=id)
    else:
        try:
            company = Company.objects.get(admin_account=request.user)
            employee = get_object_or_404(Employee, id=id, client_company=company)
        except: return redirect('login')

    if request.method == 'POST':
        if 'mark_paid_month' in request.POST:
            month = request.POST.get('mark_paid_month')
            paid_list = [m.strip() for m in (employee.payment_history or '').split(',') if m.strip()]
            if month in paid_list: paid_list.remove(month)
            else: paid_list.append(month)
            employee.payment_history = ','.join(paid_list)
            employee.save()
        elif 'increment_percentage' in request.POST:
            percentage = request.POST.get('increment_percentage')
            if percentage:
                employee.basic_salary += employee.basic_salary * (Decimal(percentage) / Decimal(100))
                employee.save()
        else:
            form = EmployeeForm(request.POST, request.FILES, instance=employee)
            if form.is_valid():
                updated_emp = form.save()
                if not request.user.is_superuser and updated_emp.client_company != company:
                    return redirect('dashboard')
        return redirect('employee_profile', id=employee.id)

    form = EmployeeForm(instance=employee)
    months = ['Jan 2026', 'Feb 2026', 'Mar 2026', 'Apr 2026', 'May 2026', 'Jun 2026', 'Jul 2026', 'Aug 2026', 'Sep 2026', 'Oct 2026', 'Nov 2026', 'Dec 2026']
    paid_list = [m.strip() for m in (employee.payment_history or '').split(',') if m.strip()]
    months_status = [{'name': m, 'is_paid': m in paid_list} for m in months]

    return render(request, 'employees/profile.html', {'employee': employee, 'form': form, 'months_status': months_status})

@login_required(login_url='/employees/login/')
def delete_employee(request, id):
    if request.user.is_superuser:
        employee = get_object_or_404(Employee, id=id)
    else:
        try:
            company = Company.objects.get(admin_account=request.user)
            employee = get_object_or_404(Employee, id=id, client_company=company)
        except:
            return redirect('login')

    employee.delete()
    return redirect('dashboard')

@login_required(login_url='/employees/login/')
def company_list(request):
    companies = Company.objects.all()
    return render(request, 'employees/company_list.html', {'companies': companies})

@login_required(login_url='/employees/login/')
def delete_company(request, id):
    if request.user.is_superuser:
        company = get_object_or_404(Company, id=id)
        company.delete()
    return redirect('company_list')
