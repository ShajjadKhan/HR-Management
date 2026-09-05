from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.urls import reverse
from .models import Employee, Property, LeaveRequest, LeaveBalance, LeavePolicy, Company, Holiday, EmployeeProperty
from .forms import LeaveRequestForm, EmployeeForm, PropertyForm, HolidayForm, LeavePolicyForm
from datetime import date, timedelta
import openpyxl
from django.db.models import Sum, Count
from django.contrib import messages

# ================== DASHBOARD ==================
def dashboard(request):
    context = {
        'employee_count': Employee.objects.count(),
        'property_count': Property.objects.count(),
        'leave_count': LeaveRequest.objects.count(),
        'pending_leave_count': LeaveRequest.objects.filter(status='pending').count(),
        'recent_employees': Employee.objects.all()[:5],
        'recent_properties': Property.objects.all()[:5],
        'expiring_soon': Employee.objects.filter(iqama_expiry__lte=date.today()+timedelta(days=21)).count(),
    }
    return render(request, 'employees/dashboard.html', context)

# ================== EMPLOYEES ==================
def employees_list(request):
    employees = Employee.objects.all()
    return render(request, 'employees/employees.html', {'employees': employees})

def employee_detail(request, pk):
    emp = get_object_or_404(Employee, pk=pk)
    balances = LeaveBalance.objects.filter(employee=emp).order_by('-year')
    current_balance = balances.first()
    assigned_props = EmployeeProperty.objects.filter(employee=emp)
    return render(request, 'employees/employee_detail.html', {
        'employee': emp,
        'balances': balances,
        'current_balance': current_balance,
        'assigned_props': assigned_props,
    })

@login_required
def employee_edit(request, pk):
    emp = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES, instance=emp)
        if form.is_valid():
            form.save()
            # Handle property assignment
            property_id = request.POST.get('property_id')
            if property_id:
                prop = get_object_or_404(Property, pk=property_id)
                EmployeeProperty.objects.update_or_create(employee=emp, defaults={'property': prop})
            else:
                EmployeeProperty.objects.filter(employee=emp).delete()
            messages.success(request, f"Employee {emp.name} updated successfully!")
            return redirect('employee_detail', pk=emp.pk)
    else:
        form = EmployeeForm(instance=emp)
    properties = Property.objects.all()
    assigned = EmployeeProperty.objects.filter(employee=emp).first()
    return render(request, 'employees/employee_form.html', {
        'form': form,
        'employee': emp,
        'properties': properties,
        'assigned': assigned,
    })

@login_required
def employee_delete(request, pk):
    emp = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        name = emp.name
        emp.delete()
        messages.success(request, f"Employee {name} deleted.")
        return redirect('employees_list')
    return render(request, 'employees/confirm_delete.html', {'object': emp, 'type': 'Employee'})

# ================== PROPERTIES ==================
def properties_list(request):
    properties = Property.objects.all()
    return render(request, 'employees/properties.html', {'properties': properties})

@login_required
def property_edit(request, pk):
    prop = get_object_or_404(Property, pk=pk)
    if request.method == 'POST':
        form = PropertyForm(request.POST, instance=prop)
        if form.is_valid():
            form.save()
            messages.success(request, f"Property {prop.property_name} updated!")
            return redirect('properties_list')
    else:
        form = PropertyForm(instance=prop)
    return render(request, 'employees/property_form.html', {'form': form, 'property': prop})

@login_required
def property_delete(request, pk):
    prop = get_object_or_404(Property, pk=pk)
    if request.method == 'POST':
        name = prop.property_name
        prop.delete()
        messages.success(request, f"Property {name} deleted.")
        return redirect('properties_list')
    return render(request, 'employees/confirm_delete.html', {'object': prop, 'type': 'Property'})

# ================== LEAVE ==================
@login_required
def leave_apply(request):
    if request.method == 'POST':
        form = LeaveRequestForm(request.POST, request.FILES)
        if form.is_valid():
            leave = form.save(commit=False)
            emp = Employee.objects.filter(user=request.user).first()
            if not emp:
                return HttpResponse("You are not linked to an employee.")
            leave.employee = emp
            leave.save()
            messages.success(request, "Leave request submitted.")
            return redirect('leave_list')
    else:
        form = LeaveRequestForm()
    return render(request, 'employees/leave_apply.html', {'form': form})

@login_required
def leave_list(request):
    if request.user.is_superuser or request.user.is_staff:
        leaves = LeaveRequest.objects.all().order_by('-applied_at')
    else:
        emp = Employee.objects.filter(user=request.user).first()
        leaves = LeaveRequest.objects.filter(employee=emp).order_by('-applied_at') if emp else []
    return render(request, 'employees/leave_list.html', {'leaves': leaves})

