from .tenant_context import get_current_company
from .models import Company

def tenant_context(request):
    """
    Supplies multi-tenant metadata to all templates.
    """
    if not request.user.is_authenticated:
        return {
            'current_company': None,
            'is_master_admin': False,
            'is_impersonating': False,
            'all_companies_for_switcher': [],
        }

    company, is_master, is_supreme_mode = get_current_company(request)

    all_companies = []
    if is_master:
        all_companies = Company.objects.all().order_by('name')

    is_jobseeker = hasattr(request.user, 'jobseeker_profile')
    jobseeker_profile = getattr(request.user, 'jobseeker_profile', None) if is_jobseeker else None

    pending_jobs_count = 0
    pending_jobseekers_count = 0
    if is_master:
        from .models import JobPost, JobSeekerProfile
        pending_jobs_count = JobPost.objects.filter(status='pending_approval').count()
        pending_jobseekers_count = JobSeekerProfile.objects.filter(status='pending_approval').count()

    return {
        'current_company': company,
        'is_master_admin': is_master,
        'is_impersonating': is_supreme_mode,
        'is_supreme_mode': is_supreme_mode,
        'supreme_mode_reason': request.session.get('supreme_mode_reason', ''),
        'all_companies_for_switcher': all_companies,
        'is_jobseeker': is_jobseeker,
        'jobseeker_profile': jobseeker_profile,
        'pending_jobs_count': pending_jobs_count,
        'pending_jobseekers_count': pending_jobseekers_count,
    }
