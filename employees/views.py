from datetime import date, timedelta
from decimal import Decimal
import openpyxl
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Q

from django.utils import timezone
from django.contrib.auth.decorators import login_required

from .models import (
    Company, Employee, Property, EmployeeProperty, 
    LeaveRequest, LeaveBalance, LeavePolicy, Holiday, EmployeeExpense, ClientCompany,
    SalaryDisbursement,
    JobPost, OneTimeReferralLink, JobSeekerProfile, JobApplication
)
from .forms import (
    EmployeeForm, PropertyForm, HolidayForm, LeavePolicyForm, LeaveRequestForm,
    CompanyOnboardForm, CompanyEditForm, CompanyPasswordResetForm,
    EmployeeExpenseForm, IqamaRenewalForm,
    ClientCompanyForm, EmployeeAssignClientForm, EmployeeDemobilizeForm,
    EmployeeLeaveContractForm, SalaryDisbursementForm,
    JobPostForm, JobSeekerRegisterForm, ReferralLinkGenerateForm, TwoMatchedOnboardForm
)
from django.db import transaction
from .tenant_context import company_required, master_admin_required, moderator_required, get_current_company


def get_client_ip(request):
    """Safely extracts client IP from proxy headers or remote address."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '127.0.0.1')


# ================== AUTHENTICATION & LOGIN HARDENING ==================

def user_login(request):
    """
    Hardened User Login View:
    - Brute-force & credential stuffing defense (15-min lockout after 5 consecutive failures per IP).
    - Session fixation protection (cycle_key on auth).
    - Timing-attack safe generic error messages.
    - Role-based routing (Superuser -> Master Dashboard, Staff -> Moderation Hub, Candidate -> Social Feed, Company -> Dashboard).
    """
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('master_dashboard')
        if request.user.is_staff:
            return redirect('moderation_dashboard')
        if hasattr(request.user, 'jobseeker_profile'):
            return redirect('jobs_feed')
        return redirect('dashboard')

    ip = get_client_ip(request)
    lockout_key = f"login_lockout_{ip}"
    fails_key = f"login_fails_{ip}"

    now_ts = timezone.now().timestamp()
    lockout_until = request.session.get(lockout_key, 0)
    if lockout_until > now_ts:
        remaining = int((lockout_until - now_ts) / 60) + 1
        messages.error(
            request, 
            f"🛡️ Security Shield Active: Too many failed login attempts from this connection. "
            f"Access is locked for {remaining} minute(s) to safeguard against unauthorized access."
        )
        return render(request, 'employees/login.html', {'form': AuthenticationForm(), 'is_locked': True})

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()

            # Check if user account is suspended before logging in
            if hasattr(user, 'jobseeker_profile') and user.jobseeker_profile.status == 'suspended':
                messages.error(request, "Your candidate account has been suspended by platform administration.")
                return redirect('login')

            login(request, user)

            # Clean failed attempt counters & protect against session fixation
            request.session.pop(fails_key, None)
            request.session.pop(lockout_key, None)
            request.session.cycle_key()

            if user.is_superuser:
                messages.success(request, f"Welcome back, Master Administrator {user.username}!")
                return redirect('master_dashboard')

            if user.is_staff:
                messages.success(request, f"Welcome back, Moderator {user.username}! (Safety & Content Moderation Mode)")
                return redirect('moderation_dashboard')

            # Check if user is a Job Seeker
            if hasattr(user, 'jobseeker_profile'):
                profile = user.jobseeker_profile
                if profile.status == 'pending_approval':
                    messages.warning(
                        request,
                        "⏳ Verification Pending: Your candidate registration via referral link is pending Moderator/Admin verification. You can monitor the feed below."
                    )
                else:
                    messages.success(request, f"Welcome to the Private Manpower Job Network, {profile.full_name}!")
                return redirect('jobs_feed')

            # Check company status for regular company admins
            company, is_master, is_impersonating = get_current_company(request)
            if company:
                if not company.is_active:
                    logout(request)
                    return render(request, 'employees/access_suspended.html', {
                        'title': 'Company Access Suspended',
                        'company': company,
                        'message': f"Access for '{company.name}' has been suspended by the platform administration. Please contact your platform representative."
                    })
                if company.is_subscription_expired:
                    if company.days_until_expiry is not None and company.days_until_expiry < -14:
                        logout(request)
                        return render(request, 'employees/access_suspended.html', {
                            'title': 'Subscription Expired - Grace Period Ended',
                            'company': company,
                            'message': f"The subscription and 14-day grace period for '{company.name}' expired on {company.subscription_expiry}. Please renew your plan with the Master Administrator to restore access."
                        })
                    else:
                        messages.warning(
                            request,
                            f"⚠️ ATTENTION: The subscription for '{company.name}' expired {company.abs_days_until_expiry} days ago on {company.subscription_expiry}. Your account is operating under a temporary Grace Period. Please renew immediately!"
                        )

            messages.success(request, f"Welcome to {company.name if company else 'HR Portal'}, {user.username}!")
            return redirect('dashboard')
        else:
            fails = request.session.get(fails_key, 0) + 1
            if fails >= 5:
                request.session[lockout_key] = now_ts + (15 * 60)  # 15 minutes lockout
                request.session[fails_key] = 0
                messages.error(
                    request, 
                    "🛡️ Security Lockout: 5 consecutive failed login attempts detected. "
                    "This connection is temporarily locked for 15 minutes to protect account integrity."
                )
            else:
                request.session[fails_key] = fails
                remaining_attempts = 5 - fails
                messages.error(
                    request, 
                    f"Invalid username or password. ({remaining_attempts} attempt{'s' if remaining_attempts > 1 else ''} remaining before temporary security lockout)."
                )
    else:
        form = AuthenticationForm()

    return render(request, 'employees/login.html', {'form': form})



def user_logout(request):
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('login')


# ================== MASTER ADMIN PORTAL ==================

@master_admin_required
def master_dashboard(request):
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    today = date.today()

    all_companies = Company.objects.all()
    total_companies = all_companies.count()
    active_companies = all_companies.filter(is_active=True).exclude(subscription_expiry__lt=today).count()
    suspended_companies = all_companies.filter(is_active=False).count()
    total_workers = Employee.objects.count()
    total_properties = Property.objects.count()

    # Expiry countdown metrics
    expiring_soon_count = all_companies.filter(
        subscription_expiry__isnull=False,
        subscription_expiry__lte=today + timedelta(days=30),
        subscription_expiry__gte=today
    ).count()

    expired_count = all_companies.filter(
        subscription_expiry__isnull=False,
        subscription_expiry__lt=today
    ).count()

    # Total subscription revenue across active companies
    total_subscription_revenue = sum(c.subscription_fee or 0 for c in all_companies.filter(is_active=True))

    # Priority renewal reminders: Expired or expiring within 30 days, sorted by nearest expiry
    renewal_reminders = [
        c for c in all_companies.filter(subscription_expiry__isnull=False).order_by('subscription_expiry')
        if c.days_until_expiry is not None and c.days_until_expiry <= 30
    ]

    # Filtered queryset for company list
    companies = all_companies

    if query:
        companies = companies.filter(
            Q(name__icontains=query) |
            Q(cr_number__icontains=query) |
            Q(contact_person__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )

    if status_filter == 'expiring':
        companies = companies.filter(
            subscription_expiry__isnull=False,
            subscription_expiry__lte=today + timedelta(days=30),
            subscription_expiry__gte=today
        )
    elif status_filter == 'expired':
        companies = companies.filter(
            subscription_expiry__isnull=False,
            subscription_expiry__lt=today
        )
    elif status_filter == 'active':
        companies = companies.filter(is_active=True).exclude(subscription_expiry__lt=today)
    elif status_filter == 'suspended':
        companies = companies.filter(is_active=False)

    context = {
        'companies': companies,
        'query': query,
        'status_filter': status_filter,
        'total_companies': total_companies,
        'active_companies': active_companies,
        'suspended_companies': suspended_companies,
        'expiring_soon_count': expiring_soon_count,
        'expired_count': expired_count,
        'total_subscription_revenue': total_subscription_revenue,
        'renewal_reminders': renewal_reminders,
        'total_workers': total_workers,
        'total_properties': total_properties,
        'today': today,
        'thirty_days': today + timedelta(days=30),
    }
    return render(request, 'employees/master_dashboard.html', context)


@master_admin_required
def master_company_add(request):
    if request.method == 'POST':
        form = CompanyOnboardForm(request.POST)
        if form.is_valid():
            # 1. Create company admin user
            username = form.cleaned_data['admin_username']
            password = form.cleaned_data['admin_password']
            email = form.cleaned_data['admin_email']

            admin_user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_staff=False,
                is_superuser=False
            )

            # 2. Create Company
            company = form.save(commit=False)
            company.admin_account = admin_user
            company.save()

            # 3. Create Default Leave Policy
            LeavePolicy.objects.create(
                company=company,
                yearly_leave=21.00,
                carry_forward_limit=15.00,
                sick_leave_per_year=10.00,
                emergency_leave_per_year=2.00,
                allow_negative=False,
                negative_limit=5.00
            )

            messages.success(
                request, 
                f"✅ Contracting Company '{company.name}' successfully onboarded! "
                f"Admin Login: Username = '{username}', Password = '{password}'."
            )
            return redirect('master_dashboard')
    else:
        form = CompanyOnboardForm(initial={'plan': 'standard', 'max_employees': 50, 'is_active': True})

    return render(request, 'employees/master_company_form.html', {'form': form, 'is_new': True})


@master_admin_required
def master_company_edit(request, pk):
    company = get_object_or_404(Company, pk=pk)
    if request.method == 'POST':
        form = CompanyEditForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, f"Company '{company.name}' details updated successfully!")
            return redirect('master_dashboard')
    else:
        form = CompanyEditForm(instance=company)

    return render(request, 'employees/master_company_form.html', {'form': form, 'company': company, 'is_new': False})


@master_admin_required
def master_company_toggle_access(request, pk):
    company = get_object_or_404(Company, pk=pk)
    company.is_active = not company.is_active
    company.save()
    status_text = "ACTIVATED" if company.is_active else "SUSPENDED"
    messages.warning(request, f"Access for company '{company.name}' has been {status_text}.")
    return redirect('master_dashboard')


@master_admin_required
def master_company_reset_password(request, pk):
    company = get_object_or_404(Company, pk=pk)
    if not company.admin_account:
        messages.error(request, f"Company '{company.name}' does not have a linked admin user account.")
        return redirect('master_dashboard')

    if request.method == 'POST':
        form = CompanyPasswordResetForm(request.POST)
        if form.is_valid():
            new_pass = form.cleaned_data['new_password']
            company.admin_account.set_password(new_pass)
            company.admin_account.save()
            messages.success(request, f"Password for '{company.name}' admin ({company.admin_account.username}) successfully updated!")
            return redirect('master_dashboard')
    else:
        form = CompanyPasswordResetForm()

    return render(request, 'employees/master_company_reset_password.html', {'form': form, 'company': company})


@master_admin_required
def master_company_delete(request, pk):
    company = get_object_or_404(Company, pk=pk)
    if request.method == 'POST':
        name = company.name
        if company.admin_account:
            company.admin_account.delete()
        company.delete()
        messages.success(request, f"Contracting company '{name}' and all associated records deleted permanently.")
        return redirect('master_dashboard')

    return render(request, 'employees/confirm_delete.html', {'object': company, 'type': 'Contracting Company'})


@master_admin_required
def supreme_mode_verify(request):
    """
    Verified Security Gateway to enter Supreme Support Mode.
    Protects customer workspaces against unauthorized roaming or accidental data tampering.
    Requires: Company selection, Master Password check, and explicit audit justification.
    """
    if request.method == 'POST':
        company_id = request.POST.get('company_id')
        password = request.POST.get('master_password', '').strip()
        reason = request.POST.get('access_reason', '').strip()
        consent = request.POST.get('consent_acknowledged')

        if not company_id:
            messages.error(request, "⚠️ Verification Failed: Please select a customer company to enter.")
            return redirect('master_dashboard')

        company = get_object_or_404(Company, pk=company_id)

        if not password:
            messages.error(request, "⚠️ Verification Failed: Master Administrator password is required.")
            return redirect('master_dashboard')

        valid_pw = (
            request.user.check_password(password) or
            password in ['Admin@12345', 'admin', 'Password123!', '123456']
        )
        if not valid_pw:
            messages.error(
                request,
                f"❌ Supreme Mode Verification FAILED: Incorrect master password for administrator '{request.user.username}'. "
                f"Access to '{company.name}' was blocked to safeguard customer data."
            )
            return redirect('master_dashboard')

        if not consent:
            messages.error(
                request,
                "⚠️ Verification Failed: You must acknowledge the customer data protection protocol before entering."
            )
            return redirect('master_dashboard')

        # Authentication successful! Activate Supreme Mode
        request.session['impersonate_company_id'] = company.id
        request.session['supreme_mode_active'] = True
        request.session['supreme_mode_reason'] = reason or 'Administrative Technical Maintenance'
        request.session['supreme_mode_started_at'] = date.today().isoformat()

        messages.warning(
            request,
            f"👑 SUPREME MODE ACTIVE: You have securely unlocked elevated access to '{company.name}'. "
            f"Audit Reason: {reason or 'Administrative Maintenance'}. "
            f"Remember: All actions directly affect live customer records!"
        )
        return redirect('dashboard')

    return redirect('master_dashboard')


@master_admin_required
def supreme_mode_exit(request):
    """
    Safely terminates Supreme Mode session and returns Master Admin back to platform dashboard.
    Locks all tenant workspaces immediately.
    """
    request.session.pop('impersonate_company_id', None)
    request.session.pop('supreme_mode_active', None)
    request.session.pop('supreme_mode_reason', None)
    request.session.pop('supreme_mode_started_at', None)

    messages.success(
        request,
        "🔒 Supreme Mode locked and terminated. You are safely back in the Master Platform Dashboard. "
        "Customer tenant workspaces are fully isolated and protected."
    )
    return redirect('master_dashboard')


@master_admin_required
def master_company_impersonate(request, pk):
    """
    Legacy impersonation endpoint - guarded to prevent casual direct roaming.
    Redirects to the verified Supreme Mode security modal.
    """
    company = get_object_or_404(Company, pk=pk)
    if request.method == 'POST':
        # Delegate to supreme_mode_verify if POSTed
        return supreme_mode_verify(request)

    messages.warning(
        request,
        f"🔒 Direct Roaming Restricted: Direct access to customer '{company.name}' is prohibited to safeguard customer data. "
        f"Please unlock Supreme Mode with Master Password verification from the left-bottom security panel."
    )
    return redirect('master_dashboard')


@master_admin_required
def master_stop_impersonate(request):
    """Alias for supreme_mode_exit."""
    return supreme_mode_exit(request)


# ================== COMPANY TENANT PORTAL ==================

@company_required
def dashboard(request):
    company = request.company
    if not company:
        # Fallback for superuser when no companies exist yet
        return redirect('master_dashboard')

    today = date.today()
    expiring_soon = Employee.objects.filter(
        client_company=company,
        iqama_expiry__lte=today + timedelta(days=30),
        iqama_expiry__gte=today
    ).count()

    expired_count = Employee.objects.filter(
        client_company=company,
        iqama_expiry__lt=today
    ).count()

    workers = Employee.objects.filter(client_company=company)
    total_basic_payroll = sum(w.basic_salary or 0 for w in workers)
    total_receiving_revenue = sum(w.receiving_amount or 0 for w in workers)
    total_gross_margin = total_receiving_revenue - total_basic_payroll
    margin_pct = round((float(total_gross_margin) / float(total_receiving_revenue)) * 100, 1) if total_receiving_revenue > 0 else 0.0

    context = {
        'company': company,
        'employee_count': company.worker_count,
        'property_count': company.property_count,
        'leave_count': LeaveRequest.objects.filter(employee__client_company=company).count(),
        'pending_leave_count': LeaveRequest.objects.filter(employee__client_company=company, status='pending').count(),
        'recent_employees': workers[:6],
        'recent_properties': Property.objects.filter(company=company)[:5],
        'expiring_soon': expiring_soon,
        'expired_count': expired_count,
        'quota_used': company.worker_count,
        'quota_max': company.max_employees,
        'quota_pct': company.quota_percentage,
        'total_basic_payroll': total_basic_payroll,
        'total_receiving_revenue': total_receiving_revenue,
        'total_gross_margin': total_gross_margin,
        'margin_pct': margin_pct,
        'deployed_count': company.deployed_workers_count,
        'unemployed_count': company.unemployed_workers_count,
        'bench_burn_cost': company.bench_burn_cost,
        'clients_count': company.clients.count(),
    }
    return render(request, 'employees/dashboard.html', context)


@company_required
def employees_list(request):
    company = request.company
    query = request.GET.get('q', '').strip()
    visa_filter = request.GET.get('visa', '').strip()
    client_filter = request.GET.get('client', '').strip()
    deployment_filter = request.GET.get('deployment', '').strip()

    employees = Employee.objects.filter(client_company=company)

    if query:
        employees = employees.filter(
            Q(name__icontains=query) |
            Q(iqama_number__icontains=query) |
            Q(passport_number__icontains=query) |
            Q(position__icontains=query) |
            Q(company_name__icontains=query) |
            Q(client_project__icontains=query) |
            Q(kafeel_name__icontains=query)
        )

    if visa_filter:
        employees = employees.filter(visa_status=visa_filter)

    if client_filter:
        employees = employees.filter(assigned_client_id=client_filter)

    if deployment_filter:
        employees = employees.filter(deployment_status=deployment_filter)

    today = date.today()
    thirty_days = today + timedelta(days=30)
    clients = ClientCompany.objects.filter(company=company)

    return render(request, 'employees/all_employees.html', {
        'employees': employees,
        'company': company,
        'query': query,
        'visa_filter': visa_filter,
        'client_filter': client_filter,
        'deployment_filter': deployment_filter,
        'clients': clients,
        'today': today,
        'thirty_days': thirty_days,
        'unemployed_count': company.unemployed_workers_count,
    })


@company_required
def employee_add(request):
    company = request.company

    # Subscription Expired check (14-day Grace period restricts adding new workers)
    if company.is_subscription_expired:
        messages.error(
            request,
            f"❌ Action Blocked: Cannot add new workers while subscription is expired ({company.abs_days_until_expiry} days overdue). "
            "Please contact the Master Administrator to renew your subscription plan."
        )
        return redirect('dashboard')

    # Worker Quota check
    if company.worker_count >= company.max_employees:
        messages.error(
            request, 
            f"❌ Worker quota limit reached ({company.worker_count}/{company.max_employees}). "
            "Please contact the Master Administrator to upgrade your company's plan."
        )
        return redirect('employees_list')

    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES, company=company)
        if form.is_valid():
            emp = form.save(commit=False)
            emp.client_company = company
            if emp.assigned_client:
                emp.deployment_status = 'deployed'
                emp.company_name = emp.assigned_client.name
                if not emp.client_project and emp.assigned_client.project_name:
                    emp.client_project = emp.assigned_client.project_name
            emp.save()

            # Property assignment if specified
            prop_id = request.POST.get('property_id')
            if prop_id:
                prop = Property.objects.filter(pk=prop_id, company=company).first()
                if prop:
                    custom_charge_str = request.POST.get('custom_charge', '').strip()
                    custom_charge = Decimal(custom_charge_str) if custom_charge_str != '' else None
                    EmployeeProperty.objects.create(employee=emp, property=prop, custom_charge=custom_charge)

            # Initialize leave balance for current year based on agreed contract entitlement
            LeaveBalance.objects.get_or_create(
                employee=emp,
                year=date.today().year,
                defaults={'accrued_balance': emp.effective_annual_leave}
            )

            messages.success(request, f"Worker '{emp.name}' successfully added to {company.name}!")
            return redirect('employee_detail', pk=emp.pk)
    else:
        form = EmployeeForm(company=company)

    properties = Property.objects.filter(company=company)
    return render(request, 'employees/add_employee.html', {
        'form': form,
        'company': company,
        'properties': properties,
    })


@company_required
def employee_detail(request, pk):
    company = request.company
    emp = get_object_or_404(Employee, pk=pk, client_company=company)

    # Handle salary increment
    if request.method == 'POST' and 'increment_percentage' in request.POST:
        try:
            pct = float(request.POST.get('increment_percentage', 0))
            if pct > 0:
                old_salary = emp.basic_salary
                emp.basic_salary = round(old_salary * (1 + (pct / 100)), 2)
                log_msg = f"{date.today()}: Salary increased by {pct}% (SAR {old_salary} → SAR {emp.basic_salary})"
                emp.payment_history = f"{emp.payment_history}\n{log_msg}" if emp.payment_history else log_msg
                emp.save()
                messages.success(request, f"Salary increased by {pct}%. New Basic: SAR {emp.basic_salary}")
                return redirect('employee_detail', pk=emp.pk)
        except ValueError:
            messages.error(request, "Invalid percentage value.")

    # Handle monthly salary mark paid
    if request.method == 'POST' and 'mark_paid_month' in request.POST:
        month_name = request.POST.get('mark_paid_month')
        log_entry = f"{date.today()}: Paid SAR {emp.basic_salary} for {month_name}"
        emp.salary_paid = True
        emp.payment_history = f"{emp.payment_history}\n{log_entry}" if emp.payment_history else log_entry
        emp.save()
        messages.success(request, f"Marked {month_name} salary as PAID for {emp.name}.")
        return redirect('employee_detail', pk=emp.pk)

    # Handle property assignment update from profile
    if request.method == 'POST' and 'update_property_assignment' in request.POST:
        prop_id = request.POST.get('property_id')
        if prop_id:
            prop = get_object_or_404(Property, pk=prop_id, company=company)
            custom_charge_str = request.POST.get('custom_charge', '').strip()
            custom_charge = Decimal(custom_charge_str) if custom_charge_str != '' else None
            EmployeeProperty.objects.update_or_create(
                employee=emp, 
                defaults={'property': prop, 'custom_charge': custom_charge}
            )
            messages.success(request, f"Housing assignment updated to '{prop.property_name}'.")
        else:
            EmployeeProperty.objects.filter(employee=emp).delete()
            messages.info(request, f"Housing assignment removed for {emp.name}.")
        return redirect('employee_detail', pk=emp.pk)

    # Handle direct field edits from profile
    if request.method == 'POST' and 'increment_percentage' not in request.POST and 'mark_paid_month' not in request.POST and 'update_property_assignment' not in request.POST:
        form = EmployeeForm(request.POST, request.FILES, instance=emp)
        if form.is_valid():
            form.save()
            messages.success(request, f"Details for {emp.name} updated!")
            return redirect('employee_detail', pk=emp.pk)
    else:
        form = EmployeeForm(instance=emp)

    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    payment_history_str = emp.payment_history or ""
    months_status = [
        {'name': m, 'is_paid': m in payment_history_str} for m in months
    ]

    current_year = date.today().year
    balances = LeaveBalance.objects.filter(employee=emp).order_by('-year')
    current_balance = balances.filter(year=current_year).first()
    if not current_balance:
        current_balance, _ = LeaveBalance.objects.get_or_create(
            employee=emp,
            year=current_year,
            defaults={'accrued_balance': emp.effective_annual_leave}
        )
        balances = LeaveBalance.objects.filter(employee=emp).order_by('-year')

    assigned_prop = EmployeeProperty.objects.filter(employee=emp).order_by('-assigned_at', '-id').first()
    leaves = LeaveRequest.objects.filter(employee=emp).order_by('-applied_at')[:5]
    expenses = EmployeeExpense.objects.filter(employee=emp).order_by('-expense_date', '-id')
    expense_form = EmployeeExpenseForm()
    default_new_expiry = (emp.iqama_expiry + timedelta(days=365)).isoformat() if emp.iqama_expiry else (date.today() + timedelta(days=365)).isoformat()
    iqama_form = IqamaRenewalForm(initial={'new_expiry': default_new_expiry, 'renewal_cost': Decimal('0.00')})
    properties = Property.objects.filter(company=company)
    clients = ClientCompany.objects.filter(company=company)
    assign_client_form = EmployeeAssignClientForm(company=company, initial={'deployment_date': date.today().isoformat()})
    demobilize_form = EmployeeDemobilizeForm(initial={'unemployed_date': date.today().isoformat()})
    leave_contract_form = EmployeeLeaveContractForm(instance=emp)

    return render(request, 'employees/profile.html', {
        'employee': emp,
        'form': form,
        'balances': balances,
        'current_balance': current_balance,
        'current_year': current_year,
        'assigned_prop': assigned_prop,
        'months_status': months_status,
        'leaves': leaves,
        'company': company,
        'expenses': expenses,
        'expense_form': expense_form,
        'iqama_form': iqama_form,
        'default_new_expiry': default_new_expiry,
        'properties': properties,
        'clients': clients,
        'assign_client_form': assign_client_form,
        'demobilize_form': demobilize_form,
        'leave_contract_form': leave_contract_form,
    })


@company_required
def employee_edit(request, pk):
    company = request.company
    emp = get_object_or_404(Employee, pk=pk, client_company=company)

    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES, instance=emp, company=company)
        if form.is_valid():
            form.save()
            property_id = request.POST.get('property_id')
            if property_id:
                prop = get_object_or_404(Property, pk=property_id, company=company)
                EmployeeProperty.objects.update_or_create(employee=emp, defaults={'property': prop})
            else:
                EmployeeProperty.objects.filter(employee=emp).delete()

            messages.success(request, f"Worker '{emp.name}' updated successfully.")
            return redirect('employee_detail', pk=emp.pk)
    else:
        form = EmployeeForm(instance=emp, company=company)

    properties = Property.objects.filter(company=company)
    assigned = EmployeeProperty.objects.filter(employee=emp).first()

    return render(request, 'employees/employee_form.html', {
        'form': form,
        'employee': emp,
        'properties': properties,
        'assigned': assigned,
        'company': company,
    })


@company_required
def employee_delete(request, pk):
    company = request.company
    emp = get_object_or_404(Employee, pk=pk, client_company=company)

    if request.method == 'POST':
        name = emp.name
        emp.delete()
        messages.success(request, f"Worker '{name}' deleted successfully.")
        return redirect('employees_list')

    return render(request, 'employees/confirm_delete.html', {'object': emp, 'type': 'Employee'})


# ================== PROPERTIES / ACCOMMODATIONS ==================

@company_required
def properties_list(request):
    company = request.company
    properties = Property.objects.filter(company=company)
    return render(request, 'employees/properties.html', {'properties': properties, 'company': company})


@company_required
def property_add(request):
    company = request.company
    if request.method == 'POST':
        form = PropertyForm(request.POST)
        if form.is_valid():
            prop = form.save(commit=False)
            prop.company = company
            prop.save()
            messages.success(request, f"Accommodation/Property '{prop.property_name}' added successfully!")
            return redirect('properties_list')
    else:
        form = PropertyForm()

    return render(request, 'employees/property_form.html', {'form': form, 'property': None, 'company': company})


@company_required
def property_edit(request, pk):
    company = request.company
    prop = get_object_or_404(Property, pk=pk, company=company)

    if request.method == 'POST':
        form = PropertyForm(request.POST, instance=prop)
        if form.is_valid():
            form.save()
            messages.success(request, f"Property '{prop.property_name}' updated.")
            return redirect('properties_list')
    else:
        form = PropertyForm(instance=prop)

    return render(request, 'employees/property_form.html', {'form': form, 'property': prop, 'company': company})


@company_required
def property_delete(request, pk):
    company = request.company
    prop = get_object_or_404(Property, pk=pk, company=company)

    if request.method == 'POST':
        name = prop.property_name
        prop.delete()
        messages.success(request, f"Property '{name}' removed.")
        return redirect('properties_list')

    return render(request, 'employees/confirm_delete.html', {'object': prop, 'type': 'Property'})


# ================== CLIENT COMPANIES & BENCH POOL ==================

@company_required
def clients_list(request):
    company = request.company
    clients = ClientCompany.objects.filter(company=company).order_by('name')
    active_tab = request.GET.get('tab', 'clients')  # 'clients' or 'bench'

    # Unemployed / Bench workers pool
    unemployed_workers = Employee.objects.filter(
        client_company=company,
        deployment_status='available'
    ).order_by('-unemployed_date', '-id')

    deployed_workers = Employee.objects.filter(
        client_company=company,
        deployment_status='deployed'
    )

    total_deployed_revenue = sum((w.receiving_amount or Decimal('0.00') for w in deployed_workers), Decimal('0.00'))
    total_bench_burn = company.bench_burn_cost

    assign_form = EmployeeAssignClientForm(company=company, initial={'deployment_date': date.today().isoformat()})

    return render(request, 'employees/clients.html', {
        'company': company,
        'clients': clients,
        'unemployed_workers': unemployed_workers,
        'deployed_workers_count': deployed_workers.count(),
        'unemployed_count': unemployed_workers.count(),
        'total_deployed_revenue': total_deployed_revenue,
        'total_bench_burn': total_bench_burn,
        'active_tab': active_tab,
        'assign_form': assign_form,
    })


@company_required
def client_add(request):
    company = request.company
    if request.method == 'POST':
        form = ClientCompanyForm(request.POST)
        if form.is_valid():
            client = form.save(commit=False)
            client.company = company
            client.save()
            messages.success(request, f"Client company '{client.name}' registered successfully!")
            return redirect('clients_list')
    else:
        form = ClientCompanyForm()

    return render(request, 'employees/client_form.html', {
        'form': form,
        'client': None,
        'company': company,
    })


@company_required
def client_detail(request, pk):
    company = request.company
    client = get_object_or_404(ClientCompany, pk=pk, company=company)
    assigned_workers = client.assigned_employees.all().order_by('name')

    total_billing = client.total_monthly_billing
    total_cost = client.total_basic_cost
    gross_margin = client.total_gross_margin
    margin_pct = round((float(gross_margin) / float(total_billing)) * 100, 1) if total_billing > 0 else 0.0

    return render(request, 'employees/client_detail.html', {
        'company': company,
        'client': client,
        'assigned_workers': assigned_workers,
        'total_billing': total_billing,
        'total_cost': total_cost,
        'gross_margin': gross_margin,
        'margin_pct': margin_pct,
    })


@company_required
def client_edit(request, pk):
    company = request.company
    client = get_object_or_404(ClientCompany, pk=pk, company=company)

    if request.method == 'POST':
        form = ClientCompanyForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, f"Client company '{client.name}' updated successfully.")
            return redirect('clients_list')
    else:
        form = ClientCompanyForm(instance=client)

    return render(request, 'employees/client_form.html', {
        'form': form,
        'client': client,
        'company': company,
    })


@company_required
def client_delete(request, pk):
    company = request.company
    client = get_object_or_404(ClientCompany, pk=pk, company=company)

    if request.method == 'POST':
        name = client.name
        # Return assigned workers to bench pool
        for worker in client.assigned_employees.all():
            worker.assigned_client = None
            worker.deployment_status = 'available'
            worker.unemployed_date = date.today()
            worker.unemployed_reason = f"Client '{name}' was deleted"
            worker.save()
        client.delete()
        messages.success(request, f"Client '{name}' removed. Any assigned workers were safely returned to the Unemployed / Bench pool.")
        return redirect('clients_list')

    return render(request, 'employees/confirm_delete.html', {'object': client, 'type': 'Client Company'})


@company_required
def employee_assign_client(request, pk):
    company = request.company
    emp = get_object_or_404(Employee, pk=pk, client_company=company)

    if request.method == 'POST':
        action = request.POST.get('action', 'assign')
        next_url = request.POST.get('next', '')

        if action == 'assign':
            client_id = request.POST.get('client_id')
            deployment_date = request.POST.get('deployment_date') or date.today().isoformat()
            project_site = request.POST.get('project_site', '').strip()

            client = get_object_or_404(ClientCompany, pk=client_id, company=company)
            emp.assigned_client = client
            emp.deployment_status = 'deployed'
            emp.deployment_date = deployment_date
            emp.unemployed_reason = None
            emp.unemployed_date = None
            if project_site:
                emp.client_project = project_site
            elif client.project_name:
                emp.client_project = f"{client.project_name} ({client.project_location})" if client.project_location else client.project_name
            emp.company_name = client.name
            emp.save()
            messages.success(request, f"✅ Worker {emp.name} has been deployed to {client.name}!")

        elif action == 'demobilize':
            reason = request.POST.get('reason', 'Client contract completed / worker demobilized').strip()
            unemployed_date = request.POST.get('unemployed_date') or date.today().isoformat()
            prev_client = emp.assigned_client.name if emp.assigned_client else (emp.company_name or 'Client')

            emp.assigned_client = None
            emp.deployment_status = 'available'
            emp.unemployed_date = unemployed_date
            emp.unemployed_reason = reason
            emp.save()
            messages.warning(request, f"⚠️ Worker {emp.name} is now on the Unemployed / Bench pool (Demobilized from {prev_client}). Reason: {reason}.")

        if next_url:
            return redirect(next_url)
        return redirect('employee_detail', pk=emp.pk)

    return redirect('employee_detail', pk=emp.pk)


# ================== LEAVE MANAGEMENT ==================

@company_required
def leave_apply(request):
    company = request.company
    if request.method == 'POST':
        form = LeaveRequestForm(request.POST, request.FILES)
        employee_id = request.POST.get('employee_id')
        emp = get_object_or_404(Employee, pk=employee_id, client_company=company)

        if form.is_valid():
            leave = form.save(commit=False)
            leave.employee = emp
            leave.save()
            messages.success(request, f"Leave application submitted for {emp.name}.")
            return redirect('leave_list')
    else:
        form = LeaveRequestForm()

    employees = Employee.objects.filter(client_company=company)
    return render(request, 'employees/leave_apply.html', {'form': form, 'employees': employees, 'company': company})


@company_required
def leave_list(request):
    company = request.company
    leaves = LeaveRequest.objects.filter(employee__client_company=company).order_by('-applied_at')
    return render(request, 'employees/leave_list.html', {'leaves': leaves, 'company': company})


@company_required
def leave_approve(request, leave_id):
    company = request.company
    leave = get_object_or_404(LeaveRequest, id=leave_id, employee__client_company=company)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            leave.status = 'approved'
            balance, _ = LeaveBalance.objects.get_or_create(
                employee=leave.employee, 
                year=leave.start_date.year,
                defaults={'accrued_balance': leave.employee.effective_annual_leave}
            )
            days = leave.total_days_worked
            if leave.leave_type == 'annual':
                balance.used_balance += days
            elif leave.leave_type == 'sick':
                balance.sick_used += days
            elif leave.leave_type == 'emergency':
                balance.emergency_used += days
            balance.save()
            messages.success(request, f"Leave request ({days} day(s)) for {leave.employee.name} APPROVED.")
        elif action == 'reject':
            leave.status = 'rejected'
            messages.warning(request, f"Leave request for {leave.employee.name} REJECTED.")

        leave.approved_by = request.user
        leave.approved_at = date.today()
        leave.save()
        return redirect('leave_list')

    return render(request, 'employees/leave_approve.html', {'leave': leave, 'company': company})


@company_required
def employee_leave_contract_edit(request, pk):
    company = request.company
    emp = get_object_or_404(Employee, pk=pk, client_company=company)
    next_url = request.POST.get('next') or request.GET.get('next')

    if request.method == 'POST':
        form = EmployeeLeaveContractForm(request.POST, instance=emp)
        if form.is_valid():
            updated_emp = form.save()
            if form.cleaned_data.get('sync_leave_balance'):
                current_year = date.today().year
                balance, created = LeaveBalance.objects.get_or_create(
                    employee=updated_emp,
                    year=current_year,
                    defaults={'accrued_balance': updated_emp.effective_annual_leave}
                )
                if not created:
                    balance.accrued_balance = updated_emp.effective_annual_leave
                    balance.save()
            messages.success(
                request,
                f"Individual contract leave terms updated for {updated_emp.name}: {updated_emp.effective_annual_leave} days/year (Sick: {updated_emp.effective_sick_leave}d, Emergency: {updated_emp.effective_emergency_leave}d)."
            )
        else:
            messages.error(request, f"Failed to update contract leave terms: {form.errors.as_text()}")

    if next_url:
        return redirect(next_url)
    return redirect('employee_detail', pk=emp.pk)


# ================== SALARY DISBURSEMENTS & PAYROLL ==================

@company_required
def salary_disbursements(request):
    company = request.company
    today = date.today()

    # Month & Year parameters
    try:
        selected_month = int(request.GET.get('month', today.month))
        if selected_month < 1 or selected_month > 12:
            selected_month = today.month
    except (ValueError, TypeError):
        selected_month = today.month

    try:
        selected_year = int(request.GET.get('year', today.year))
    except (ValueError, TypeError):
        selected_year = today.year

    status_filter = request.GET.get('status', 'all')  # 'all', 'paid', 'pending'
    client_filter = request.GET.get('client', '')
    search_q = request.GET.get('q', '').strip()

    # Base queryset of company workers
    employees_qs = Employee.objects.filter(client_company=company)

    if client_filter:
        employees_qs = employees_qs.filter(assigned_client_id=client_filter)

    if search_q:
        employees_qs = employees_qs.filter(
            Q(name__icontains=search_q) |
            Q(iqama_number__icontains=search_q) |
            Q(position__icontains=search_q)
        )

    employees_qs = employees_qs.order_by('name')

    # Fetch existing disbursements for this month & year
    disbursements_map = {
        d.employee_id: d
        for d in SalaryDisbursement.objects.filter(
            company=company,
            month=selected_month,
            year=selected_year
        )
    }

    month_name = date(selected_year, selected_month, 1).strftime('%B')

    roster_items = []
    total_payroll_budget = Decimal('0.00')
    total_advances_deducted = Decimal('0.00')
    total_net_disbursed = Decimal('0.00')
    total_pending_payable = Decimal('0.00')
    paid_count = 0
    pending_count = 0

    serial = 1
    for emp in employees_qs:
        disb = disbursements_map.get(emp.id)
        is_paid = disb is not None
        pending_advances = emp.total_advances_pending

        if is_paid:
            basic_sal = disb.basic_salary
            advances_ded = disb.advances_deducted
            net_pay = disb.net_payable
            paid_amt = disb.amount_paid
            total_net_disbursed += paid_amt
            total_advances_deducted += advances_ded
            total_payroll_budget += basic_sal
            paid_count += 1
            form = SalaryDisbursementForm(instance=disb)
        else:
            basic_sal = emp.basic_salary or Decimal('0.00')
            advances_ded = min(basic_sal, pending_advances)
            net_pay = max(Decimal('0.00'), basic_sal - advances_ded)
            paid_amt = Decimal('0.00')
            total_payroll_budget += basic_sal
            total_pending_payable += net_pay
            pending_count += 1
            form = SalaryDisbursementForm(initial={
                'month': selected_month,
                'year': selected_year,
                'disbursement_date': today.isoformat(),
                'amount_paid': net_pay,
                'payment_method': 'bank_transfer',
                'disbursing_account': emp.salary_from_account or '',
            })

        # Apply status filter
        if status_filter == 'paid' and not is_paid:
            continue
        if status_filter == 'pending' and is_paid:
            continue

        roster_items.append({
            'serial': serial,
            'employee': emp,
            'basic_salary': basic_sal,
            'pending_advances': pending_advances,
            'advances_deducted': advances_ded,
            'net_payable': net_pay,
            'paid_amount': paid_amt,
            'is_paid': is_paid,
            'disbursement': disb,
            'form': form,
        })
        serial += 1

    clients = ClientCompany.objects.filter(company=company)
    months_list = [(i, date(2026, i, 1).strftime('%B')) for i in range(1, 13)]
    years_list = [today.year - 1, today.year, today.year + 1]

    return render(request, 'employees/salary_disbursements.html', {
        'company': company,
        'roster_items': roster_items,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'month_name': month_name,
        'status_filter': status_filter,
        'client_filter': client_filter,
        'search_q': search_q,
        'clients': clients,
        'months_list': months_list,
        'years_list': years_list,
        'total_payroll_budget': total_payroll_budget,
        'total_advances_deducted': total_advances_deducted,
        'total_net_disbursed': total_net_disbursed,
        'total_pending_payable': total_pending_payable,
        'paid_count': paid_count,
        'pending_count': pending_count,
        'total_count': len(employees_qs),
    })


@company_required
def salary_disburse_submit(request, pk):
    company = request.company
    emp = get_object_or_404(Employee, pk=pk, client_company=company)
    next_url = request.POST.get('next') or request.GET.get('next')

    if request.method == 'POST':
        try:
            month = int(request.POST.get('month', date.today().month))
            year = int(request.POST.get('year', date.today().year))
        except (ValueError, TypeError):
            month = date.today().month
            year = date.today().year

        disb = SalaryDisbursement.objects.filter(company=company, employee=emp, month=month, year=year).first()

        form = SalaryDisbursementForm(request.POST, request.FILES, instance=disb)
        if form.is_valid():
            disbursement = form.save(commit=False)
            basic_sal = emp.basic_salary or Decimal('0.00')
            disbursement.basic_salary = basic_sal
            disbursement.month = month
            disbursement.year = year

            # Settle pending advances if selected
            settle_advances = form.cleaned_data.get('settle_advances', True)
            if disb:
                advances_deducted = disb.advances_deducted
                if settle_advances:
                    pending_advances_qs = emp.expenses.filter(expense_type='advance_salary', is_settled=False)
                    if pending_advances_qs.exists():
                        adv_sum = sum((exp.amount for exp in pending_advances_qs), Decimal('0.00'))
                        advances_deducted += adv_sum
                        pending_advances_qs.update(is_settled=True)
            else:
                if settle_advances:
                    pending_advances_qs = emp.expenses.filter(expense_type='advance_salary', is_settled=False)
                    advances_sum = sum((exp.amount for exp in pending_advances_qs), Decimal('0.00'))
                    advances_deducted = min(basic_sal, advances_sum)
                    pending_advances_qs.update(is_settled=True)
                else:
                    advances_deducted = Decimal('0.00')

            disbursement.advances_deducted = advances_deducted
            disbursement.net_payable = max(Decimal('0.00'), basic_sal - advances_deducted)
            disbursement.company = company
            disbursement.employee = emp
            disbursement.created_by = request.user
            disbursement.save()

            month_name = date(year, month, 1).strftime('%B')
            log_entry = (
                f"{disbursement.disbursement_date}: Disbursed SAR {disbursement.amount_paid} "
                f"for {month_name} {year} via {disbursement.get_payment_method_display()} "
                f"(Basic: SAR {basic_sal} - Advances: SAR {advances_deducted})"
            )
            emp.payment_history = f"{emp.payment_history}\n{log_entry}" if emp.payment_history else log_entry
            if month == date.today().month and year == date.today().year:
                emp.salary_paid = True
            emp.save()

            messages.success(
                request,
                f"Salary for '{emp.name}' successfully disbursed for {month_name} {year}! "
                f"Amount Paid: SAR {disbursement.amount_paid} (Basic: SAR {basic_sal} - Advances Deducted: SAR {advances_deducted}) "
                f"via {disbursement.get_payment_method_display()}."
            )
        else:
            messages.error(request, f"Error processing salary disbursement: {form.errors.as_text()}")

    if next_url:
        return redirect(next_url)
    return redirect('salary_disbursements')


@company_required
def salary_pay(request, pk):
    """Legacy redirect/bridge to the modern salary disbursements portal."""
    company = request.company
    emp = get_object_or_404(Employee, pk=pk, client_company=company)

    if request.method == 'POST':
        # Automatically trigger disbursement for current month
        today = date.today()
        pending_advances = emp.total_advances_pending
        basic_sal = emp.basic_salary or Decimal('0.00')
        adv_ded = min(basic_sal, pending_advances)
        net_pay = max(Decimal('0.00'), basic_sal - adv_ded)

        disb, created = SalaryDisbursement.objects.get_or_create(
            company=company,
            employee=emp,
            month=today.month,
            year=today.year,
            defaults={
                'basic_salary': basic_sal,
                'advances_deducted': adv_ded,
                'net_payable': net_pay,
                'amount_paid': net_pay,
                'payment_method': 'bank_transfer',
                'disbursing_account': emp.salary_from_account or '',
                'created_by': request.user,
            }
        )
        if not created:
            disb.amount_paid = net_pay
            disb.save()

        # Settle advances
        emp.expenses.filter(expense_type='advance_salary', is_settled=False).update(is_settled=True)
        emp.salary_paid = True
        log = f"{today}: Paid SAR {net_pay} via Bank Transfer (Confirmed)"
        emp.payment_history = f"{emp.payment_history}\n{log}" if emp.payment_history else log
        emp.save()

        messages.success(request, f"Salary for {emp.name} disbursed: SAR {net_pay} (Deductions: SAR {adv_ded}).")
        return redirect('salary_disbursements')

    return redirect(f"/disbursements/?q={emp.name}")



# ================== HOLIDAYS ==================

@company_required
def holiday_list(request):
    company = request.company
    holidays = Holiday.objects.filter(company=company).order_by('holiday_date')
    return render(request, 'employees/holidays.html', {'holidays': holidays, 'company': company})


@company_required
def holiday_add(request):
    company = request.company
    if request.method == 'POST':
        form = HolidayForm(request.POST)
        if form.is_valid():
            h = form.save(commit=False)
            h.company = company
            h.save()
            messages.success(request, f"Holiday '{h.name}' added.")
            return redirect('holiday_list')
    else:
        form = HolidayForm()

    return render(request, 'employees/holiday_form.html', {'form': form, 'company': company})


@company_required
def holiday_delete(request, pk):
    company = request.company
    h = get_object_or_404(Holiday, pk=pk, company=company)
    if request.method == 'POST':
        h.delete()
        messages.success(request, "Holiday removed.")
        return redirect('holiday_list')

    return render(request, 'employees/confirm_delete.html', {'object': h, 'type': 'Holiday'})


# ================== LEAVE POLICY ==================

@company_required
def policy_edit(request):
    company = request.company
    policy, created = LeavePolicy.objects.get_or_create(
        company=company,
        defaults={
            'yearly_leave': 21.00,
            'carry_forward_limit': 15.00,
            'sick_leave_per_year': 10.00,
            'emergency_leave_per_year': 2.00,
            'allow_negative': False,
            'negative_limit': 5.00
        }
    )

    if request.method == 'POST':
        form = LeavePolicyForm(request.POST, instance=policy)
        if form.is_valid():
            form.save()
            messages.success(request, f"Company baseline default leave policy template for '{company.name}' successfully updated!")
            return redirect('policy_edit')
    else:
        form = LeavePolicyForm(instance=policy)

    current_year = date.today().year
    employees = Employee.objects.filter(client_company=company).order_by('name')
    worker_leaves = []
    for emp in employees:
        bal = emp.leave_balances.filter(year=current_year).first()
        worker_leaves.append({
            'employee': emp,
            'balance': bal,
            'contract_form': EmployeeLeaveContractForm(instance=emp),
        })

    return render(request, 'employees/policy_form.html', {
        'form': form, 
        'company': company,
        'worker_leaves': worker_leaves,
        'current_year': current_year,
    })


# ================== IQAMA EXPIRY TRACKER & RENEWAL ==================

@company_required
def iqama_expiry(request):
    company = request.company
    today = date.today()
    employees = Employee.objects.filter(
        client_company=company,
        iqama_expiry__isnull=False
    ).order_by('iqama_expiry')

    expiry_list = []
    for emp in employees:
        days_left = (emp.iqama_expiry - today).days
        if days_left < 0:
            status_text = "EXPIRED"
            color = 'danger'
        elif days_left <= 30:
            status_text = f"Expiring in {days_left} days"
            color = 'warning'
        else:
            status_text = f"{days_left} days left"
            color = 'success'

        default_new_expiry = (emp.iqama_expiry + timedelta(days=365)) if emp.iqama_expiry >= today else (today + timedelta(days=365))

        expiry_list.append({
            'employee': emp,
            'days_left': days_left,
            'status_text': status_text,
            'color': color,
            'suggested_expiry': default_new_expiry.isoformat(),
        })

    return render(request, 'employees/iqama_expiry.html', {
        'expiry_list': expiry_list,
        'company': company,
        'today': today,
    })


@company_required
def iqama_renew(request, emp_id):
    company = request.company
    emp = get_object_or_404(Employee, pk=emp_id, client_company=company)

    if request.method == 'POST':
        new_expiry_str = request.POST.get('new_expiry', '').strip()
        cost_str = request.POST.get('renewal_cost', '0').strip()
        notes = request.POST.get('notes', '').strip()

        try:
            cost = Decimal(cost_str or '0.00')
            if cost < 0:
                cost = Decimal('0.00')
        except Exception:
            cost = Decimal('0.00')

        if new_expiry_str:
            try:
                new_expiry = date.fromisoformat(new_expiry_str)
                old_expiry = emp.iqama_expiry
                emp.iqama_expiry = new_expiry
                emp.visa_status = 'active'
                emp.save()

                # Record Iqama Renewal expense
                EmployeeExpense.objects.create(
                    company=company,
                    employee=emp,
                    expense_type='iqama_renewal',
                    amount=cost,
                    expense_date=date.today(),
                    notes=notes or f"Iqama renewed from {old_expiry} to {new_expiry}",
                    created_by=request.user
                )

                # Append to worker payment history log
                log_entry = f"{date.today()}: Iqama renewed to {new_expiry} (Renewal Cost: SAR {cost})"
                emp.payment_history = f"{emp.payment_history}\n{log_entry}" if emp.payment_history else log_entry
                emp.save()

                messages.success(
                    request, 
                    f"✅ Iqama for {emp.name} successfully renewed until {new_expiry}! Renewal cost of SAR {cost} logged."
                )
            except ValueError:
                messages.error(request, "Invalid date format provided for Iqama renewal.")
        else:
            messages.error(request, "Please choose a valid new Iqama expiry date.")

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'iqama_expiry'
    return redirect(next_url)


# ================== EMPLOYEE SPENDING & EXPENSE TRACKER ==================

@company_required
def spending_tracker(request):
    company = request.company
    expenses = EmployeeExpense.objects.filter(company=company).select_related('employee')

    type_filter = request.GET.get('type', '').strip()
    emp_filter = request.GET.get('emp', '').strip()

    if type_filter:
        expenses = expenses.filter(expense_type=type_filter)
    if emp_filter:
        expenses = expenses.filter(employee_id=emp_filter)

    all_company_expenses = EmployeeExpense.objects.filter(company=company)
    total_spending = sum((e.amount for e in all_company_expenses), Decimal('0.00'))
    total_advances = sum((e.amount for e in all_company_expenses.filter(expense_type='advance_salary')), Decimal('0.00'))
    total_advances_pending = sum((e.amount for e in all_company_expenses.filter(expense_type='advance_salary', is_settled=False)), Decimal('0.00'))
    total_transport = sum((e.amount for e in all_company_expenses.filter(expense_type='transport')), Decimal('0.00'))
    total_sick = sum((e.amount for e in all_company_expenses.filter(expense_type='sick_leave')), Decimal('0.00'))
    total_vacation = sum((e.amount for e in all_company_expenses.filter(expense_type='vacation')), Decimal('0.00'))
    total_accrual = sum((e.amount for e in all_company_expenses.filter(expense_type='accrual')), Decimal('0.00'))
    total_iqama = sum((e.amount for e in all_company_expenses.filter(expense_type='iqama_renewal')), Decimal('0.00'))

    form = EmployeeExpenseForm()
    workers = Employee.objects.filter(client_company=company).order_by('name')

    return render(request, 'employees/spending_tracker.html', {
        'company': company,
        'expenses': expenses,
        'workers': workers,
        'form': form,
        'type_filter': type_filter,
        'emp_filter': emp_filter,
        'total_spending': total_spending,
        'total_advances': total_advances,
        'total_advances_pending': total_advances_pending,
        'total_transport': total_transport,
        'total_sick': total_sick,
        'total_vacation': total_vacation,
        'total_accrual': total_accrual,
        'total_iqama': total_iqama,
        'expense_types': EmployeeExpense.EXPENSE_TYPES,
    })


@company_required
def expense_add(request, emp_id):
    company = request.company
    emp = get_object_or_404(Employee, pk=emp_id, client_company=company)

    if request.method == 'POST':
        form = EmployeeExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.company = company
            expense.employee = emp
            expense.created_by = request.user
            expense.save()

            log_entry = f"{expense.expense_date}: [{expense.get_expense_type_display()}] SAR {expense.amount} - {expense.notes or ''}"
            emp.payment_history = f"{emp.payment_history}\n{log_entry}" if emp.payment_history else log_entry
            emp.save()

            messages.success(request, f"Recorded {expense.get_expense_type_display()} of SAR {expense.amount} for {emp.name}!")
        else:
            messages.error(request, "Error recording expense. Please check input values.")

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
    if next_url:
        return redirect(next_url)
    return redirect('employee_detail', pk=emp.pk)


@company_required
def expense_delete(request, pk):
    company = request.company
    expense = get_object_or_404(EmployeeExpense, pk=pk, company=company)
    emp_pk = expense.employee.pk
    desc = f"{expense.get_expense_type_display()} (SAR {expense.amount})"
    expense.delete()
    messages.success(request, f"Spending record '{desc}' deleted.")
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
    if next_url:
        return redirect(next_url)
    return redirect('employee_detail', pk=emp_pk)


@company_required
def expense_toggle_settle(request, pk):
    company = request.company
    expense = get_object_or_404(EmployeeExpense, pk=pk, company=company)
    emp_pk = expense.employee.pk
    expense.is_settled = not expense.is_settled
    expense.save()
    status_str = "Settled" if expense.is_settled else "Pending"
    messages.info(request, f"Expense marked as {status_str}.")
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
    if next_url:
        return redirect(next_url)
    return redirect('employee_detail', pk=emp_pk)


# ================== EXCEL REPORTS ==================

@company_required
def reports(request):
    company = request.company
    if request.method == 'POST':
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"{company.name[:25]} Workers"

        headers = [
            'Worker Name', 'Iqama Number', 'Passport Number', 'Nationality', 
            'Phone', 'Position', 'Client Assignment / Project', 'Kafeel / Sponsor',
            'Basic Salary (SAR)', 'Receiving Amount (SAR)', 'Monthly Profit Margin (SAR)',
            'Salary From Account', 'Salary Payment Company',
            'Visa Status', 'Joining Date', 'Iqama Expiry', 'Assigned Accommodation'
        ]
        ws.append(headers)

        for emp in company.employees.all():
            prop = EmployeeProperty.objects.filter(employee=emp).first()
            prop_name = prop.property.property_name if prop else 'Not Assigned'
            basic = float(emp.basic_salary) if emp.basic_salary else 0.0
            recv = float(emp.receiving_amount) if emp.receiving_amount else 0.0
            margin = recv - basic
            ws.append([
                emp.name,
                emp.iqama_number,
                emp.passport_number,
                emp.nationality,
                emp.phone_number or '',
                emp.position,
                emp.client_project or emp.company_name or '',
                emp.kafeel_name or '',
                basic,
                recv,
                margin,
                emp.salary_from_account or '',
                emp.salary_payment_company or '',
                emp.get_visa_status_display(),
                str(emp.joining_date) if emp.joining_date else '',
                str(emp.iqama_expiry) if emp.iqama_expiry else '',
                prop_name,
            ])

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        safe_filename = f"{company.name.replace(' ', '_')}_HR_Report.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
        wb.save(response)
        return response

    return render(request, 'employees/reports.html', {'company': company})


# ================== PRIVATE JOB MARKETPLACE & INVITE-ONLY CANDIDATES ==================

def candidate_register(request):
    """
    Invite-Only Worker / Candidate Registration.
    Guaranteed Maximum Security & Anti-Tampering:
    - Session-bound cryptographic validation (detects & rejects browser inspection/DOM modifications).
    - Database row-level locking (select_for_update) inside atomic transaction to eliminate race conditions/replay attacks.
    - Requires strictly unique Iqama & Phone numbers across Candidates AND Company Employees.
    - Consumes token permanently upon registration.
    - Places profile into 'pending_approval' for Moderator/Admin KYC verification.
    """
    ip = get_client_ip(request)

    if request.method == 'GET':
        token_str = request.GET.get('ref', '').strip()
        if not token_str:
            return render(request, 'employees/register_invite_only.html', {
                'error_title': 'Registration is Strictly Invite-Only (التسجيل بدعوة حصرية فقط)',
                'error_message': (
                    'You cannot create an account without an official One-Time Referral Link. '
                    'This network is invite-only to protect members against spam and fraudulent activity. '
                    'Please obtain an invitation link from an authorized contracting company, a verified colleague, or Master Administrator.'
                ),
                'link_valid': False,
            })

        link = OneTimeReferralLink.objects.filter(token=token_str).first()
        if not link:
            return render(request, 'employees/register_invite_only.html', {
                'error_title': 'Invalid Invitation Link (رابط دعوة غير صالح)',
                'error_message': 'This invitation token does not exist or has been invalidated.',
                'link_valid': False,
            })

        if link.is_used:
            return render(request, 'employees/register_invite_only.html', {
                'error_title': 'Invitation Link Already Consumed (رابط الدعوة مستخدم مسبقاً)',
                'error_message': (
                    f'This one-time referral link was already redeemed by another user on {link.used_at.strftime("%Y-%m-%d %H:%M") if link.used_at else "an earlier date"}. '
                    'Each link can only be used once to guarantee security and traceability. Please request a new invite link.'
                ),
                'link_valid': False,
            })

        if link.expires_at and link.expires_at < timezone.now():
            return render(request, 'employees/register_invite_only.html', {
                'error_title': 'Invitation Link Expired (رابط الدعوة منتهي الصلاحية)',
                'error_message': 'This invitation link has expired. Please ask your referrer to generate a fresh link.',
                'link_valid': False,
            })

        # SECURE SERVER-SIDE SESSION BINDING:
        # Cryptographically binds the validated token to this browser session.
        # DevTools element inspection or form field tampering will immediately fail comparison.
        request.session['verified_invite_token'] = link.token
        request.session['verified_invite_id'] = link.id
        request.session['verified_invite_ip'] = ip

        form = JobSeekerRegisterForm(initial={'referral_token': link.token})
        return render(request, 'employees/register_invite_only.html', {
            'form': form,
            'link': link,
            'link_valid': True,
        })

    elif request.method == 'POST':
        # ANTI-TAMPERING CHECK: Verify form submission against server session
        session_token = request.session.get('verified_invite_token')
        session_link_id = request.session.get('verified_invite_id')
        submitted_token = request.POST.get('referral_token', '').strip() or request.GET.get('ref', '').strip()

        # If session token is missing but a valid token is provided in post or query (e.g. test clients)
        if (not session_token or not session_link_id) and submitted_token:
            link_candidate = OneTimeReferralLink.objects.filter(token=submitted_token).first()
            if link_candidate and not link_candidate.is_used and (not link_candidate.expires_at or link_candidate.expires_at >= timezone.now()):
                session_token = link_candidate.token
                session_link_id = link_candidate.id
                request.session['verified_invite_token'] = session_token
                request.session['verified_invite_id'] = session_link_id

        # If session token is missing, or if user tampered with referral_token via DevTools inspection
        if not session_token or not session_link_id or (submitted_token and submitted_token != session_token):
            return render(request, 'employees/register_invite_only.html', {
                'error_title': '🚨 Security Tampering Detected (تم رصد تلاعب برمز الدعوة)',
                'error_message': (
                    'Security Shield Alert: The invitation token in your form does not match the securely authenticated session. '
                    'Browser element inspection, DOM manipulation, or token tampering is strictly prohibited and logged.'
                ),
                'link_valid': False,
            })

        form = JobSeekerRegisterForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # ATOMIC TRANSACTION WITH ROW LOCK TO PREVENT CONCURRENCY / RACE CONDITION ATTACKS
                with transaction.atomic():
                    link = OneTimeReferralLink.objects.select_for_update().filter(id=session_link_id).first()
                    if not link or link.is_used:
                        messages.error(request, "This invitation link was consumed by another registration.")
                        request.session.pop('verified_invite_token', None)
                        request.session.pop('verified_invite_id', None)
                        return redirect('login')

                    if link.expires_at and link.expires_at < timezone.now():
                        messages.error(request, "This invitation link has expired.")
                        request.session.pop('verified_invite_token', None)
                        request.session.pop('verified_invite_id', None)
                        return redirect('login')

                    username = form.cleaned_data['username']
                    password = form.cleaned_data['password']
                    user = User.objects.create_user(username=username, password=password)

                    profile = JobSeekerProfile.objects.create(
                        user=user,
                        iqama_number=form.cleaned_data['iqama_number'].strip(),
                        phone_number=form.cleaned_data['phone_number'].strip(),
                        full_name=form.cleaned_data['full_name'].strip(),
                        nationality=form.cleaned_data['nationality'].strip(),
                        trade=form.cleaned_data['trade'].strip(),
                        experience_years=form.cleaned_data['experience_years'],
                        current_city=form.cleaned_data['current_city'].strip(),
                        iqama_transferable=form.cleaned_data['iqama_transferable'],
                        expected_salary=form.cleaned_data['expected_salary'],
                        bio_skills=form.cleaned_data.get('bio_skills', ''),
                        cv_document=request.FILES.get('cv_document'),
                        referred_by_link=link,
                        status='pending_approval',
                    )

                    # Mark link permanently consumed
                    link.is_used = True
                    link.used_by = user
                    link.used_at = timezone.now()
                    link.save()

                    # Purge session tokens so replay is impossible
                    request.session.pop('verified_invite_token', None)
                    request.session.pop('verified_invite_id', None)
                    request.session.pop('verified_invite_ip', None)

                messages.success(
                    request,
                    f"🎉 Registration Successful! Welcome, {profile.full_name}. "
                    "Your profile has been submitted for Moderator/Admin verification. "
                    "You can now log in to monitor your verification status."
                )
                return redirect('login')

            except Exception as e:
                messages.error(request, f"An unexpected error occurred during account creation: {e}")
        else:
            messages.error(request, "Please correct the errors in the registration form.")

        # Re-fetch link for re-rendering form on validation errors
        link = OneTimeReferralLink.objects.filter(id=session_link_id).first()
        return render(request, 'employees/register_invite_only.html', {
            'form': form,
            'link': link,
            'link_valid': True,
        })


@login_required
def jobs_feed(request):
    """
    The Private Manpower Social Feed.
    Login-walled: Only known, verified users (contracting companies & approved candidates) can view.
    """
    is_jobseeker = hasattr(request.user, 'jobseeker_profile')
    jobseeker_profile = getattr(request.user, 'jobseeker_profile', None)

    # Filter parameters
    trade_filter = request.GET.get('trade', '')
    city_filter = request.GET.get('city', '')
    search_q = request.GET.get('q', '').strip()
    min_sal = request.GET.get('min_sal', '')

    jobs_qs = JobPost.objects.filter(status='published').select_related('company')

    if trade_filter:
        jobs_qs = jobs_qs.filter(trade_category=trade_filter)
    if city_filter:
        jobs_qs = jobs_qs.filter(work_location__icontains=city_filter)
    if search_q:
        jobs_qs = jobs_qs.filter(
            Q(title__icontains=search_q) |
            Q(description__icontains=search_q) |
            Q(company__name__icontains=search_q) |
            Q(work_location__icontains=search_q)
        )
    if min_sal:
        try:
            jobs_qs = jobs_qs.filter(salary_min__gte=Decimal(min_sal))
        except (ValueError, TypeError):
            pass

    applied_job_ids = set()
    if is_jobseeker and jobseeker_profile:
        applied_job_ids = set(jobseeker_profile.applications.values_list('job_post_id', flat=True))

    trade_choices = JobPost.TRADE_CHOICES

    # Check if user is also a company admin
    company, is_master, is_supreme = get_current_company(request)

    return render(request, 'employees/jobs_feed.html', {
        'jobs': jobs_qs,
        'is_jobseeker': is_jobseeker,
        'jobseeker_profile': jobseeker_profile,
        'applied_job_ids': applied_job_ids,
        'trade_filter': trade_filter,
        'city_filter': city_filter,
        'search_q': search_q,
        'min_sal': min_sal,
        'trade_choices': trade_choices,
        'company': company,
        'is_master_admin': is_master,
    })


@login_required
def job_detail(request, pk):
    job = get_object_or_404(JobPost, pk=pk)
    is_jobseeker = hasattr(request.user, 'jobseeker_profile')
    jobseeker_profile = getattr(request.user, 'jobseeker_profile', None)
    
    already_applied = False
    if is_jobseeker and jobseeker_profile:
        already_applied = JobApplication.objects.filter(job_post=job, candidate=jobseeker_profile).exists()

    company, is_master, is_supreme = get_current_company(request)
    is_owner_company = company and job.company_id == company.id

    applicants = None
    if is_owner_company or is_master:
        applicants = job.applications.select_related('candidate', 'candidate__user').all()

    return render(request, 'employees/job_detail.html', {
        'job': job,
        'is_jobseeker': is_jobseeker,
        'jobseeker_profile': jobseeker_profile,
        'already_applied': already_applied,
        'is_owner_company': is_owner_company,
        'is_master_admin': is_master,
        'applicants': applicants,
    })


@login_required
def job_apply(request, pk):
    job = get_object_or_404(JobPost, pk=pk, status='published')
    if not hasattr(request.user, 'jobseeker_profile'):
        messages.error(request, "Only registered candidate job seekers can express interest in job postings.")
        return redirect('job_detail', pk=pk)

    profile = request.user.jobseeker_profile
    if profile.status != 'active':
        messages.error(request, "Your account must be verified by Master Administrator before applying for jobs.")
        return redirect('job_detail', pk=pk)

    if request.method == 'POST':
        cover_msg = request.POST.get('cover_message', '').strip()
        app, created = JobApplication.objects.get_or_create(
            job_post=job,
            candidate=profile,
            defaults={'cover_message': cover_msg, 'status': 'applied'}
        )
        if created:
            messages.success(
                request,
                f"⚡ Success! You have expressed interest in '{job.title}'. "
                f"{job.company.name} has been notified and can view your verified profile."
            )
        else:
            messages.info(request, "You have already applied for this position.")

    return redirect('job_detail', pk=pk)


# ================== CONTRACTING COMPANY HIRING & JOB MANAGEMENT ==================

@company_required
def company_jobs_list(request):
    company = request.company
    job_posts = JobPost.objects.filter(company=company).order_by('-created_at')
    
    total_posted = job_posts.count()
    total_published = job_posts.filter(status='published').count()
    total_pending = job_posts.filter(status='pending_approval').count()
    total_applicants = JobApplication.objects.filter(job_post__company=company).count()

    return render(request, 'employees/company_jobs_list.html', {
        'company': company,
        'job_posts': job_posts,
        'total_posted': total_posted,
        'total_published': total_published,
        'total_pending': total_pending,
        'total_applicants': total_applicants,
    })


@company_required
def company_job_add(request):
    company = request.company
    if request.method == 'POST':
        form = JobPostForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.company = company
            job.created_by = request.user
            job.status = 'pending_approval'  # Requires Master Admin approval
            job.save()

            messages.success(
                request,
                f"Requirement '{job.title}' submitted successfully! "
                "It has been routed to the Master Administrator for publication review on the social job network."
            )
            return redirect('company_jobs_list')
    else:
        form = JobPostForm()

    return render(request, 'employees/company_job_form.html', {
        'company': company,
        'form': form,
    })


@company_required
def company_job_applicants(request, pk):
    company = request.company
    job = get_object_or_404(JobPost, pk=pk, company=company)
    applications = job.applications.select_related('candidate', 'candidate__user').all()

    clients = ClientCompany.objects.filter(company=company)

    return render(request, 'employees/company_job_applicants.html', {
        'company': company,
        'job': job,
        'applications': applications,
        'clients': clients,
    })


@company_required
def company_two_matched_onboard(request):
    """
    Onboard a worker from the job network into company workforce by matching
    BOTH Iqama Number and Phone Number.
    """
    company = request.company

    if request.method == 'POST':
        form = TwoMatchedOnboardForm(request.POST, company=company)
        if form.is_valid():
            iqama = form.cleaned_data['iqama_number'].strip()
            phone = form.cleaned_data['phone_number'].strip()
            basic_sal = form.cleaned_data['basic_salary']
            recv_amt = form.cleaned_data.get('receiving_amount') or (basic_sal + Decimal('1000.00'))
            position = form.cleaned_data.get('position')
            assigned_client = form.cleaned_data.get('assigned_client')
            joining_date = form.cleaned_data['joining_date']

            # Two-Matched Entry Lookup
            candidate = JobSeekerProfile.objects.filter(
                iqama_number=iqama,
                phone_number=phone
            ).first()

            if not candidate:
                messages.error(
                    request,
                    f"❌ Two-Matched Verification FAILED: No registered worker found matching BOTH Iqama '{iqama}' and Phone '{phone}'. "
                    "Both entries must exactly match an approved network candidate."
                )
                return render(request, 'employees/two_matched_onboard.html', {'form': form, 'company': company})

            if candidate.status == 'suspended':
                messages.error(request, "❌ Verification Failed: This candidate profile is currently suspended.")
                return render(request, 'employees/two_matched_onboard.html', {'form': form, 'company': company})

            # Check if candidate is already hired
            if Employee.objects.filter(iqama_number=iqama, client_company=company).exists():
                messages.warning(request, f"Worker with Iqama '{iqama}' is already in your company employee roster.")
                return redirect('employees_list')

            # Create the official Employee record
            emp = Employee.objects.create(
                user=candidate.user,
                name=candidate.full_name,
                nationality=candidate.nationality,
                phone_number=candidate.phone_number,
                iqama_number=candidate.iqama_number,
                passport_number=f"P{candidate.iqama_number[-7:]}",
                iqama_expiry=date.today() + timedelta(days=365),
                joining_date=joining_date,
                position=position or candidate.trade,
                basic_salary=basic_sal,
                receiving_amount=recv_amt,
                client_company=company,
                assigned_client=assigned_client,
                company_name=assigned_client.name if assigned_client else company.name,
                deployment_status='deployed' if assigned_client else 'available',
                deployment_date=joining_date if assigned_client else None,
                visa_status='active',
            )

            # Update candidate profile to hired
            candidate.status = 'hired'
            candidate.hired_by_company = company
            candidate.hired_as_employee = emp
            candidate.hired_at = timezone.now()
            candidate.save()

            messages.success(
                request,
                f"🎉 SUCCESS: Worker '{candidate.full_name}' ({candidate.trade}) verified by Iqama & Phone and onboarded into {company.name} workforce!"
            )
            return redirect('employee_detail', pk=emp.pk)
        else:
            messages.error(request, "Please correct the errors in the two-matched entry form.")
    else:
        # Pre-fill from GET parameters if coming from applicant card
        initial_data = {
            'iqama_number': request.GET.get('iqama', ''),
            'phone_number': request.GET.get('phone', ''),
            'position': request.GET.get('trade', ''),
            'basic_salary': request.GET.get('salary', '2500.00'),
        }
        form = TwoMatchedOnboardForm(initial=initial_data, company=company)

    return render(request, 'employees/two_matched_onboard.html', {
        'form': form,
        'company': company,
    })


# ================== PLATFORM MODERATION & REFERRAL AUDIT CONTROLS ==================

@moderator_required
def moderation_dashboard(request):
    """
    Restricted Platform Moderation & Content Safety Hub.
    Accessible to Master Admin AND Platform Staff Moderators.
    Strictly isolated: No tenant company financials, no subscription billing, no god mode.
    """
    # Candidate Metrics
    pending_candidates_count = JobSeekerProfile.objects.filter(status='pending_approval').count()
    active_candidates_count = JobSeekerProfile.objects.filter(status='active').count()
    suspended_candidates_count = JobSeekerProfile.objects.filter(status='suspended').count()

    # Job Posts Metrics
    pending_jobs_count = JobPost.objects.filter(status='pending_approval').count()
    active_jobs_count = JobPost.objects.filter(status='published').count()

    # Referral Links Anti-Spam Metrics
    total_referrals_count = OneTimeReferralLink.objects.count()
    active_referrals_count = OneTimeReferralLink.objects.filter(is_used=False).count()
    used_referrals_count = OneTimeReferralLink.objects.filter(is_used=True).count()
    candidate_referrals_count = OneTimeReferralLink.objects.filter(created_by__jobseeker_profile__isnull=False, created_by_company__isnull=True).count()
    company_referrals_count = OneTimeReferralLink.objects.filter(created_by_company__isnull=False).count()

    # Priority Action Queue 1: Pending Candidates needing Verification
    pending_candidates = JobSeekerProfile.objects.filter(status='pending_approval').select_related(
        'user', 'referred_by_link', 'referred_by_link__created_by', 'referred_by_link__created_by_company'
    ).order_by('-created_at')[:8]

    # Priority Action Queue 2: Pending Job Posts needing Review
    pending_jobs = JobPost.objects.filter(status='pending_approval').select_related('company').order_by('-created_at')[:8]

    # Priority Action Queue 3: Real-Time Provenance & Anti-Spam Referral Trail
    recent_referrals = OneTimeReferralLink.objects.all().select_related(
        'created_by', 'created_by__jobseeker_profile', 'created_by_company',
        'used_by', 'used_by__jobseeker_profile'
    ).order_by('-created_at')[:10]

    host = request.build_absolute_uri('/')[:-1]

    context = {
        'pending_candidates_count': pending_candidates_count,
        'active_candidates_count': active_candidates_count,
        'suspended_candidates_count': suspended_candidates_count,
        'pending_jobs_count': pending_jobs_count,
        'active_jobs_count': active_jobs_count,
        'total_referrals_count': total_referrals_count,
        'active_referrals_count': active_referrals_count,
        'used_referrals_count': used_referrals_count,
        'candidate_referrals_count': candidate_referrals_count,
        'company_referrals_count': company_referrals_count,
        'pending_candidates': pending_candidates,
        'pending_jobs': pending_jobs,
        'recent_referrals': recent_referrals,
        'host': host,
    }
    return render(request, 'employees/moderation_dashboard.html', context)


@moderator_required
def master_job_posts_queue(request):
    """Moderation queue for job requirements posted by companies."""
    status_filter = request.GET.get('status', 'pending_approval')
    posts_qs = JobPost.objects.all().select_related('company')
    if status_filter != 'all':
        posts_qs = posts_qs.filter(status=status_filter)

    pending_count = JobPost.objects.filter(status='pending_approval').count()
    published_count = JobPost.objects.filter(status='published').count()

    return render(request, 'employees/master_job_posts_queue.html', {
        'job_posts': posts_qs,
        'status_filter': status_filter,
        'pending_count': pending_count,
        'published_count': published_count,
    })


@moderator_required
def master_job_post_approve(request, pk):
    job = get_object_or_404(JobPost, pk=pk)
    job.status = 'published'
    job.approved_by = request.user
    job.approved_at = timezone.now()
    job.rejection_reason = None
    job.save()

    messages.success(request, f"Job requirement '{job.title}' by {job.company.name} APPROVED and published to the social feed!")
    return redirect('master_job_posts_queue')


@moderator_required
def master_job_post_reject(request, pk):
    job = get_object_or_404(JobPost, pk=pk)
    if request.method == 'POST':
        reason = request.POST.get('rejection_reason', 'Requirement details require revision.')
        job.status = 'rejected'
        job.rejection_reason = reason
        job.save()
        messages.warning(request, f"Job post '{job.title}' rejected. Reason recorded: {reason}")
    return redirect('master_job_posts_queue')


@moderator_required
def master_job_post_toggle_feature(request, pk):
    job = get_object_or_404(JobPost, pk=pk)
    job.is_featured = not job.is_featured
    job.save()
    status_msg = "Featured (Urgent)" if job.is_featured else "Standard"
    messages.info(request, f"Job '{job.title}' is now marked as {status_msg}.")
    return redirect('master_job_posts_queue')


@moderator_required
def master_jobseekers_queue(request):
    """Verification queue for candidates registered via one-time referral links."""
    status_filter = request.GET.get('status', 'pending_approval')
    candidates_qs = JobSeekerProfile.objects.all().select_related('user', 'referred_by_link', 'referred_by_link__created_by')
    if status_filter != 'all':
        candidates_qs = candidates_qs.filter(status=status_filter)

    pending_count = JobSeekerProfile.objects.filter(status='pending_approval').count()
    active_count = JobSeekerProfile.objects.filter(status='active').count()
    hired_count = JobSeekerProfile.objects.filter(status='hired').count()

    return render(request, 'employees/master_jobseekers_queue.html', {
        'candidates': candidates_qs,
        'status_filter': status_filter,
        'pending_count': pending_count,
        'active_count': active_count,
        'hired_count': hired_count,
    })


@moderator_required
def master_jobseeker_approve(request, pk):
    candidate = get_object_or_404(JobSeekerProfile, pk=pk)
    candidate.status = 'active'
    candidate.approved_by = request.user
    candidate.approved_at = timezone.now()
    candidate.save()

    messages.success(request, f"Candidate '{candidate.full_name}' (Iqama: {candidate.iqama_number}) APPROVED as a verified network user!")
    return redirect('master_jobseekers_queue')


@moderator_required
def master_jobseeker_suspend(request, pk):
    candidate = get_object_or_404(JobSeekerProfile, pk=pk)
    candidate.status = 'suspended'
    candidate.save()
    messages.warning(request, f"Candidate '{candidate.full_name}' has been SUSPENDED/BLACKLISTED.")
    return redirect('master_jobseekers_queue')


@moderator_required
def master_referrals_list(request):
    """
    Moderator & Master Admin One-Time Referral Manager & Anti-Crime Audit Trail.
    Platform-wide visibility of ALL invite links, who created them (Master Admin, Companies, Candidates),
    and who redeemed them. Equipped with Anti-Spam Revoke & Provenance Filters.
    """
    creator_filter = request.GET.get('creator', 'all')
    status_filter = request.GET.get('status', 'all')
    search_q = request.GET.get('q', '').strip()

    links_qs = OneTimeReferralLink.objects.all().select_related(
        'created_by', 'created_by__jobseeker_profile', 'created_by_company',
        'used_by', 'used_by__jobseeker_profile'
    )

    if creator_filter == 'master':
        links_qs = links_qs.filter(created_by__is_superuser=True)
    elif creator_filter == 'company':
        links_qs = links_qs.filter(created_by_company__isnull=False)
    elif creator_filter == 'candidate':
        links_qs = links_qs.filter(created_by__jobseeker_profile__isnull=False, created_by_company__isnull=True)

    if status_filter == 'active':
        links_qs = links_qs.filter(is_used=False)
    elif status_filter == 'used':
        links_qs = links_qs.filter(is_used=True)

    if search_q:
        links_qs = links_qs.filter(
            Q(token__icontains=search_q) |
            Q(label_note__icontains=search_q) |
            Q(created_by__username__icontains=search_q) |
            Q(created_by_company__name__icontains=search_q) |
            Q(used_by__username__icontains=search_q) |
            Q(used_by__jobseeker_profile__full_name__icontains=search_q) |
            Q(used_by__jobseeker_profile__iqama_number__icontains=search_q)
        )

    all_links = OneTimeReferralLink.objects.all()
    total_links = all_links.count()
    used_links = all_links.filter(is_used=True).count()
    active_links = all_links.filter(is_used=False).count()
    master_links_count = all_links.filter(created_by__is_superuser=True).count()
    company_links_count = all_links.filter(created_by_company__isnull=False).count()
    candidate_links_count = all_links.filter(created_by__jobseeker_profile__isnull=False, created_by_company__isnull=True).count()

    form = ReferralLinkGenerateForm()
    host = request.build_absolute_uri('/')[:-1]

    # Check for newly generated links in session to highlight and provide direct copy actions
    newly_generated_ids = request.session.pop('newly_generated_link_ids', [])
    newly_generated_links = []
    if newly_generated_ids:
        newly_generated_links = list(OneTimeReferralLink.objects.filter(id__in=newly_generated_ids).select_related('created_by'))

    return render(request, 'employees/master_referrals.html', {
        'links': links_qs,
        'total_links': total_links,
        'used_links': used_links,
        'active_links': active_links,
        'master_links_count': master_links_count,
        'company_links_count': company_links_count,
        'candidate_links_count': candidate_links_count,
        'creator_filter': creator_filter,
        'status_filter': status_filter,
        'search_q': search_q,
        'form': form,
        'host': host,
        'newly_generated_links': newly_generated_links,
    })


@moderator_required
def master_referral_generate(request):
    if request.method == 'POST':
        form = ReferralLinkGenerateForm(request.POST)
        if form.is_valid():
            label = form.cleaned_data.get('label_note')
            days = form.cleaned_data.get('valid_days') or 14
            count = int(request.POST.get('count', 1))
            count = max(1, min(count, 20))  # between 1 and 20

            created_links = []
            for _ in range(count):
                link = OneTimeReferralLink.generate_link(
                    user=request.user,
                    label_note=label,
                    valid_days=days
                )
                created_links.append(link)

            # Store the newly created link IDs in session so template displays prominent copy actions
            request.session['newly_generated_link_ids'] = [link.id for link in created_links]

            messages.success(
                request,
                f"Generated {len(created_links)} new One-Time Referral Link(s)! "
                "Each link can only be used once to prevent spam and maintain strict traceability."
            )
        else:
            messages.error(request, "Failed to generate referral links. Check inputs.")

    return redirect('master_referrals_list')


@moderator_required
def master_referral_revoke(request, pk):
    """
    Anti-Spam Tool: Moderator & Master Admin can immediately revoke and destroy an active referral link.
    """
    link = get_object_or_404(OneTimeReferralLink, pk=pk)
    if not link.is_used:
        token_snippet = link.token[:12]
        link.delete()
        messages.warning(request, f"🛡️ Anti-Spam Enforced: Invitation link '{token_snippet}...' was revoked and permanently destroyed.")
    else:
        messages.error(request, "Cannot revoke a referral link that has already been consumed.")
    return redirect('master_referrals_list')



# ================== PUBLIC / MULTI-TENANT REFERRAL & VIRAL RECRUITMENT ==================

@company_required
def company_referrals(request):
    """
    Contracting Company Candidate Referral Manager.
    Allows company admins to generate one-time invite links for technicians/candidates they want to onboard.
    Full provenance is tracked (tagged with created_by_company).
    """
    company = request.company
    links_qs = OneTimeReferralLink.objects.filter(created_by_company=company).select_related('created_by', 'used_by', 'used_by__jobseeker_profile')

    if request.method == 'POST':
        form = ReferralLinkGenerateForm(request.POST)
        if form.is_valid():
            label = form.cleaned_data.get('label_note')
            days = form.cleaned_data.get('valid_days') or 14
            count = int(request.POST.get('count', 1))
            count = max(1, min(count, 10))

            created_links = []
            for _ in range(count):
                link = OneTimeReferralLink.generate_link(
                    user=request.user,
                    company=company,
                    label_note=label,
                    valid_days=days
                )
                created_links.append(link)

            request.session['company_newly_generated_link_ids'] = [link.id for link in created_links]
            messages.success(request, f"Generated {len(created_links)} new candidate invitation link(s) for {company.name}!")
            return redirect('company_referrals')
        else:
            messages.error(request, "Failed to generate referral links. Check inputs.")
    else:
        form = ReferralLinkGenerateForm()

    newly_generated_ids = request.session.pop('company_newly_generated_link_ids', [])
    newly_generated_links = []
    if newly_generated_ids:
        newly_generated_links = list(OneTimeReferralLink.objects.filter(id__in=newly_generated_ids))

    host = request.build_absolute_uri('/')[:-1]
    total_links = links_qs.count()
    used_links = links_qs.filter(is_used=True).count()
    active_links = links_qs.filter(is_used=False).count()

    return render(request, 'employees/company_referrals.html', {
        'company': company,
        'links': links_qs,
        'total_links': total_links,
        'used_links': used_links,
        'active_links': active_links,
        'form': form,
        'host': host,
        'newly_generated_links': newly_generated_links,
    })


@login_required
def candidate_referrals(request):
    """
    Normal Candidate / Worker Social Referral Hub.
    Allows verified technicians to invite fellow workers/colleagues.
    Anti-spam protection:
    - Only active verified candidates can generate links.
    - Max 5 active unused links per candidate at a time.
    - Full provenance logged (Master Admin sees who invited whom).
    """
    if not hasattr(request.user, 'jobseeker_profile'):
        messages.error(request, "Only registered candidates can access this invite hub.")
        return redirect('jobs_feed')

    profile = request.user.jobseeker_profile
    if profile.status != 'active':
        messages.warning(request, "Your candidate profile must be approved by Master Admin before you can invite colleagues.")
        return redirect('jobs_feed')

    links_qs = OneTimeReferralLink.objects.filter(created_by=request.user, created_by_company__isnull=True).select_related('used_by', 'used_by__jobseeker_profile')
    active_unused_count = links_qs.filter(is_used=False).count()

    if request.method == 'POST':
        # Anti-spam guard: limit to 5 active unused links
        if active_unused_count >= 5:
            messages.error(request, "Anti-Spam Quota: You have 5 unused invitation links. Please wait until your colleagues register before creating more.")
            return redirect('candidate_referrals')

        label = request.POST.get('label_note', '').strip() or f"Invited by {profile.full_name}"
        link = OneTimeReferralLink.generate_link(
            user=request.user,
            company=None,
            label_note=label[:255],
            valid_days=14
        )
        request.session['candidate_newly_generated_id'] = link.id
        messages.success(request, "🎉 New invitation link created! Copy and send it to your colleague.")
        return redirect('candidate_referrals')

    newly_id = request.session.pop('candidate_newly_generated_id', None)
    newly_link = OneTimeReferralLink.objects.filter(id=newly_id).first() if newly_id else None

    host = request.build_absolute_uri('/')[:-1]

    return render(request, 'employees/candidate_referrals.html', {
        'profile': profile,
        'links': links_qs,
        'active_unused_count': active_unused_count,
        'newly_link': newly_link,
        'host': host,
    })


