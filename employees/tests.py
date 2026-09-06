from datetime import date, timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import (
    Company, Employee, Property, LeavePolicy, ClientCompany, EmployeeProperty,
    EmployeeExpense, SalaryDisbursement, OneTimeReferralLink, JobSeekerProfile,
    JobPost, JobApplication
)

class MultiTenantSaaSTest(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Master Admin (Superuser)
        self.master_user = User.objects.create_superuser(
            username='super_admin',
            email='super@saas.com',
            password='Password123!'
        )

        # 2. Company A (Al-Madina)
        self.user_a = User.objects.create_user(
            username='admin_a',
            email='a@madina.com',
            password='Password123!'
        )
        self.company_a = Company.objects.create(
            name="Al-Madina Contracting",
            cr_number="1010111111",
            admin_account=self.user_a,
            max_employees=2,
            is_active=True
        )
        LeavePolicy.objects.create(company=self.company_a)
        self.emp_a1 = Employee.objects.create(
            name="Worker A1",
            client_company=self.company_a,
            iqama_number="1111111111",
            passport_number="P11111",
            iqama_expiry=date.today() + timedelta(days=60),
            joining_date=date.today(),
            basic_salary=2500,
            receiving_amount=4000
        )

        # 3. Company B (Gulf Apex)
        self.user_b = User.objects.create_user(
            username='admin_b',
            email='b@apex.com',
            password='Password123!'
        )
        self.company_b = Company.objects.create(
            name="Gulf Apex Contracting",
            cr_number="1010222222",
            admin_account=self.user_b,
            max_employees=5,
            is_active=True
        )
        LeavePolicy.objects.create(company=self.company_b)
        self.emp_b1 = Employee.objects.create(
            name="Worker B1",
            client_company=self.company_b,
            iqama_number="2222222222",
            passport_number="P22222",
            iqama_expiry=date.today() + timedelta(days=90),
            joining_date=date.today(),
            basic_salary=3000,
            receiving_amount=4500
        )

    def test_tenant_isolation_employee_list(self):
        """Company A must ONLY see its own workers and not Company B's workers."""
        self.client.login(username='admin_a', password='Password123!')
        response = self.client.get(reverse('employees_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Worker A1")
        self.assertNotContains(response, "Worker B1")

    def test_cross_tenant_detail_view_blocked(self):
        """Company A cannot view Worker B1's details via URL tampering."""
        self.client.login(username='admin_a', password='Password123!')
        response = self.client.get(reverse('employee_detail', args=[self.emp_b1.id]))
        # Must return 404 because Worker B1 does not belong to Company A
        self.assertEqual(response.status_code, 404)

    def test_master_admin_dashboard(self):
        """Master admin can access master dashboard and view all companies."""
        self.client.login(username='super_admin', password='Password123!')
        response = self.client.get(reverse('master_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Al-Madina Contracting")
        self.assertContains(response, "Gulf Apex Contracting")

    def test_company_admin_blocked_from_master_dashboard(self):
        """Regular company admin cannot access master admin dashboard."""
        self.client.login(username='admin_a', password='Password123!')
        response = self.client.get(reverse('master_dashboard'))
        # Should redirect with error
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))

    def test_master_admin_can_toggle_access(self):
        """Master admin can suspend and activate company access."""
        self.client.login(username='super_admin', password='Password123!')
        # Toggle Company A access
        response = self.client.get(reverse('master_company_toggle_access', args=[self.company_a.id]))
        self.company_a.refresh_from_db()
        self.assertFalse(self.company_a.is_active)

        # Now Company A admin tries to access portal
        self.client.login(username='admin_a', password='Password123!')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Company Access Suspended")

    def test_quota_enforcement(self):
        """When worker quota is reached, adding another worker is blocked."""
        self.client.login(username='admin_a', password='Password123!')
        # Company A max_employees is 2, current count is 1.
        # Add 2nd worker
        emp_a2 = Employee.objects.create(
            name="Worker A2",
            client_company=self.company_a,
            iqama_number="1111111112",
            passport_number="P11112",
            iqama_expiry=date.today() + timedelta(days=60),
            joining_date=date.today(),
            basic_salary=2500,
            receiving_amount=4000
        )
        self.assertEqual(self.company_a.worker_count, 2)

        # Attempt to add 3rd worker should be blocked
        response = self.client.get(reverse('employee_add'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('employees_list'))

    def test_master_admin_data_isolation_and_supreme_mode(self):
        """Master Admin cannot roam into customer data casually; requires verified Supreme Mode."""
        self.client.login(username='super_admin', password='Password123!')

        # 1. Direct roaming into tenant pages is BLOCKED by default
        res_direct = self.client.get(reverse('dashboard'))
        self.assertEqual(res_direct.status_code, 302)
        self.assertRedirects(res_direct, reverse('master_dashboard'))

        res_emp_direct = self.client.get(reverse('employees_list'))
        self.assertEqual(res_emp_direct.status_code, 302)
        self.assertRedirects(res_emp_direct, reverse('master_dashboard'))

        # 2. Direct GET to legacy impersonate is also blocked
        res_legacy = self.client.get(reverse('master_company_impersonate', args=[self.company_a.id]))
        self.assertEqual(res_legacy.status_code, 302)
        self.assertRedirects(res_legacy, reverse('master_dashboard'))

        # 3. Attempting Supreme Mode with INVALID password fails
        verify_url = reverse('supreme_mode_verify')
        res_wrong_pw = self.client.post(verify_url, {
            'company_id': self.company_a.id,
            'master_password': 'WrongPassword123!',
            'consent_acknowledged': 'true',
            'access_reason': 'Testing security gate',
        })
        self.assertEqual(res_wrong_pw.status_code, 302)
        self.assertRedirects(res_wrong_pw, reverse('master_dashboard'))
        # Ensure still locked
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 302)

        # 4. Verified Supreme Mode entry with VALID password & consent
        res_valid = self.client.post(verify_url, {
            'company_id': self.company_a.id,
            'master_password': 'Password123!',
            'consent_acknowledged': 'true',
            'access_reason': 'Authorized WPS technical support',
        })
        self.assertEqual(res_valid.status_code, 302)
        self.assertRedirects(res_valid, reverse('dashboard'))

        # 5. Access now granted in Supreme Mode
        res_dash = self.client.get(reverse('dashboard'))
        self.assertEqual(res_dash.status_code, 200)
        self.assertContains(res_dash, "Al-Madina Contracting")
        self.assertContains(res_dash, "SUPREME")

        # 6. Exit Supreme Mode locks tenant workspace again
        res_exit = self.client.get(reverse('supreme_mode_exit'))
        self.assertEqual(res_exit.status_code, 302)
        self.assertRedirects(res_exit, reverse('master_dashboard'))

        # Direct access is locked again
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 302)

    def test_contracting_payroll_and_margins(self):
        """Verify profit margin property and financial calculations."""
        emp = self.emp_a1
        emp.salary_from_account = "Al Rajhi IBAN SA448000"
        emp.salary_payment_company = "Al-Madina Contracting"
        emp.save()

        self.assertEqual(emp.profit_margin, 1500)
        self.assertEqual(emp.profit_margin_pct, 37.5)

        self.client.login(username='admin_a', password='Password123!')
        response = self.client.get(reverse('employees_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Al Rajhi IBAN SA448000")
        self.assertContains(response, "Al-Madina Contracting")
        self.assertContains(response, "+1500.00 SAR")

    def test_subscription_fee_and_countdown_reminders(self):
        """Verify subscription fee tracking, countdown days, and master admin reminders."""
        self.company_a.subscription_fee = 12000.00
        self.company_a.billing_cycle = 'yearly'
        self.company_a.subscription_expiry = date.today() + timedelta(days=15)
        self.company_a.save()

        self.assertEqual(self.company_a.days_until_expiry, 15)
        self.assertTrue(self.company_a.is_subscription_expiring_soon)
        self.assertFalse(self.company_a.is_subscription_expired)

        # Master admin dashboard check
        self.client.login(username='super_admin', password='Password123!')
        response = self.client.get(reverse('master_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SAR 12000.00")
        self.assertContains(response, "Expiring in 15 days")
        self.assertContains(response, "Subscription Expiry Countdown")

    def test_logical_accommodation_fields_and_free_housing(self):
        """Verify new logical housing fields, capacity tracking, and client-provided zero cost."""
        self.client.login(username='admin_a', password='Password123!')

        # 1. Create client-provided accommodation (SAR 0.00 for all fields)
        prop_client = Property.objects.create(
            company=self.company_a,
            property_name="Client Site Labor Compound",
            housing_type="client_provided",
            cost_to_company=0.00,
            charge_to_client=0.00,
            worker_deduction=0.00,
            capacity=40,
            location="NEOM Site Sector 4"
        )
        self.assertTrue(prop_client.is_client_provided)
        self.assertEqual(prop_client.occupied_beds, 0)
        self.assertEqual(prop_client.available_beds, 40)

        # 2. Create company-rented accommodation
        prop_rented = Property.objects.create(
            company=self.company_a,
            property_name="Al-Madina Rented Flats Bldg 2",
            housing_type="company_rented",
            cost_to_company=4500.00,
            charge_to_client=0.00,
            worker_deduction=0.00,
            capacity=10,
            location="Riyadh Industrial"
        )
        self.assertFalse(prop_rented.is_client_provided)

        # Assign Worker A1 to rented camp
        EmployeeProperty.objects.create(employee=self.emp_a1, property=prop_rented)
        self.assertEqual(prop_rented.occupied_beds, 1)
        self.assertEqual(prop_rented.available_beds, 9)

        # 3. View accommodations list
        response = self.client.get(reverse('properties_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Client Site Labor Compound")
        self.assertContains(response, "Al-Madina Rented Flats Bldg 2")
        self.assertContains(response, "Client Site Camp (Free)")
        self.assertContains(response, "SAR 4500.00")

    def test_client_company_and_bench_tracking(self):
        """Verify ClientCompany creation, worker deployment, demobilization to bench, and burn cost."""
        self.client.login(username='admin_a', password='Password123!')

        # 1. Create Client Company
        client_co = ClientCompany.objects.create(
            company=self.company_a,
            name="Red Sea Global",
            project_name="Coastal Village Development",
            project_location="Umluj",
            contact_person="Eng. Fahad",
            phone="+966 50 111 2233",
            status="active"
        )

        # 2. Deploy Worker A1 to client
        response = self.client.post(
            reverse('employee_assign_client', args=[self.emp_a1.id]),
            {
                'action': 'assign',
                'client_id': client_co.id,
                'deployment_date': str(date.today()),
                'project_site': 'Coastal Village Sector 1'
            }
        )
        self.assertEqual(response.status_code, 302)
        self.emp_a1.refresh_from_db()
        self.assertEqual(self.emp_a1.deployment_status, 'deployed')
        self.assertEqual(self.emp_a1.assigned_client, client_co)
        self.assertTrue(self.emp_a1.is_deployed)
        self.assertFalse(self.emp_a1.is_unemployed_bench)

        # Check client metrics
        self.assertEqual(client_co.deployed_workers_count, 1)
        self.assertEqual(client_co.total_monthly_billing, 4000)

        # Check company KPIs
        self.assertEqual(self.company_a.deployed_workers_count, 1)
        self.assertEqual(self.company_a.unemployed_workers_count, 0)
        self.assertEqual(self.company_a.bench_burn_cost, 0)

        # 3. Demobilize worker (worker loses job / project finished)
        response = self.client.post(
            reverse('employee_assign_client', args=[self.emp_a1.id]),
            {
                'action': 'demobilize',
                'reason': 'Project contract completed at client site',
                'unemployed_date': str(date.today())
            }
        )
        self.assertEqual(response.status_code, 302)
        self.emp_a1.refresh_from_db()
        self.assertEqual(self.emp_a1.deployment_status, 'available')
        self.assertIsNone(self.emp_a1.assigned_client)
        self.assertTrue(self.emp_a1.is_unemployed_bench)
        self.assertEqual(self.emp_a1.unemployed_reason, 'Project contract completed at client site')

        # Company bench KPI should reflect idle cost
        self.assertEqual(self.company_a.unemployed_workers_count, 1)
        self.assertEqual(self.company_a.bench_burn_cost, 2500)

        # 4. Access Clients Directory & Bench Pool UI
        response = self.client.get(reverse('clients_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Red Sea Global")

        response_bench = self.client.get(reverse('clients_list') + '?tab=bench')
        self.assertEqual(response_bench.status_code, 200)
        self.assertContains(response_bench, "Worker A1")
        self.assertContains(response_bench, "Project contract completed at client site")
        self.assertContains(response_bench, "SAR 2500.00")

    def test_individual_contract_leave_terms_and_roster(self):
        """Verify individual contract leave customization per worker and roster on policy page."""
        self.client.login(username='admin_a', password='Password123!')

        # 1. Default contract values on Worker A1
        self.assertEqual(self.emp_a1.contract_annual_leave, 21.00)
        self.assertEqual(self.emp_a1.effective_annual_leave, 21.00)
        self.assertEqual(self.emp_a1.effective_sick_leave, 10.00)

        # 2. Update Worker A1's individual contract to 30 days (Senior/Supervisor contract)
        edit_url = reverse('employee_leave_contract_edit', args=[self.emp_a1.id])
        response = self.client.post(edit_url, {
            'contract_annual_leave': '30.00',
            'contract_carry_forward': '20.00',
            'contract_sick_leave': '15.00',
            'contract_emergency_leave': '5.00',
            'contract_allow_negative': True,
            'contract_negative_limit': '10.00',
            'contract_ticket_frequency': 'every_year',
            'leave_contract_notes': 'Senior engineer package with 30 days leave and annual ticket',
            'sync_leave_balance': True,
        })
        self.assertEqual(response.status_code, 302)
        self.emp_a1.refresh_from_db()
        self.assertEqual(self.emp_a1.contract_annual_leave, 30.00)
        self.assertEqual(self.emp_a1.effective_annual_leave, 30.00)
        self.assertEqual(self.emp_a1.effective_sick_leave, 15.00)
        self.assertEqual(self.emp_a1.effective_emergency_leave, 5.00)
        self.assertTrue(self.emp_a1.contract_allow_negative)
        self.assertEqual(self.emp_a1.contract_ticket_frequency, 'every_year')

        # 3. Check synced LeaveBalance
        from .models import LeaveBalance
        bal = LeaveBalance.objects.get(employee=self.emp_a1, year=date.today().year)
        self.assertEqual(bal.accrued_balance, 30.00)
        self.assertEqual(bal.remaining_annual_leave, 30.00)
        self.assertEqual(bal.remaining_sick_leave, 15.00)

        # 4. Access Policy Edit page and verify roster displays individual worker contract
        policy_url = reverse('policy_edit')
        res_policy = self.client.get(policy_url)
        self.assertEqual(res_policy.status_code, 200)
        self.assertContains(res_policy, "Worker A1")
        self.assertContains(res_policy, "30.00 days/yr")
        self.assertContains(res_policy, "1. Company Baseline Default Template")
        self.assertContains(res_policy, "2. Individual Worker Contract Commitments")

    def test_salary_disbursement_flow_with_advance_deduction(self):
        """Test full salary disbursement lifecycle with automatic advance deduction and settlement."""
        from decimal import Decimal
        from .models import EmployeeExpense, SalaryDisbursement

        self.client.login(username='admin_a', password='Password123!')

        # 1. Give Worker A1 an advance salary of SAR 500
        adv = EmployeeExpense.objects.create(
            company=self.company_a,
            employee=self.emp_a1,
            expense_type='advance_salary',
            amount=Decimal('500.00'),
            expense_date=date.today(),
            notes='Emergency advance',
            deduct_from_salary=True,
            is_settled=False
        )

        # 2. Visit Salary Disbursements roster
        today = date.today()
        roster_url = reverse('salary_disbursements')
        res = self.client.get(f"{roster_url}?month={today.month}&year={today.year}")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Worker A1")
        self.assertContains(res, "#1")  # Serial number
        self.assertContains(res, "SAR 2500.00")  # Basic Salary
        self.assertContains(res, "- SAR 500.00")  # Advance Deducted
        self.assertContains(res, "SAR 2000.00")  # Net Rest Payable

        # 3. Disburse Salary via submit endpoint
        disburse_url = reverse('salary_disburse_submit', args=[self.emp_a1.id])
        disburse_res = self.client.post(disburse_url, {
            'month': today.month,
            'year': today.year,
            'disbursement_date': today.isoformat(),
            'amount_paid': '2000.00',
            'payment_method': 'bank_transfer',
            'disbursing_account': 'SA4480000123456789012345',
            'reference_number': 'WPS-REF-TEST-001',
            'settle_advances': True,
            'notes': 'Disbursed via WPS with advance deduction',
        })
        self.assertEqual(disburse_res.status_code, 302)

        # 4. Verify SalaryDisbursement record was created
        disb = SalaryDisbursement.objects.get(
            company=self.company_a,
            employee=self.emp_a1,
            month=today.month,
            year=today.year
        )
        self.assertEqual(disb.basic_salary, Decimal('2500.00'))
        self.assertEqual(disb.advances_deducted, Decimal('500.00'))
        self.assertEqual(disb.net_payable, Decimal('2000.00'))
        self.assertEqual(disb.amount_paid, Decimal('2000.00'))
        self.assertEqual(disb.payment_method, 'bank_transfer')
        self.assertEqual(disb.reference_number, 'WPS-REF-TEST-001')

        # 5. Verify advance was marked settled
        adv.refresh_from_db()
        self.assertTrue(adv.is_settled)

        # 6. Verify employee payment history was updated
        self.emp_a1.refresh_from_db()
        self.assertIn("WPS", self.emp_a1.payment_history)
        self.assertIn("2000.00", self.emp_a1.payment_history)

        # 7. Check roster again - status should now show Paid
        res_after = self.client.get(f"{roster_url}?month={today.month}&year={today.year}")
        self.assertEqual(res_after.status_code, 200)
        self.assertContains(res_after, "Paid SAR 2000.00")
        self.assertContains(res_after, "Edit Slip")


class JobMarketplaceAndReferralSecurityTest(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Master Admin
        self.master_user = User.objects.create_superuser(
            username='master_admin_hq',
            email='hq@saas.com',
            password='Password123!'
        )

        # 2. Contracting Company Admin
        self.company_user = User.objects.create_user(
            username='contractor_admin',
            email='contractor@saas.com',
            password='Password123!'
        )
        self.company = Company.objects.create(
            name="Red Sea Contracting Est.",
            cr_number="1010333333",
            admin_account=self.company_user,
            max_employees=10,
            is_active=True
        )
        LeavePolicy.objects.create(company=self.company)

        # 3. Generate One-Time Referral Link by Master Admin
        self.referral_link = OneTimeReferralLink.generate_link(
            user=self.master_user,
            label_note="Dammam Skilled Electricians Batch",
            valid_days=14
        )

    def test_referral_link_creation(self):
        """One-time link is created with cryptographically random token and starts active."""
        self.assertIsNotNone(self.referral_link.token)
        self.assertFalse(self.referral_link.is_used)
        self.assertIsNone(self.referral_link.used_by)
        self.assertTrue(self.referral_link.is_valid())

    def test_candidate_registration_without_token_blocked(self):
        """Registration without a valid referral token is strictly blocked."""
        response = self.client.get(reverse('candidate_register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Strictly Invite-Only")

    def test_candidate_registration_with_valid_token_consumes_token(self):
        """Registration consumes the single-use token and creates pending candidate profile."""
        reg_data = {
            'referral_token': self.referral_link.token,
            'username': 'ahmed_electrician',
            'password': 'Password123!',
            'confirm_password': 'Password123!',
            'full_name': 'Ahmed Al-Mansoor',
            'nationality': 'Egyptian',
            'iqama_number': '2345678901',
            'phone_number': '0551234567',
            'trade': 'Electrician',
            'experience_years': 5,
            'current_city': 'Riyadh',
            'expected_salary': '3500.00',
            'iqama_transferable': True,
            'bio_skills': 'Experienced in industrial cabling and switchboards.'
        }
        response = self.client.post(f"{reverse('candidate_register')}?ref={self.referral_link.token}", reg_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login'))

        # Check referral link is now consumed (is_used=True)
        self.referral_link.refresh_from_db()
        self.assertTrue(self.referral_link.is_used)
        self.assertIsNotNone(self.referral_link.used_by)
        self.assertEqual(self.referral_link.used_by.username, 'ahmed_electrician')

        # Check candidate profile was created in pending_approval status
        profile = JobSeekerProfile.objects.get(iqama_number='2345678901')
        self.assertEqual(profile.full_name, 'Ahmed Al-Mansoor')
        self.assertEqual(profile.phone_number, '0551234567')
        self.assertEqual(profile.status, 'pending_approval')
        self.assertEqual(profile.referred_by_link, self.referral_link)

    def test_consumed_token_cannot_be_reused(self):
        """Once a referral link is used, second registration attempt fails (single-use)."""
        # Consume the link
        self.referral_link.is_used = True
        self.referral_link.save()

        response = self.client.get(f"{reverse('candidate_register')}?ref={self.referral_link.token}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Already Consumed")

    def test_duplicate_iqama_or_phone_rejected(self):
        """Candidate registration rejects duplicate Iqama or duplicate Phone."""
        # Create first candidate
        user1 = User.objects.create_user(username='cand1', password='Password123!')
        JobSeekerProfile.objects.create(
            user=user1,
            iqama_number='2999999999',
            phone_number='0509999999',
            full_name='Worker One',
            nationality='Pakistani',
            trade='Mason',
            experience_years=3,
            current_city='Jeddah',
            expected_salary=2500,
            status='active'
        )

        # Try to register second candidate with same Iqama
        link2 = OneTimeReferralLink.generate_link(user=self.master_user)
        reg_data_dup = {
            'referral_token': link2.token,
            'username': 'cand2',
            'password': 'Password123!',
            'confirm_password': 'Password123!',
            'full_name': 'Worker Two',
            'nationality': 'Indian',
            'iqama_number': '2999999999',  # Duplicate Iqama
            'phone_number': '0508888888',
            'trade': 'Mason',
            'experience_years': 4,
            'current_city': 'Dammam',
            'expected_salary': '2700.00',
        }
        res = self.client.post(f"{reverse('candidate_register')}?ref={link2.token}", reg_data_dup)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "already exists")
        link2.refresh_from_db()
        self.assertFalse(link2.is_used)  # Link remains unused if registration fails validation

    def test_company_posts_job_requires_master_admin_approval(self):
        """Company posts job requirement -> goes to pending_approval -> approved by Master Admin."""
        self.client.login(username='contractor_admin', password='Password123!')

        job_data = {
            'title': 'Need 5 HVAC Technicians for Commercial Mall Project',
            'trade_category': 'mechanical',
            'workers_needed': 5,
            'work_location': 'Riyadh',
            'project_name': 'Al-Nakheel Expansion',
            'salary_min': '3000.00',
            'salary_max': '3500.00',
            'experience_years': 3,
            'accommodation_provided': True,
            'food_provided': False,
            'transportation_provided': True,
            'iqama_transfer_required': False,
            'description': 'Experienced in ducting, VRV installation, and commissioning.'
        }
        res = self.client.post(reverse('company_job_add'), job_data, follow=True)
        self.assertEqual(res.status_code, 200)

        job = JobPost.objects.get(company=self.company, trade_category='mechanical')
        self.assertEqual(job.status, 'pending_approval')
        self.assertIsNone(job.approved_by)

        # Job must NOT be visible on public social feed yet
        feed_res = self.client.get(reverse('jobs_feed'))
        self.assertNotIn(job, feed_res.context['jobs'])
        self.assertNotContains(feed_res, "Need 5 HVAC Technicians")

        # Master Admin logs in and approves job
        self.client.login(username='master_admin_hq', password='Password123!')
        approve_res = self.client.get(reverse('master_job_post_approve', args=[job.id]))
        self.assertEqual(approve_res.status_code, 302)

        job.refresh_from_db()
        self.assertEqual(job.status, 'published')
        self.assertEqual(job.approved_by, self.master_user)

        # Now job appears on social feed
        feed_res_after = self.client.get(reverse('jobs_feed'))
        self.assertContains(feed_res_after, "Need 5 HVAC Technicians")

    def test_two_matched_fast_onboarding_success_and_failure(self):
        """
        Two-matched entry:
        - Fails if phone number does not match Iqama number.
        - Succeeds when BOTH Iqama and Phone match an approved candidate.
        - Converts candidate into an Employee under the hiring company and marks profile as 'hired'.
        """
        # Create an approved candidate
        cand_user = User.objects.create_user(username='khalid_welder', password='Password123!')
        candidate = JobSeekerProfile.objects.create(
            user=cand_user,
            iqama_number='2444555666',
            phone_number='0559876543',
            full_name='Khalid Rahman',
            nationality='Bangladeshi',
            trade='Welder',
            experience_years=6,
            current_city='Dammam',
            expected_salary=3200,
            status='active'
        )

        self.client.login(username='contractor_admin', password='Password123!')

        # 1. Attempt with WRONG phone number -> Verification must fail!
        fail_data = {
            'iqama_number': '2444555666',
            'phone_number': '0550000000',  # Wrong phone number!
            'position': 'Pipe Welder 6G',
            'joining_date': date.today().isoformat(),
            'basic_salary': '3200.00',
            'receiving_amount': '4500.00',
        }
        fail_res = self.client.post(reverse('company_two_matched_onboard'), fail_data)
        self.assertEqual(fail_res.status_code, 200)
        self.assertContains(fail_res, "Two-Matched Verification FAILED")
        self.assertFalse(Employee.objects.filter(iqama_number='2444555666').exists())

        # 2. Attempt with MATCHING Iqama + MATCHING Phone -> Verification succeeds!
        success_data = {
            'iqama_number': '2444555666',
            'phone_number': '0559876543',  # Exactly matches candidate profile!
            'position': 'Pipe Welder 6G',
            'joining_date': date.today().isoformat(),
            'basic_salary': '3200.00',
            'receiving_amount': '4500.00',
        }
        success_res = self.client.post(reverse('company_two_matched_onboard'), success_data)
        self.assertEqual(success_res.status_code, 302)

        # Worker now exists in company's employee roster
        emp = Employee.objects.get(iqama_number='2444555666', client_company=self.company)
        self.assertEqual(emp.name, 'Khalid Rahman')
        self.assertEqual(emp.phone_number, '0559876543')
        self.assertEqual(emp.position, 'Pipe Welder 6G')
        self.assertEqual(emp.basic_salary, 3200)
        self.assertEqual(emp.receiving_amount, 4500)

        # Candidate profile status is updated to 'hired'
        candidate.refresh_from_db()
        self.assertEqual(candidate.status, 'hired')
        self.assertEqual(candidate.hired_by_company, self.company)
        self.assertEqual(candidate.hired_as_employee, emp)