@login_required
def leave_approve(request, leave_id):
    leave = get_object_or_404(LeaveRequest, id=leave_id)
    if request.user.is_superuser or request.user.is_staff:
        if request.method == 'POST':
            action = request.POST.get('action')
            if action == 'approve':
                leave.status = 'approved'
                balance = LeaveBalance.objects.filter(employee=leave.employee, year=leave.start_date.year).first()
                if balance:
                    balance.used_balance += leave.total_days_worked
                    balance.save()
                messages.success(request, f"Leave approved.")
            elif action == 'reject':
                leave.status = 'rejected'
                messages.warning(request, f"Leave rejected.")
            leave.approved_by = request.user
            leave.approved_at = date.today()
            leave.save()
            return redirect('leave_list')
    return render(request, 'employees/leave_approve.html', {'leave': leave})

# ================== SALARY PAYMENT ==================
@login_required
def salary_pay(request, pk):
    emp = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        emp.salary_paid = True
        # Log payment history
        if emp.payment_history:
            emp.payment_history += f"\n{date.today()}: Paid SAR {emp.basic_salary} (Confirmed)"
        else:
            emp.payment_history = f"{date.today()}: Paid SAR {emp.basic_salary} (Confirmed)"
        emp.save()
        messages.success(request, f"✅ Salary for {emp.name} marked as paid. Confirmation saved.")
        return redirect('employee_detail', pk=emp.pk)
    return render(request, 'employees/salary_confirm.html', {'employee': emp})

# ================== HOLIDAYS ==================
@login_required
def holiday_list(request):
    holidays = Holiday.objects.all().order_by('holiday_date')
    return render(request, 'employees/holidays.html', {'holidays': holidays})

@login_required
def holiday_add(request):
    if request.method == 'POST':
        form = HolidayForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Holiday added.")
            return redirect('holiday_list')
    else:
        form = HolidayForm()
    return render(request, 'employees/holiday_form.html', {'form': form})

@login_required
def holiday_delete(request, pk):
    h = get_object_or_404(Holiday, pk=pk)
    if request.method == 'POST':
        h.delete()
        messages.success(request, "Holiday deleted.")
        return redirect('holiday_list')
    return render(request, 'employees/confirm_delete.html', {'object': h, 'type': 'Holiday'})

# ================== LEAVE POLICY ==================
@login_required
def policy_edit(request):
    policy = LeavePolicy.objects.first()
    if not policy:
        # Create one if none exists
        comp = Company.objects.first()
        if comp:
            policy = LeavePolicy.objects.create(company=comp)
    if request.method == 'POST':
        form = LeavePolicyForm(request.POST, instance=policy)
        if form.is_valid():
            form.save()
            messages.success(request, "Leave policy updated.")
            return redirect('dashboard')
    else:
        form = LeavePolicyForm(instance=policy)
    return render(request, 'employees/policy_form.html', {'form': form})

# ================== IQAMA ==================
@login_required
def iqama_expiry(request):
    today = date.today()
    employees = Employee.objects.filter(iqama_expiry__isnull=False).order_by('iqama_expiry')
    expiry_list = []
    for emp in employees:
        days_left = (emp.iqama_expiry - today).days
        color = 'danger' if days_left < 0 else 'warning' if days_left <= 21 else 'success'
        expiry_list.append({'employee': emp, 'days_left': days_left, 'color': color})
    return render(request, 'employees/iqama_expiry.html', {'expiry_list': expiry_list})

# ================== REPORTS ==================
@login_required
def reports(request):
    if request.method == 'POST':
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Employees"
        headers = ['Name', 'Position', 'Company', 'Salary', 'Joining Date', 'Iqama Expiry', 'Property']
        ws.append(headers)
        for emp in Employee.objects.all():
            prop = EmployeeProperty.objects.filter(employee=emp).first()
            prop_name = prop.property.property_name if prop else '-'
            ws.append([emp.name, emp.position, emp.company_name, str(emp.basic_salary), str(emp.joining_date), str(emp.iqama_expiry), prop_name])
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=hr_report.xlsx'
        wb.save(response)
        return response
    return render(request, 'employees/reports.html')

@login_required
def property_add(request):
    if request.method == 'POST':
        form = PropertyForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Property added successfully!")
            return redirect('properties_list')
    else:
        form = PropertyForm()
    return render(request, 'employees/property_form.html', {'form': form, 'property': None})
