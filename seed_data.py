import os
import django
from datetime import date, timedelta
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_backend.settings')
django.setup()

from django.contrib.auth.models import User
from employees.models import (
    TenantCompany, UserProfile, ClientCompany, ProjectSite, ContractRate,
    Employee, EmployeeDeployment, MonthlyFinancialRecord, LeavePolicy
)

# 1. Master Admin User Setup
admin_user, _ = User.objects.get_or_create(username='admin')
admin_user.is_superuser = True
admin_user.is_staff = True
admin_user.set_password('1122')
admin_user.save()

profile, _ = UserProfile.objects.get_or_create(user=admin_user)
profile.role = 'master_admin'
profile.save()

# 2. Tenant 1: Nasaem Al Enjaz Manpower Services
nasaem, _ = TenantCompany.objects.get_or_create(
    name="Nasaem Al Enjaz Manpower Services",
    defaults={
        "trade_name_ar": "شركة نسائم الإنجاز لتوريد الكوادر البشرية",
        "cr_number": "1010789456",
        "qiwa_id": "700123456",
        "tax_number": "30045678900003",
        "contact_email": "operations@nasaemalenjaz.com",
        "contact_phone": "+966 50 123 4567",
        "address": "King Fahd Road, Al-Olaya, Riyadh, Saudi Arabia",
        "subscription_status": "active",
        "max_employees": 300,
        "default_ticket_accrual": Decimal("150.00"),
        "default_leave_accrual": Decimal("100.00"),
        "default_eosb_accrual": Decimal("50.00"),
        "default_iqama_levy_accrual": Decimal("350.00"),
        "default_other_overhead": Decimal("100.00"),
    }
)

# Link admin user as owner for testing
nasaem.owner_user = admin_user
nasaem.save()
profile.tenant = nasaem
profile.save()

# Create LeavePolicy for Nasaem
LeavePolicy.objects.get_or_create(tenant=nasaem)

# 2b. Tenant 2: Al-Bader Contracting & Manpower (for demonstrating multi-tenant sales)
albader, _ = TenantCompany.objects.get_or_create(
    name="Al-Bader Contracting & Manpower",
    defaults={
        "trade_name_ar": "شركة البدر للمقاولات والاستقدام",
        "cr_number": "1010543210",
        "qiwa_id": "700987654",
        "tax_number": "300112233440003",
        "contact_email": "hr@albader-sa.com",
        "contact_phone": "+966 55 987 6543",
        "address": "Al Malaz District, Riyadh, Saudi Arabia",
        "subscription_status": "active",
        "max_employees": 150,
    }
)

# 3. Client Companies under Nasaem
marriott, _ = ClientCompany.objects.get_or_create(
    tenant=nasaem,
    name="Riyadh Marriott Hotel",
    defaults={
        "cr_number": "1010998877",
        "contact_person": "Eng. Tariq Al-Mansoor (Director of Operations)",
        "phone": "+966 11 477 9300",
        "email": "procurement@riyadhmarriott.com",
        "billing_address": "King Saud Road, Riyadh 11415",
    }
)

hilton, _ = ClientCompany.objects.get_or_create(
    tenant=nasaem,
    name="Hilton Riyadh Hotel & Residences",
    defaults={
        "cr_number": "1010887766",
        "contact_person": "Sarah Al-Ghamdi (Facilities Manager)",
        "phone": "+966 11 234 5678",
        "email": "hr.procure@hiltonriyadh.com",
        "billing_address": "Eastern Ring Branch Rd, Granada, Riyadh",
    }
)

# 4. Project Sites under Clients
dq_site, _ = ProjectSite.objects.get_or_create(
    client=marriott,
    name="Marriott Diplomatic Quarter (DQ)",
    defaults={
        "location": "Abdullah Alsahmi St, Diplomatic Quarter, Riyadh",
        "site_manager": "Ahmed Al-Harbi",
        "site_phone": "+966 50 222 3344",
    }
)

airport_site, _ = ProjectSite.objects.get_or_create(
    client=marriott,
    name="Marriott Airport Road",
    defaults={
        "location": "Airport Road, King Khalid International Airport, Riyadh",
        "site_manager": "Mustafa Kamal",
        "site_phone": "+966 50 333 4455",
    }
)

hilton_site, _ = ProjectSite.objects.get_or_create(
    client=hilton,
    name="Hilton Business Gate",
    defaults={
        "location": "Granada Business Gate, Riyadh",
        "site_manager": "Khaled Al-Otaibi",
        "site_phone": "+966 50 444 5566",
    }
)

# 5. Contract Rates
ContractRate.objects.get_or_create(
    client=marriott,
    position_title="Housekeeping (HK)",
    defaults={
        "monthly_billing_rate": Decimal("3150.00"),
        "standard_worker_salary": Decimal("1200.00"),
        "overtime_hourly_rate": Decimal("20.00"),
    }
)

