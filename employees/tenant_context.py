from functools import wraps
from django.shortcuts import redirect, render
from django.contrib import messages
from .models import Company, Employee

def get_current_company(request):
    """
    Resolves current company context for the active session/user.
    Returns: (company, is_master, is_impersonating)
    """
    if not request.user.is_authenticated:
        return None, False, False

    # Check if Superuser / Master Admin
    if request.user.is_superuser:
        impersonate_id = request.session.get('impersonate_company_id')
        if impersonate_id:
            company = Company.objects.filter(id=impersonate_id).first()
            if company:
                return company, True, True
            # Invalid ID, clean up session
            request.session.pop('impersonate_company_id', None)
        # Master Admin has NO default company when not in verified Supreme Mode.
        # They stay isolated on their own master admin platform to safeguard customer data.
        return None, True, False

    # Check if user is a Company Admin
    company = getattr(request.user, 'managed_company', None)
    if not company:
        company = Company.objects.filter(admin_account=request.user).first()
    
    if company:
        return company, False, False

    # Check if user is an Employee
    emp = Employee.objects.filter(user=request.user).first()
    if emp and emp.client_company:
        return emp.client_company, False, False

    return None, False, False


def company_required(view_func):
    """
    Enforces valid tenant context and company subscription/access status.
    Protects customer workspaces against unauthorized roaming by Master Admin.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        company, is_master, is_supreme_mode = get_current_company(request)

        # Security check for Master Admin / Superuser
        if request.user.is_superuser:
            if not company or not is_supreme_mode:
                # Master admin attempted to roam into customer data without verified Supreme Mode!
                messages.error(
                    request,
                    "🔒 Customer Data Protection: Direct access to customer tenant pages is locked. "
                    "Master Administrator must stay in the Master Admin Portal. "
                    "To enter a customer workspace for verified technical assistance, use Supreme Mode at the bottom-left."
                )
                return redirect('master_dashboard')

            request.company = company
            request.is_master_admin = True
            request.is_impersonating = True
            request.is_supreme_mode = True
            return view_func(request, *args, **kwargs)

        company, is_master, is_impersonating = get_current_company(request)
        if not company:
            if hasattr(request.user, 'jobseeker_profile'):
                return redirect('jobs_feed')
            return render(request, 'employees/access_suspended.html', {
                'title': 'No Company Associated',
                'message': 'Your account is not associated with any active contracting company. Please contact the platform master administrator.'
            })

        # Check access suspension
        if not company.is_active:
            return render(request, 'employees/access_suspended.html', {
                'title': 'Company Access Suspended',
                'company': company,
                'message': f"Access for '{company.name}' has been suspended by the platform administration. Please contact support or your account representative to restore access."
            })

        # Check subscription expiry - enforce 14-day grace period before hard lockout
        if company.is_subscription_expired:
            if company.days_until_expiry is not None and company.days_until_expiry < -14:
                return render(request, 'employees/access_suspended.html', {
                    'title': 'Subscription Expired - Grace Period Ended',
                    'company': company,
                    'message': f"The subscription for '{company.name}' expired on {company.subscription_expiry}. The 14-day grace period has ended. Please renew your plan with the platform administrator to restore access."
                })

        request.company = company
        request.is_master_admin = False
        request.is_impersonating = False
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def master_admin_required(view_func):
    """
    Restricts access strictly to the SaaS Master Administrator (superuser).
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_superuser:
            messages.error(request, "Access restricted. Only Master Administrators can access this portal.")
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)

    return _wrapped_view
