import os
import django
from datetime import date, timedelta
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_backend.settings')
django.setup()

from django.contrib.auth.models import User
from employees.models import (
    Company, Employee, Property, EmployeeProperty, 
    LeavePolicy, LeaveBalance, Holiday, EmployeeExpense, ClientCompany
)

def seed():
    print("Seeding initial Master Admin and Sample Contracting Companies...")

    # 1. Master Admin (Platform Super-Admin)
    master_admin, created = User.objects.get_or_create(
        username="master_admin",
        defaults={
            'email': "master@antigravityhr.com",
            'is_staff': True,
            'is_superuser': True,
        }
    )
    master_admin.set_password("Admin@12345")
    master_admin.is_staff = True
    master_admin.is_superuser = True
    master_admin.save()
    print(f"✅ Master Admin user: {master_admin.username} (Password: Admin@12345)")

    # 2. Contracting Company 1: Al-Madina Contracting LLC
    admin_madina, _ = User.objects.get_or_create(
        username="almadina_admin",
        defaults={'email': "hr@almadina-contracting.com", 'is_staff': False, 'is_superuser': False}
    )
    admin_madina.set_password("Madina@12345")
    admin_madina.save()

    madina_company, _ = Company.objects.get_or_create(
        name="Al-Madina Contracting LLC",
        defaults={
            'cr_number': "1010892341",
            'contact_person': "Sheikh Tariq Al-Madina",
            'email': "contact@almadina-contracting.com",
            'phone': "+966 50 123 4567",
            'address': "Olaya District, Riyadh, Saudi Arabia",
            'admin_account': admin_madina,
            'plan': "standard",
            'max_employees': 50,
            'is_active': True,
            'subscription_expiry': date.today() + timedelta(days=365),
            'notes': "Annual enterprise agreement signed for 50 worker slots.",
        }
    )
    LeavePolicy.objects.get_or_create(company=madina_company, defaults={'yearly_leave': 21.00})
    print(f"✅ Company 1: {madina_company.name} | Admin: almadina_admin (Password: Madina@12345)")

    madina_company.subscription_fee = 15000.00
    madina_company.billing_cycle = 'yearly'
    madina_company.subscription_expiry = date.today() + timedelta(days=18)
    madina_company.save()

    # Accommodations for Madina
    prop1, _ = Property.objects.get_or_create(
        company=madina_company,
        property_name="Camp Al-Noor #4, Riyadh Industrial Area",
        defaults={
            'housing_type': 'company_rented',
            'cost_to_company': 3500.00,
            'charge_to_client': 0.00,
            'worker_deduction': 0.00,
            'capacity': 30,
            'location': "Riyadh 2nd Industrial City",
        }
    )
    prop1.housing_type = 'company_rented'
    prop1.cost_to_company = 3500.00
    prop1.capacity = 30
    prop1.location = "Riyadh 2nd Industrial City"
    prop1.save()

    # Accommodation 2 for Madina (Client-Provided at SAR 0.00)
    prop_client, _ = Property.objects.get_or_create(
        company=madina_company,
        property_name="Qiddiya Client Camp Sector 4 (Client-Provided)",
        defaults={
            'housing_type': 'client_provided',
            'cost_to_company': 0.00,
            'charge_to_client': 0.00,
            'worker_deduction': 0.00,
            'capacity': 50,
            'location': "Qiddiya Project Site Camp",
        }
    )
    prop_client.housing_type = 'client_provided'
    prop_client.cost_to_company = 0.00
    prop_client.charge_to_client = 0.00
    prop_client.worker_deduction = 0.00
    prop_client.capacity = 50
    prop_client.location = "Qiddiya Project Site Camp"
    prop_client.save()

    # Clients for Madina
    client_metro, _ = ClientCompany.objects.get_or_create(
        company=madina_company,
        name="Riyadh Metro Transit Consortium",
        defaults={
            'contact_person': "Jean-Pierre Laurent",
            'phone': "+966 55 111 8899",
            'email': "contracts@rmtc.sa",
            'project_name': "Riyadh Metro Line 3 Extension",
            'project_location': "Riyadh",
            'contract_number': "RMT-2025-992",
            'status': "active",
        }
    )

    client_qiddiya, _ = ClientCompany.objects.get_or_create(
        company=madina_company,
        name="Qiddiya Investment Co.",
        defaults={
            'contact_person': "Eng. Abdullah Al-Sudairy",
            'phone': "+966 50 222 1100",
            'email': "procurement@qiddiya.com",
            'project_name': "Qiddiya Speed Park & Infrastructure",
            'project_location': "Riyadh / Qiddiya",
            'contract_number': "QID-2026-041",
            'status': "active",
        }
    )

    # Sample Employees for Madina
    emp1, _ = Employee.objects.get_or_create(
        iqama_number="2458901234",
        defaults={
            'name': "Mohammed Rafiq",
            'nationality': "Bangladeshi",
            'phone_number': "+966 55 987 6543",
            'passport_number': "EE0987123",
            'iqama_expiry': date.today() + timedelta(days=15),  # Expiring soon
            'joining_date': date.today() - timedelta(days=300),
            'kafeel_name': "Al-Madina Manpower Sponsorship",
            'visa_status': "active",
            'client_company': madina_company,
            'assigned_client': client_metro,
            'deployment_status': "deployed",
            'deployment_date': date.today() - timedelta(days=180),
            'client_project': "Riyadh Metro Line 3 Project",
            'position': "Structural Welder",
            'basic_salary': 2800.00,
            'receiving_amount': 4500.00,
            'salary_from_account': "Al Rajhi Bank (IBAN: SA4480000201608010)",
            'salary_payment_company': "Al-Madina Contracting LLC",
            'salary_paid': True,
            'payment_history': f"{date.today()}: Paid SAR 2800.00 for January",
        }
    )
    emp1.assigned_client = client_metro
    emp1.deployment_status = 'deployed'
    emp1.salary_from_account = "Al Rajhi Bank (IBAN: SA4480000201608010)"
    emp1.salary_payment_company = "Al-Madina Contracting LLC"
    emp1.contract_annual_leave = Decimal('21.00')
    emp1.contract_ticket_frequency = 'every_year'
    emp1.contract_carry_forward = Decimal('15.00')
    emp1.contract_sick_leave = Decimal('10.00')
    emp1.contract_emergency_leave = Decimal('2.00')
    emp1.leave_contract_notes = "Standard labor contract: 21 days annual leave with Dhaka round-trip ticket."
    emp1.save()
    EmployeeProperty.objects.get_or_create(employee=emp1, property=prop1)
    LeaveBalance.objects.get_or_create(employee=emp1, year=date.today().year, defaults={'accrued_balance': 21.00})

    # Sample expenses for Mohammed Rafiq
    if not EmployeeExpense.objects.filter(employee=emp1, expense_type='iqama_renewal').exists():
        EmployeeExpense.objects.create(
            company=madina_company,
            employee=emp1,
            expense_type='iqama_renewal',
            amount=650.00,
            notes="Jawazat 1-Year renewal fee",
            expense_date=date.today() - timedelta(days=20)
        )
    if not EmployeeExpense.objects.filter(employee=emp1, expense_type='vacation').exists():
        EmployeeExpense.objects.create(
            company=madina_company,
            employee=emp1,
            expense_type='vacation',
            amount=1200.00,
            notes="Annual leave flight ticket (Dhaka roundtrip)",
            expense_date=date.today() - timedelta(days=60)
        )

    emp2, _ = Employee.objects.get_or_create(
        iqama_number="2458909876",
        defaults={
            'name': "Suresh Kumar",
            'nationality': "Indian",
            'phone_number': "+966 54 321 0987",
            'passport_number': "M8765432",
            'iqama_expiry': date.today() + timedelta(days=180),  # Valid
            'joining_date': date.today() - timedelta(days=120),
            'kafeel_name': "Al-Madina Manpower Sponsorship",
            'visa_status': "active",
            'client_company': madina_company,
            'assigned_client': client_qiddiya,
            'deployment_status': "deployed",
            'deployment_date': date.today() - timedelta(days=90),
            'client_project': "Qiddiya Infrastructure Site",
            'position': "Heavy Equipment Operator",
            'basic_salary': 3200.00,
            'receiving_amount': 5200.00,
            'salary_from_account': "Al Rajhi Bank (IBAN: SA4480000201608010)",
            'salary_payment_company': "Al-Madina Contracting LLC",
            'salary_paid': False,
        }
    )
    emp2.assigned_client = client_qiddiya
    emp2.deployment_status = 'deployed'
    emp2.salary_from_account = "Al Rajhi Bank (IBAN: SA4480000201608010)"
    emp2.salary_payment_company = "Al-Madina Contracting LLC"
    emp2.contract_annual_leave = Decimal('25.00')
    emp2.contract_ticket_frequency = 'every_2_years'
    emp2.contract_allow_negative = True
    emp2.contract_negative_limit = Decimal('5.00')
    emp2.contract_sick_leave = Decimal('10.00')
    emp2.contract_emergency_leave = Decimal('3.00')
    emp2.leave_contract_notes = "Special operator contract: 25 days leave, ticket every 2 years, advance leave permitted."
    emp2.save()
    LeaveBalance.objects.get_or_create(employee=emp2, year=date.today().year, defaults={'accrued_balance': 25.00})
    # Assign Suresh to Client-provided camp (SAR 0.00)
    EmployeeProperty.objects.filter(employee=emp2).delete()
    EmployeeProperty.objects.create(employee=emp2, property=prop_client, custom_charge=0.00)

    # Sample expenses for Suresh Kumar (Advance salary + transport)
    if not EmployeeExpense.objects.filter(employee=emp2, expense_type='advance_salary').exists():
        EmployeeExpense.objects.create(
            company=madina_company,
            employee=emp2,
            expense_type='advance_salary',
            amount=500.00,
            notes="Emergency advance against salary",
            deduct_from_salary=True,
            expense_date=date.today() - timedelta(days=5)
        )
    if not EmployeeExpense.objects.filter(employee=emp2, expense_type='transport').exists():
        EmployeeExpense.objects.create(
            company=madina_company,
            employee=emp2,
            expense_type='transport',
            amount=150.00,
            notes="Monthly site bus transport pass",
            deduct_from_salary=False,
            expense_date=date.today() - timedelta(days=10)
        )

    # 3. Contracting Company 2: Gulf Apex Manpower Co.
    admin_apex, _ = User.objects.get_or_create(
        username="gulfapex_admin",
        defaults={'email': "admin@gulfapex.sa", 'is_staff': False, 'is_superuser': False}
    )
    admin_apex.set_password("Apex@12345")
    admin_apex.save()

    apex_company, _ = Company.objects.get_or_create(
        name="Gulf Apex Manpower Co.",
        defaults={
            'cr_number': "1010774512",
            'contact_person': "Fahad Al-Zahrani",
            'email': "info@gulfapex.sa",
            'phone': "+966 56 444 3322",
            'address': "Al-Khobar Corniche, Eastern Province",
            'admin_account': admin_apex,
            'plan': "standard",
            'subscription_fee': 9500.00,
            'billing_cycle': "yearly",
            'max_employees': 35,
            'is_active': True,
            'subscription_expiry': date.today() + timedelta(days=120),
            'notes': "Standard subscription for 35 workers.",
        }
    )
    apex_company.subscription_fee = 9500.00
    apex_company.billing_cycle = "yearly"
    apex_company.subscription_expiry = date.today() + timedelta(days=120)
    apex_company.save()
    LeavePolicy.objects.get_or_create(company=apex_company, defaults={'yearly_leave': 21.00})
    print(f"✅ Company 2: {apex_company.name} | Admin: gulfapex_admin (Password: Apex@12345)")

    # Accommodation for Apex
    prop2, _ = Property.objects.get_or_create(
        company=apex_company,
        property_name="Dammam Port Workers Housing Block B",
        defaults={'charge_amount': 2800.00, 'employee_salary': 1200.00}
    )

    # Worker for Apex
    emp3, _ = Employee.objects.get_or_create(
        iqama_number="2399123456",
        defaults={
            'name': "Ali Raza",
            'nationality': "Pakistani",
            'phone_number': "+966 53 111 2233",
            'passport_number': "PK445566",
            'iqama_expiry': date.today() - timedelta(days=5),
            'joining_date': date.today() - timedelta(days=400),
            'kafeel_name': "Gulf Apex Sponsorship",
            'visa_status': "expired",
            'client_company': apex_company,
            'client_project': "Aramco Ras Tanura Refinery",
            'position': "Piping Inspector",
            'basic_salary': 4000.00,
            'receiving_amount': 6500.00,
            'salary_from_account': "SNB Al-Ahli Payroll (IBAN: SA03100000012345)",
            'salary_payment_company': "Gulf Apex Manpower Co.",
            'salary_paid': False,
        }
    )
    emp3.salary_from_account = "SNB Al-Ahli Payroll (IBAN: SA03100000012345)"
    emp3.salary_payment_company = "Gulf Apex Manpower Co."
    emp3.save()
    EmployeeProperty.objects.get_or_create(employee=emp3, property=prop2)

    # 4. Contracting Company 3 (Expired subscription for reminder demo): Red Sea Builders Est.
    admin_redsea, _ = User.objects.get_or_create(
        username="redsea_admin",
        defaults={'email': "info@redsea-builders.sa", 'is_staff': False, 'is_superuser': False}
    )
    admin_redsea.set_password("Redsea@12345")
    admin_redsea.save()

    redsea_company, _ = Company.objects.get_or_create(
        name="Red Sea Builders Est.",
        defaults={
            'cr_number': "4030291823",
            'contact_person': "Ibrahim Al-Harbi",
            'email': "contracts@redsea-builders.sa",
            'phone': "+966 55 888 7766",
            'address': "Al-Hamra, Jeddah",
            'admin_account': admin_redsea,
            'plan': "starter",
            'subscription_fee': 4800.00,
            'billing_cycle': "quarterly",
            'max_employees': 20,
            'is_active': True,
            'subscription_expiry': date.today() - timedelta(days=4),
            'notes': "Quarterly agreement expired. Follow up for renewal payment.",
        }
    )
    redsea_company.subscription_fee = 4800.00
    redsea_company.billing_cycle = "quarterly"
    redsea_company.subscription_expiry = date.today() - timedelta(days=4)
    redsea_company.save()
    LeavePolicy.objects.get_or_create(company=redsea_company, defaults={'yearly_leave': 21.00})
    print(f"✅ Company 3: {redsea_company.name} | Admin: redsea_admin (Password: Redsea@12345)")

    # Accommodations for Red Sea Builders
    prop3, _ = Property.objects.get_or_create(
        company=redsea_company,
        property_name="Jeddah Port Labor Housing Complex - Bldg 4",
        defaults={
            'housing_type': 'company_rented',
            'cost_to_company': 3200.00,
            'charge_to_client': 0.00,
            'worker_deduction': 0.00,
            'capacity': 28,
            'location': "Jeddah Islamic Port Logistics Zone",
        }
    )
    prop3.housing_type = 'company_rented'
    prop3.cost_to_company = 3200.00
    prop3.capacity = 28
    prop3.location = "Jeddah Islamic Port Logistics Zone"
    prop3.save()

    prop_rsg_camp, _ = Property.objects.get_or_create(
        company=redsea_company,
        property_name="RSG Coastal Village Camp (Client-Provided)",
        defaults={
            'housing_type': 'client_provided',
            'cost_to_company': 0.00,
            'charge_to_client': 0.00,
            'worker_deduction': 0.00,
            'capacity': 60,
            'location': "Red Sea Project Site, Umluj",
        }
    )
    prop_rsg_camp.housing_type = 'client_provided'
    prop_rsg_camp.cost_to_company = 0.00
    prop_rsg_camp.charge_to_client = 0.00
    prop_rsg_camp.worker_deduction = 0.00
    prop_rsg_camp.capacity = 60
    prop_rsg_camp.location = "Red Sea Project Site, Umluj"
    prop_rsg_camp.save()

    # Clients for Red Sea Builders
    client_rsg, _ = ClientCompany.objects.get_or_create(
        company=redsea_company,
        name="Red Sea Global (RSG)",
        defaults={
            'contact_person': "Eng. Fahad Al-Ghamdi",
            'phone': "+966 50 444 1122",
            'email': "procurement@redseaglobal.com",
            'project_name': "The Red Sea Project - Shura Island Package",
            'project_location': "Umluj / Tabuk Province",
            'contract_number': "RSG-SUB-2025-012",
            'status': "active",
            'notes': "Site camp provided free of charge by client at Coastal Village Camp.",
        }
    )

    client_nesma, _ = ClientCompany.objects.get_or_create(
        company=redsea_company,
        name="Nesma & Partners Contracting",
        defaults={
            'contact_person': "Tariq Mansour",
            'phone': "+966 54 888 3344",
            'email': "t.mansour@nesmapartners.com",
            'project_name': "Jeddah Islamic Port Logistics Zone",
            'project_location': "Jeddah Port",
            'contract_number': "NES-JED-884",
            'status': "active",
        }
    )

    # Worker 1 for Red Sea Builders (Deployed at Nesma & Partners)
    emp4, _ = Employee.objects.get_or_create(
        iqama_number="2412345678",
        defaults={
            'name': "Tariq Mahmoud",
            'nationality': "Egyptian",
            'phone_number': "+966 54 999 1122",
            'passport_number': "EG987654",
            'iqama_expiry': date.today() + timedelta(days=45),
            'joining_date': date.today() - timedelta(days=200),
            'kafeel_name': "Red Sea Contracting",
            'visa_status': "active",
            'client_company': redsea_company,
            'assigned_client': client_nesma,
            'deployment_status': "deployed",
            'deployment_date': date.today() - timedelta(days=120),
            'client_project': "Jeddah Islamic Port Logistics Zone",
            'position': "Site Supervisor",
            'basic_salary': 3500.00,
            'receiving_amount': 5500.00,
            'salary_from_account': "Riyad Bank (IBAN: SA1220000004567890)",
            'salary_payment_company': "Red Sea Builders Est.",
            'salary_paid': True,
        }
    )
    emp4.assigned_client = client_nesma
    emp4.deployment_status = "deployed"
    emp4.salary_from_account = "Riyad Bank (IBAN: SA1220000004567890)"
    emp4.salary_payment_company = "Red Sea Builders Est."
    emp4.contract_annual_leave = Decimal('30.00')
    emp4.contract_ticket_frequency = 'every_year'
    emp4.contract_sick_leave = Decimal('15.00')
    emp4.contract_emergency_leave = Decimal('3.00')
    emp4.leave_contract_notes = "Supervisor package: 30 days annual leave with annual Cairo round-trip ticket."
    emp4.save()
    EmployeeProperty.objects.get_or_create(employee=emp4, property=prop3)
    LeaveBalance.objects.get_or_create(employee=emp4, year=date.today().year, defaults={'accrued_balance': 30.00})

    # Worker 2 for Red Sea Builders (UNEMPLOYED / ON BENCH POOL!)
    emp5, _ = Employee.objects.get_or_create(
        iqama_number="2498765432",
        defaults={
            'name': "Bilal Ahmed",
            'nationality': "Bangladeshi",
            'phone_number': "+966 50 222 3344",
            'passport_number': "BD112233",
            'iqama_expiry': date.today() + timedelta(days=12),
            'joining_date': date.today() - timedelta(days=150),
            'kafeel_name': "Red Sea Contracting",
            'visa_status': "active",
            'client_company': redsea_company,
            'assigned_client': None,
            'deployment_status': "available",
            'unemployed_date': date.today() - timedelta(days=14),
            'unemployed_reason': "Demobilized from Red Sea Global project after Phase 1 completion",
            'position': "Mason Foreman",
            'basic_salary': 2200.00,
            'receiving_amount': 3800.00,
            'salary_from_account': "Riyad Bank (IBAN: SA1220000004567890)",
            'salary_payment_company': "Red Sea Builders Est.",
            'salary_paid': False,
        }
    )
    emp5.assigned_client = None
    emp5.deployment_status = "available"
    emp5.unemployed_date = date.today() - timedelta(days=14)
    emp5.unemployed_reason = "Demobilized from Red Sea Global project after Phase 1 completion"
    emp5.salary_from_account = "Riyad Bank (IBAN: SA1220000004567890)"
    emp5.salary_payment_company = "Red Sea Builders Est."
    emp5.contract_annual_leave = Decimal('21.00')
    emp5.contract_ticket_frequency = 'every_2_years'
    emp5.save()
    EmployeeProperty.objects.get_or_create(employee=emp5, property=prop3)
    LeaveBalance.objects.get_or_create(employee=emp5, year=date.today().year, defaults={'accrued_balance': 21.00})


    print("🎉 Demo data successfully seeded!")

if __name__ == '__main__':
    seed()