ContractRate.objects.get_or_create(
    client=marriott,
    position_title="AC Technician",
    defaults={
        "monthly_billing_rate": Decimal("5000.00"),
        "standard_worker_salary": Decimal("2500.00"),
        "overtime_hourly_rate": Decimal("35.00"),
    }
)

ContractRate.objects.get_or_create(
    client=marriott,
    position_title="Kitchen Steward",
    defaults={
        "monthly_billing_rate": Decimal("2800.00"),
        "standard_worker_salary": Decimal("1200.00"),
        "overtime_hourly_rate": Decimal("18.00"),
    }
)

ContractRate.objects.get_or_create(
    client=hilton,
    position_title="Housekeeping (HK)",
    defaults={
        "monthly_billing_rate": Decimal("3200.00"),
        "standard_worker_salary": Decimal("1200.00"),
        "overtime_hourly_rate": Decimal("22.00"),
    }
)

ContractRate.objects.get_or_create(
    client=hilton,
    position_title="Electrician",
    defaults={
        "monthly_billing_rate": Decimal("4500.00"),
        "standard_worker_salary": Decimal("2200.00"),
        "overtime_hourly_rate": Decimal("30.00"),
    }
)

# 6. Employees for Nasaem
today = date.today()

e1, _ = Employee.objects.get_or_create(
    tenant=nasaem,
    iqama_number="2450123456",
    defaults={
        "name": "Md. Kabir Hossain",
        "employee_id": "NE-101",
        "nationality": "Bangladesh",
        "origin_country": "Bangladesh",
        "phone_number": "+966 57 111 2233",
        "iqama_expiry": today + timedelta(days=240),
        "iqama_expiry_hijri": "1448/06/15",
        "passport_number": "A09876543",
        "passport_expiry": today + timedelta(days=700),
        "border_number": "3104567891",
        "qiwa_contract_number": "QW-998822",
        "ajeer_notice_number": "AJ-2026-4411",
        "ajeer_expiry": today + timedelta(days=180),
        "insurance_expiry": today + timedelta(days=200),
        "kafeel_name": "Nasaem Al Enjaz Co.",
        "visa_status": "active",
        "position": "Housekeeping (HK)",
        "iqama_profession": "عامل نظافة (Cleaning Worker)",
        "joining_date": today - timedelta(days=365),
        "status": "deployed",
        "current_client": marriott,
        "current_site": dq_site,
        "basic_salary": Decimal("1200.00"),
        "food_allowance": Decimal("0.00"),
        "housing_allowance": Decimal("0.00"),
        "client_billing_rate": Decimal("3150.00"),
        "ticket_accrual": Decimal("150.00"),
        "leave_accrual": Decimal("100.00"),
        "eosb_accrual": Decimal("50.00"),
        "iqama_levy_accrual": Decimal("350.00"),
        "other_overhead": Decimal("100.00"),
        "salary_paid": True,
        "payment_history": f"{today}: Paid SAR 1200 via Alinma Payroll WPA",
    }
)

e2, _ = Employee.objects.get_or_create(
    tenant=nasaem,
    iqama_number="2461234567",
    defaults={
        "name": "Rajesh Kumar Sharma",
        "employee_id": "NE-102",
        "nationality": "India",
        "origin_country": "India",
        "phone_number": "+966 57 222 3344",
        "iqama_expiry": today + timedelta(days=18), # Expiring soon alert!
        "iqama_expiry_hijri": "1448/03/12",
        "passport_number": "Z1234567",
        "passport_expiry": today + timedelta(days=500),
        "border_number": "3104567892",
        "qiwa_contract_number": "QW-998833",
        "ajeer_notice_number": "AJ-2026-4422",
        "ajeer_expiry": today + timedelta(days=15),
        "insurance_expiry": today + timedelta(days=20),
        "kafeel_name": "Nasaem Al Enjaz Co.",
        "visa_status": "expiring_soon",
        "position": "AC Technician",
        "iqama_profession": "فني تكييف (HVAC Technician)",
        "joining_date": today - timedelta(days=500),
        "status": "deployed",
        "current_client": marriott,
        "current_site": airport_site,
        "basic_salary": Decimal("2500.00"),
        "food_allowance": Decimal("200.00"),
        "housing_allowance": Decimal("0.00"),
        "client_billing_rate": Decimal("5000.00"),
        "ticket_accrual": Decimal("150.00"),
        "leave_accrual": Decimal("208.00"),
        "eosb_accrual": Decimal("104.00"),
        "iqama_levy_accrual": Decimal("350.00"),
        "other_overhead": Decimal("100.00"),
        "salary_paid": True,
        "payment_history": f"{today}: Paid SAR 2700 via Alinma Payroll WPA",
    }
)

