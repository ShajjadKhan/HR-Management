from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),

    # Master Admin Platform Portal
    path('master-admin/', views.master_dashboard, name='master_dashboard'),
    path('master-admin/companies/add/', views.master_company_add, name='master_company_add'),
    path('master-admin/companies/<int:pk>/edit/', views.master_company_edit, name='master_company_edit'),
    path('master-admin/companies/<int:pk>/toggle-access/', views.master_company_toggle_access, name='master_company_toggle_access'),
    path('master-admin/companies/<int:pk>/reset-password/', views.master_company_reset_password, name='master_company_reset_password'),
    path('master-admin/companies/<int:pk>/delete/', views.master_company_delete, name='master_company_delete'),
    path('master-admin/companies/<int:pk>/impersonate/', views.master_company_impersonate, name='master_company_impersonate'),
    path('master-admin/stop-impersonate/', views.master_stop_impersonate, name='master_stop_impersonate'),
    path('master-admin/supreme-mode/verify/', views.supreme_mode_verify, name='supreme_mode_verify'),
    path('master-admin/supreme-mode/exit/', views.supreme_mode_exit, name='supreme_mode_exit'),

    # Tenant Company Dashboard & Workers
    path('', views.dashboard, name='dashboard'),
    path('employees/', views.employees_list, name='employees_list'),
    path('employees/add/', views.employee_add, name='employee_add'),
    path('employees/<int:pk>/', views.employee_detail, name='employee_detail'),
    path('employees/profile/<int:pk>/', views.employee_detail, name='employee_profile'),
    path('employees/<int:pk>/edit/', views.employee_edit, name='employee_edit'),
    path('employees/<int:pk>/delete/', views.employee_delete, name='employee_delete'),
    path('employees/delete/<int:pk>/', views.employee_delete, name='employee_delete_alias'),



    # Accommodations / Properties
    path('properties/', views.properties_list, name='properties_list'),
    path('properties/add/', views.property_add, name='property_add'),
    path('properties/<int:pk>/edit/', views.property_edit, name='property_edit'),
    path('properties/<int:pk>/delete/', views.property_delete, name='property_delete'),

    # Clients & Bench Tracking
    path('clients/', views.clients_list, name='clients_list'),
    path('clients/add/', views.client_add, name='client_add'),
    path('clients/<int:pk>/', views.client_detail, name='client_detail'),
    path('clients/<int:pk>/edit/', views.client_edit, name='client_edit'),
    path('clients/<int:pk>/delete/', views.client_delete, name='client_delete'),
    path('employees/<int:pk>/assign-client/', views.employee_assign_client, name='employee_assign_client'),

    # Leave Management
    path('leave/apply/', views.leave_apply, name='leave_apply'),
    path('leave/list/', views.leave_list, name='leave_list'),
    path('leave/approve/<int:leave_id>/', views.leave_approve, name='leave_approve'),
    path('employees/<int:pk>/leave-contract/edit/', views.employee_leave_contract_edit, name='employee_leave_contract_edit'),

    # Payroll & Salary Disbursements
    path('disbursements/', views.salary_disbursements, name='salary_disbursements'),
    path('disbursements/<int:pk>/pay/', views.salary_disburse_submit, name='salary_disburse_submit'),
    path('salary/pay/<int:pk>/', views.salary_pay, name='salary_pay'),

    # Holidays & Leave Policy
    path('holidays/', views.holiday_list, name='holiday_list'),
    path('holidays/add/', views.holiday_add, name='holiday_add'),
    path('holidays/<int:pk>/delete/', views.holiday_delete, name='holiday_delete'),
    path('policy/edit/', views.policy_edit, name='policy_edit'),

    # Iqama Expiry & Renewal
    path('iqama/', views.iqama_expiry, name='iqama_expiry'),
    path('iqama/renew/<int:emp_id>/', views.iqama_renew, name='iqama_renew'),

    # Spending & Expense Tracker
    path('spending/', views.spending_tracker, name='spending_tracker'),
    path('employees/<int:emp_id>/expenses/add/', views.expense_add, name='expense_add'),
    path('expenses/<int:pk>/delete/', views.expense_delete, name='expense_delete'),
    path('expenses/<int:pk>/toggle-settle/', views.expense_toggle_settle, name='expense_toggle_settle'),

    # Excel Reports
    path('reports/', views.reports, name='reports'),

    # Private Manpower Job Marketplace & Invite-Only Network
    path('register/', views.candidate_register, name='candidate_register'),
    path('jobs/', views.jobs_feed, name='jobs_feed'),
    path('jobs/<int:pk>/', views.job_detail, name='job_detail'),
    path('jobs/<int:pk>/apply/', views.job_apply, name='job_apply'),

    # Contracting Company Hiring Portal & Two-Matched Fast Onboarding
    path('jobs/company/', views.company_jobs_list, name='company_jobs_list'),
    path('jobs/company/add/', views.company_job_add, name='company_job_add'),
    path('jobs/company/<int:pk>/applicants/', views.company_job_applicants, name='company_job_applicants'),
    path('jobs/onboard/two-matched/', views.company_two_matched_onboard, name='company_two_matched_onboard'),

    # Master Admin Moderation Queues & 1-Time Referral Traceability
    path('master-admin/job-posts/', views.master_job_posts_queue, name='master_job_posts_queue'),
    path('master-admin/job-posts/<int:pk>/approve/', views.master_job_post_approve, name='master_job_post_approve'),
    path('master-admin/job-posts/<int:pk>/reject/', views.master_job_post_reject, name='master_job_post_reject'),
    path('master-admin/job-posts/<int:pk>/feature/', views.master_job_post_toggle_feature, name='master_job_post_toggle_feature'),
    path('master-admin/job-seekers/', views.master_jobseekers_queue, name='master_jobseekers_queue'),
    path('master-admin/job-seekers/<int:pk>/approve/', views.master_jobseeker_approve, name='master_jobseeker_approve'),
    path('master-admin/job-seekers/<int:pk>/suspend/', views.master_jobseeker_suspend, name='master_jobseeker_suspend'),
    path('master-admin/referrals/', views.master_referrals_list, name='master_referrals_list'),
    path('master-admin/referrals/generate/', views.master_referral_generate, name='master_referral_generate'),
]