e3, _ = Employee.objects.get_or_create(
    tenant=nasaem,
    iqama_number="2472345678",
    defaults={
        "name": "Muhammad Farhan",
        "employee_id": "NE-103",
        "nationality": "Pakistan",
        "origin_country": "Pakistan",
        "phone_number": "+966 57 333 4455",
        "iqama_expiry": today + timedelta(days=120),
        "iqama_expiry_hijri": "1448/05/01",
        "passport_number": "P7654321",
        "passport_expiry": today + timedelta(days=400),
        "border_number": "3104567893",
        "qiwa_contract_number": "QW-998844",
        "ajeer_notice_number": "AJ-2026-4433",
        "ajeer_expiry": today + timedelta(days=90),
        "insurance_expiry": today + timedelta(days=120),
        "kafeel_name": "Nasaem Al Enjaz Co.",
        "visa_status": "active",
        "position": "Electrician",
        "iqama_profession": "كهربائي عام (General Electrician)",
        "joining_date": today - timedelta(days=200),
        "status": "deployed",
        "current_client": hilton,
        "current_site": hilton_site,
        "basic_salary": Decimal("2200.00"),
        "food_allowance": Decimal("0.00"),
        "housing_allowance": Decimal("0.00"),
        "client_billing_rate": Decimal("4500.00"),
        "ticket_accrual": Decimal("150.00"),
        "leave_accrual": Decimal("183.00"),
        "eosb_accrual": Decimal("91.00"),
        "iqama_levy_accrual": Decimal("350.00"),
        "other_overhead": Decimal("100.00"),
        "salary_paid": False,
    }
)

e4, _ = Employee.objects.get_or_create(
    tenant=nasaem,
    iqama_number="2483456789",
    defaults={
        "name": "Noel Santos",
        "employee_id": "NE-104",
        "nationality": "Philippines",
        "origin_country": "Philippines",
        "phone_number": "+966 57 444 5566",
        "iqama_expiry": today + timedelta(days=300),
        "iqama_expiry_hijri": "1448/08/20",
        "passport_number": "PH889911",
        "passport_expiry": today + timedelta(days=900),
        "border_number": "3104567894",
        "qiwa_contract_number": "QW-998855",
        "kafeel_name": "Nasaem Al Enjaz Co.",
        "visa_status": "active",
        "position": "Housekeeping Supervisor",
        "iqama_profession": "مشرف نظافة (Cleaning Supervisor)",
        "joining_date": today - timedelta(days=60),
        "status": "bench", # Currently on Bench / Standby at Camp
        "current_client": None,
        "current_site": None,
        "basic_salary": Decimal("1800.00"),
        "food_allowance": Decimal("0.00"),
        "housing_allowance": Decimal("0.00"),
        "client_billing_rate": Decimal("0.00"),
        "ticket_accrual": Decimal("150.00"),
        "leave_accrual": Decimal("150.00"),
        "eosb_accrual": Decimal("75.00"),
        "iqama_levy_accrual": Decimal("350.00"),
        "other_overhead": Decimal("100.00"),
        "salary_paid": False,
        "additional_note": "Awaiting deployment approval from Riyadh Marriott or new client.",
    }
)

# Deployments records
EmployeeDeployment.objects.get_or_create(
    employee=e1, client=marriott, site=dq_site,
    defaults={"role_title": "Housekeeping (HK)", "billing_rate": Decimal("3150.00"), "worker_salary": Decimal("1200.00"), "start_date": today - timedelta(days=180), "status": "active"}
)
EmployeeDeployment.objects.get_or_create(
    employee=e2, client=marriott, site=airport_site,
    defaults={"role_title": "AC Technician", "billing_rate": Decimal("5000.00"), "worker_salary": Decimal("2500.00"), "start_date": today - timedelta(days=120), "status": "active"}
)
EmployeeDeployment.objects.get_or_create(
    employee=e3, client=hilton, site=hilton_site,
    defaults={"role_title": "Electrician", "billing_rate": Decimal("4500.00"), "worker_salary": Decimal("2200.00"), "start_date": today - timedelta(days=90), "status": "active"}
)

# Monthly Financial Snapshot
for emp in [e1, e2, e3, e4]:
    MonthlyFinancialRecord.objects.get_or_create(
        tenant=nasaem,
        employee=emp,
        year=today.year,
        month=today.month,
        defaults={
            "client": emp.current_client,
            "site": emp.current_site,
            "status_at_month": emp.status,
            "client_billed": emp.client_billing_rate,
            "salary_paid": Decimal(emp.total_salary_payable),
            "ticket_provision": emp.ticket_accrual,
            "leave_provision": emp.leave_accrual,
            "eosb_provision": emp.eosb_accrual,
            "iqama_provision": emp.iqama_levy_accrual,
            "other_overhead": emp.other_overhead,
            "net_profit": Decimal(emp.monthly_net_profit),
            "is_salary_settled": emp.salary_paid,
            "is_client_invoiced": True if emp.status == 'deployed' else False,
        }
    )

print("Seed data successfully installed!")
