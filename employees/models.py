from datetime import date, timedelta
from decimal import Decimal
import uuid
import secrets
from django.db import models
from django.contrib.auth.models import User

builtin_property = property

class Company(models.Model):
    PLAN_CHOICES = [
        ('starter', 'Starter (up to 25 workers)'),
        ('standard', 'Standard (up to 100 workers)'),
        ('enterprise', 'Enterprise (Unlimited)'),
    ]

    name = models.CharField(max_length=150, verbose_name="Company Name")
    cr_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="CR Number (سجل تجاري)")
    contact_person = models.CharField(max_length=100, blank=True, null=True, verbose_name="Contact Person")
    email = models.EmailField(blank=True, null=True, verbose_name="Contact Email")
    phone = models.CharField(max_length=30, blank=True, null=True, verbose_name="Contact Phone")
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Office Address")
    admin_account = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_company')
    
    BILLING_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly / Annual'),
        ('one_time', 'One-time License'),
    ]

    # Master Admin Access Control
    is_active = models.BooleanField(default=True, verbose_name="Access Status")
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='standard')
    subscription_fee = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00, 
        verbose_name="Subscription Fee (SAR)",
        help_text="Recurring license fee agreed with this company"
    )
    billing_cycle = models.CharField(
        max_length=20,
        choices=BILLING_CHOICES,
        default='yearly',
        verbose_name="Billing Frequency"
    )
    max_employees = models.PositiveIntegerField(default=50, verbose_name="Max Workers Allowed")
    subscription_expiry = models.DateField(null=True, blank=True, verbose_name="Subscription Expiry Date")
    notes = models.TextField(blank=True, null=True, verbose_name="Admin / Contract Notes")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name = "Contracting Company"
        verbose_name_plural = "Contracting Companies"
        ordering = ['-id']

    def __str__(self):
        return self.name

    @property
    def worker_count(self):
        return self.employees.count()

    @property
    def property_count(self):
        return self.properties.count()

    @property
    def days_until_expiry(self):
        """Returns integer days remaining until subscription expires, or None if no date set."""
        from datetime import date
        if self.subscription_expiry:
            return (self.subscription_expiry - date.today()).days
        return None

    @property
    def abs_days_until_expiry(self):
        d = self.days_until_expiry
        return abs(d) if d is not None else None

    @property
    def is_subscription_expired(self):
        d = self.days_until_expiry
        return d is not None and d < 0

    @property
    def is_subscription_expiring_soon(self):
        d = self.days_until_expiry
        return d is not None and 0 <= d <= 30

    @property
    def is_access_granted(self):
        return self.is_active and not self.is_subscription_expired

    @property
    def quota_percentage(self):
        if self.max_employees and self.max_employees > 0:
            return min(100, int((self.worker_count / self.max_employees) * 100))
        return 0

    @property
    def deployed_workers_count(self):
        return self.employees.filter(deployment_status='deployed').count()

    @property
    def unemployed_workers_count(self):
        return self.employees.filter(deployment_status='available').count()

    @property
    def bench_burn_cost(self):
        """Monthly basic salary paid to unemployed/bench workers who are not generating revenue."""
        bench_workers = self.employees.filter(deployment_status='available')
        return sum((emp.basic_salary or Decimal('0.00') for emp in bench_workers), Decimal('0.00'))

    @property
    def total_monthly_client_billing(self):
        """Total monthly receiving amount billed to all clients for deployed workers."""
        deployed = self.employees.filter(deployment_status='deployed')
        return sum((emp.receiving_amount or Decimal('0.00') for emp in deployed), Decimal('0.00'))


class ClientCompany(models.Model):
    """
    Client Company / Customer that hires/contracts workers from this manpower company.
    e.g. Saudi Aramco, Red Sea Global, Nesma & Partners, Qiddiya Investment Co.
    """
    CLIENT_STATUS_CHOICES = [
        ('active', 'Active Client / Ongoing Project (عميل نشط)'),
        ('completed', 'Contract Completed (منتهي)'),
        ('suspended', 'Suspended / On Hold (معلق)'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='clients')
    name = models.CharField(max_length=200, verbose_name="Client Company Name")
    contact_person = models.CharField(max_length=150, blank=True, null=True, verbose_name="Contact Person / Project Manager")
    phone = models.CharField(max_length=50, blank=True, null=True, verbose_name="Contact Phone")
    email = models.EmailField(blank=True, null=True, verbose_name="Contact Email")
    project_name = models.CharField(max_length=200, blank=True, null=True, verbose_name="Project / Site Name")
    project_location = models.CharField(max_length=200, blank=True, null=True, verbose_name="Project Location / City")
    cr_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="CR / Commercial Registration #")
    contract_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="Contract / Agreement #")
    contract_start = models.DateField(blank=True, null=True, verbose_name="Contract Start Date")
    contract_end = models.DateField(blank=True, null=True, verbose_name="Contract End Date")
    status = models.CharField(max_length=20, choices=CLIENT_STATUS_CHOICES, default='active', verbose_name="Project Status")
    notes = models.TextField(blank=True, null=True, verbose_name="Notes & Commercial Terms")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Client Company"
        verbose_name_plural = "Client Companies"
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def deployed_workers(self):
        return self.assigned_employees.filter(deployment_status='deployed')

    @property
    def deployed_workers_count(self):
        return self.deployed_workers.count()

    @property
    def total_monthly_billing(self):
        return sum((emp.receiving_amount or Decimal('0.00') for emp in self.deployed_workers), Decimal('0.00'))

    @property
    def total_basic_cost(self):
        return sum((emp.basic_salary or Decimal('0.00') for emp in self.deployed_workers), Decimal('0.00'))

    @property
    def total_gross_margin(self):
        return self.total_monthly_billing - self.total_basic_cost


class Employee(models.Model):
    VISA_CHOICES = [
        ('active', 'Active / Valid Iqama'),
        ('expired', 'Expired Iqama'),
        ('transfer', 'In Transfer Process'),
        ('exit_reentry', 'Exit / Re-entry Visa'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    nationality = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    photo = models.ImageField(upload_to='photos/', null=True, blank=True)
    iqama_number = models.CharField(max_length=50, unique=True)
    passport_number = models.CharField(max_length=50, unique=True)
    iqama_expiry = models.DateField()
    joining_date = models.DateField()
    transfer_dates = models.DateField(blank=True, null=True, verbose_name="Join Date")
    kafeel_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Sponsor / Kafeel Name")
    visa_status = models.CharField(max_length=20, choices=VISA_CHOICES, default='active')
    company_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Client / Project Name")
    client_company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, related_name='employees')
    client_project = models.CharField(max_length=150, blank=True, null=True, verbose_name="Client Project / Work Location")
    position = models.CharField(max_length=100)
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2)
    receiving_amount = models.DecimalField(max_digits=10, decimal_places=2)
    salary_paid = models.BooleanField(default=False)
    payment_history = models.TextField(blank=True, null=True)
    salary_from_account = models.CharField(max_length=255, blank=True, null=True)
    salary_payment_company = models.CharField(max_length=255, blank=True, null=True)
    additional_note = models.TextField(blank=True, null=True)
    working_place = models.CharField(max_length=255, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    assigned_client = models.ForeignKey(
        ClientCompany, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_employees',
        verbose_name="Assigned Client Company"
    )
    deployment_status = models.CharField(
        max_length=20, 
        choices=[
            ('deployed', 'Deployed at Client (على رأس العمل لدى العميل)'),
            ('available', 'Unemployed / On Bench / Not Hired (غير مسكن / قائمة الانتظار)'),
            ('vacation', 'On Vacation / Leave (إجازة رسمية)'),
            ('terminated', 'Released / Contract Ended (منتهي العقد)'),
        ], 
        default='available',
        verbose_name="Deployment Status"
    )
    deployment_date = models.DateField(
        null=True, 
        blank=True, 
        verbose_name="Current Deployment Start Date"
    )
    unemployed_date = models.DateField(
        null=True, 
        blank=True, 
        verbose_name="Demobilization / Job Loss Date"
    )
    unemployed_reason = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name="Reason Unemployed / Demobilized",
        help_text="e.g. Project completed at client, client cut manpower, awaiting placement"
    )

    # Individual Contractual Leave Entitlement (Contract-specific terms)
    contract_annual_leave = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('21.00'),
        verbose_name="Contract Annual Leave (Days/Year)",
        help_text="Committed annual leave days in worker's employment contract (e.g. 21 standard, 30 for engineers, 42 for 2-year cycle)."
    )
    contract_carry_forward = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('15.00'),
        verbose_name="Carry Forward Limit (Days)",
        help_text="Max unused leave days allowed to roll over to next year."
    )
    contract_sick_leave = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('10.00'),
        verbose_name="Paid Sick Leave (Days/Year)",
        help_text="Paid sick leave days committed in contract per year."
    )
    contract_emergency_leave = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('2.00'),
        verbose_name="Emergency / Casual Leave (Days/Year)",
        help_text="Emergency leave days committed in contract per year."
    )
    contract_allow_negative = models.BooleanField(
        default=False, 
        verbose_name="Allow Advance / Negative Leave",
        help_text="Permit worker to request advance leave beyond current accrued balance."
    )
    contract_negative_limit = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('5.00'),
        verbose_name="Max Advance Leave (Days)",
        help_text="Maximum advance leave days allowed if negative balance is enabled."
    )
    contract_ticket_frequency = models.CharField(
        max_length=50, 
        default='every_year',
        choices=[
            ('every_year', 'Annual Flight Ticket (تذكرة سنوية)'),
            ('every_2_years', 'Every 2 Years Flight Ticket (تذكرة كل سنتين)'),
            ('none', 'No Flight Ticket Entitlement (بدون تذكرة سفر)'),
        ],
        verbose_name="Flight Ticket Entitlement"
    )
    leave_contract_notes = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Contract Leave Stipulations / Notes",
        help_text="Individual agreement clauses, ticket destination, visa exit re-entry terms, etc."
    )

    class Meta:
        ordering = ['-id']

    def __str__(self): return self.name

    @property
    def company(self):
        return self.client_company

    @company.setter
    def company(self, val):
        self.client_company = val

    @property
    def is_deployed(self):
        return self.deployment_status == 'deployed' and self.assigned_client is not None

    @property
    def is_unemployed_bench(self):
        return self.deployment_status == 'available' or (self.assigned_client is None and self.deployment_status not in ['vacation', 'terminated'])

    @property
    def current_client_display(self):
        if self.assigned_client:
            return self.assigned_client.name
        if self.company_name:
            return self.company_name
        return "Unassigned (Bench / Not Hired)"

    @property
    def profit_margin(self):
        """Monthly gross profit margin generated by this worker (Receiving Amount - Basic Salary)."""
        recv = self.receiving_amount or Decimal('0.00')
        basic = self.basic_salary or Decimal('0.00')
        return recv - basic

    @property
    def profit_margin_pct(self):
        """Gross margin percentage."""
        recv = self.receiving_amount or Decimal('0.00')
        if recv > 0:
            margin = self.profit_margin
            return round((float(margin) / float(recv)) * 100, 1)
        return 0.0

    @property
    def total_spending(self):
        """Total recorded extra spending & expenses on this worker."""
        return sum((exp.amount for exp in self.expenses.all()), Decimal('0.00'))

    @property
    def total_advances_pending(self):
        """Unsettled advance salary to be deducted."""
        return sum((exp.amount for exp in self.expenses.filter(expense_type='advance_salary', is_settled=False)), Decimal('0.00'))

    @property
    def iqama_renewal_total(self):
        return sum((exp.amount for exp in self.expenses.filter(expense_type='iqama_renewal')), Decimal('0.00'))

    @property
    def transport_total(self):
        return sum((exp.amount for exp in self.expenses.filter(expense_type='transport')), Decimal('0.00'))

    @property
    def sick_leave_total(self):
        return sum((exp.amount for exp in self.expenses.filter(expense_type='sick_leave')), Decimal('0.00'))

    @property
    def vacation_total(self):
        return sum((exp.amount for exp in self.expenses.filter(expense_type='vacation')), Decimal('0.00'))

    @property
    def accrual_total(self):
        return sum((exp.amount for exp in self.expenses.filter(expense_type='accrual')), Decimal('0.00'))

    @property
    def effective_annual_leave(self):
        return self.contract_annual_leave if self.contract_annual_leave is not None else Decimal('21.00')

    @property
    def effective_carry_forward(self):
        return self.contract_carry_forward if self.contract_carry_forward is not None else Decimal('15.00')

    @property
    def effective_sick_leave(self):
        return self.contract_sick_leave if self.contract_sick_leave is not None else Decimal('10.00')

    @property
    def effective_emergency_leave(self):
        return self.contract_emergency_leave if self.contract_emergency_leave is not None else Decimal('2.00')


HOUSING_TYPE_CHOICES = [
    ('client_provided', 'Client-Provided Site Camp (Free - SAR 0.00) / سكن موقع موفر من العميل'),
    ('company_rented', 'Company-Rented Camp / Building / سكن مستأجر من الشركة'),
    ('worker_provided', 'Worker Self-Housing / Allowance / سكن فردي أو بدل سكن'),
]

class Property(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='properties')
    property_name = models.CharField(max_length=255, verbose_name="Accommodation / Camp Name")
    housing_type = models.CharField(
        max_length=30, 
        choices=HOUSING_TYPE_CHOICES, 
        default='company_rented',
        verbose_name="Housing Type / Provider"
    )
    location = models.CharField(max_length=255, blank=True, null=True, verbose_name="Camp Location / Site Address")
    capacity = models.PositiveIntegerField(
        default=0, 
        verbose_name="Bed / Resident Capacity",
        help_text="Total number of bed spaces available in this camp/property."
    )
    cost_to_company = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        verbose_name="Camp Rent / Cost to Company (SAR/month)",
        help_text="Monthly rent or facility cost paid by our company to the camp landlord/operator. 0.00 if client-provided."
    )
    charge_to_client = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        verbose_name="Housing Invoiced to Client (SAR/month)",
        help_text="Monthly amount invoiced to client company for accommodation. 0.00 if client-provided or bundled in worker rate."
    )
    worker_deduction = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        verbose_name="Worker Salary Deduction (SAR/month)",
        help_text="Amount deducted from worker's monthly salary for housing. 0.00 if housing is provided free."
    )
    charge_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        verbose_name="Monthly Charge (SAR)"
    )
    employee_salary = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        verbose_name="Salary Base / Deduction (SAR)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Accommodation Property"
        verbose_name_plural = "Accommodation Properties"

    def __str__(self):
        return self.property_name

    def save(self, *args, **kwargs):
        if self.housing_type == 'client_provided':
            self.cost_to_company = Decimal('0.00')
            self.charge_to_client = Decimal('0.00')
            self.worker_deduction = Decimal('0.00')
        
        # Keep legacy fields synced for backward compatibility
        if self.charge_to_client is not None:
            self.charge_amount = self.charge_to_client
        elif self.housing_type == 'client_provided':
            self.charge_amount = Decimal('0.00')

        if self.worker_deduction is not None:
            self.employee_salary = self.worker_deduction
        elif self.housing_type == 'client_provided':
            self.employee_salary = Decimal('0.00')

        super().save(*args, **kwargs)

    @property
    def occupied_beds(self):
        return self.assigned_employees.count()

    @property
    def available_beds(self):
        if self.capacity and self.capacity > 0:
            return max(0, self.capacity - self.occupied_beds)
        return None

    @property
    def is_client_provided(self):
        return self.housing_type == 'client_provided' or (self.cost_to_company == Decimal('0.00') and (self.charge_to_client == Decimal('0.00') or self.charge_amount == Decimal('0.00')))



class EmployeeProperty(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='property_assignments')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='assigned_employees')
    custom_charge = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Custom Charge for Worker (SAR)",
        help_text="Leave blank to use property charge. Set 0.00 if client-provided for this worker."
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Employee Accommodation Assignment"
        verbose_name_plural = "Employee Accommodation Assignments"

    def __str__(self):
        return f"{self.employee.name} - {self.property.property_name}"

    @builtin_property
    def effective_charge(self):
        if self.custom_charge is not None:
            return self.custom_charge
        return self.property.charge_amount if self.property else Decimal('0.00')

    @builtin_property
    def is_client_provided(self):
        return self.effective_charge == Decimal('0.00')


class EmployeeExpense(models.Model):
    EXPENSE_TYPES = [
        ('iqama_renewal', 'Iqama Renewal (تجديد إقامة)'),
        ('advance_salary', 'Advance Salary / Loan (سلفة راتب)'),
        ('transport', 'Transportation / Travel (مواصلات وترحيل)'),
        ('sick_leave', 'Sick Leave / Medical (إجازة مرضية وتأمين طبي)'),
        ('vacation', 'Vacation / Exit-Reentry / Ticket (تذاكر وتأشيرات إجازة)'),
        ('accrual', 'Accrual / EOSB Gratuity (مستحقات نهاية الخدمة)'),
        ('other', 'Other Expense (مصاريف أخرى)'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='expenses')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='expenses')
    expense_type = models.CharField(max_length=30, choices=EXPENSE_TYPES, verbose_name="Expense Category")
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Amount (SAR)")
    expense_date = models.DateField(default=date.today, verbose_name="Date")
    notes = models.TextField(blank=True, null=True, verbose_name="Description / Notes")
    deduct_from_salary = models.BooleanField(
        default=False, 
        verbose_name="Deduct from monthly salary",
        help_text="Check if this amount (e.g. advance salary) should be deducted from monthly salary payment"
    )
    is_settled = models.BooleanField(default=False, verbose_name="Settled / Paid Off")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-expense_date', '-id']
        verbose_name = "Employee Spending Record"
        verbose_name_plural = "Employee Spending Records"

    def __str__(self):
        return f"{self.employee.name} - {self.get_expense_type_display()} (SAR {self.amount})"


class SalaryDisbursement(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('bank_transfer', 'Bank Transfer / WPS (تحويل بنكي / حماية الأجور)'),
        ('cash', 'Cash (نقداً)'),
        ('cheque', 'Cheque (شيك مصرفي)'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='salary_disbursements')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='salary_disbursements')
    month = models.PositiveSmallIntegerField(verbose_name="Disbursement Month")  # 1 to 12
    year = models.PositiveIntegerField(verbose_name="Disbursement Year")          # e.g. 2026
    disbursement_date = models.DateField(default=date.today, verbose_name="Payment Date")
    
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Contract Basic Salary")
    advances_deducted = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name="Advances Deducted")
    other_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name="Other Deductions")
    net_payable = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Net Payable")
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Amount Disbursed")
    
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES, default='bank_transfer', verbose_name="Payment Method")
    disbursing_account = models.CharField(max_length=255, blank=True, null=True, verbose_name="Disbursing Account / IBAN")
    reference_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="Transaction Reference # / Slip #")
    receipt_doc = models.FileField(upload_to='salary_receipts/', null=True, blank=True, verbose_name="Payment Receipt / Voucher")
    notes = models.TextField(blank=True, null=True, verbose_name="Disbursement Notes")
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-year', '-month', '-disbursement_date', '-id']
        unique_together = ('employee', 'month', 'year')
        verbose_name = "Salary Disbursement"
        verbose_name_plural = "Salary Disbursements"

    def __str__(self):
        return f"{self.employee.name} - {self.month}/{self.year} (SAR {self.amount_paid})"


class LeavePolicy(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='leave_policies')
    yearly_leave = models.DecimalField(max_digits=5, decimal_places=2, default=21.00)
    carry_forward_limit = models.DecimalField(max_digits=5, decimal_places=2, default=15.00)
    sick_leave_per_year = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    emergency_leave_per_year = models.DecimalField(max_digits=5, decimal_places=2, default=2.00)
    allow_negative = models.BooleanField(default=False)
    negative_limit = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    def __str__(self): return f"Policy for {self.company.name}"

class LeaveBalance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_balances')
    year = models.IntegerField()
    accrued_balance = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    carried_forward_balance = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    used_balance = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    sick_used = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    emergency_used = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    negative_balance = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    class Meta:
        unique_together = ('employee', 'year')
    def __str__(self): return f"{self.employee.name} - {self.year}"

    @property
    def remaining_annual_leave(self):
        return (self.accrued_balance + self.carried_forward_balance) - self.used_balance

    @property
    def remaining_sick_leave(self):
        return max(Decimal('0.00'), self.employee.effective_sick_leave - self.sick_used)

    @property
    def remaining_emergency_leave(self):
        return max(Decimal('0.00'), self.employee.effective_emergency_leave - self.emergency_used)

class LeaveRequest(models.Model):
    LEAVE_TYPES = [
        ('annual', 'Annual Leave'),
        ('sick', 'Sick Leave'),
        ('emergency', 'Emergency Leave'),
    ]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    is_half_day = models.BooleanField(default=False)
    reason = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=[('pending','Pending'),('approved','Approved'),('rejected','Rejected')], default='pending')
    applied_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_leaves')
    approved_at = models.DateTimeField(null=True, blank=True)
    unpaid_days = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    attachment = models.FileField(upload_to='leave_attachments/', null=True, blank=True)
    def __str__(self): return f"{self.employee.name} - {self.leave_type} - {self.status}"

    @property
    def total_days_worked(self):
        # counts days excluding Fridays and Saturdays
        delta = (self.end_date - self.start_date).days + 1
        days = 0
        for i in range(delta):
            d = self.start_date + timedelta(days=i)
            if d.weekday() not in [4,5]:  # Friday=4, Saturday=5
                days += 1
        if self.is_half_day:
            days = max(0.5, days - 0.5)
        return Decimal(str(days))

class Holiday(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='holidays')
    holiday_date = models.DateField()
    name = models.CharField(max_length=255)
    def __str__(self): return f"{self.name} - {self.holiday_date}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"Notification for {self.user.username}"


# ================== MANPOWER JOB SOCIAL MARKETPLACE & VERIFIED HIRING ==================

class OneTimeReferralLink(models.Model):
    """
    Invite-only one-time referral link model.
    Guarantees anti-spam, crime prevention, and accountability by tracking exactly who referred whom.
    Links cannot be reused once consumed.
    """
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_referrals')
    created_by_company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='company_referrals')
    label_note = models.CharField(max_length=255, blank=True, null=True, help_text="Note on who this invite is intended for")
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    used_by = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='used_referral_link')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "One-Time Referral Link"
        verbose_name_plural = "One-Time Referral Links"

    def __str__(self):
        status = "USED" if self.is_used else "ACTIVE"
        return f"Invite #{self.id} [{status}] by {self.created_by.username} ({self.token[:8]}...)"

    def is_valid(self):
        if self.is_used:
            return False
        if self.expires_at:
            from django.utils import timezone
            if self.expires_at < timezone.now():
                return False
        return True

    @classmethod
    def generate_link(cls, user, company=None, label_note=None, valid_days=14):
        token = secrets.token_urlsafe(24)
        expires_at = None
        if valid_days:
            from django.utils import timezone
            expires_at = timezone.now() + timedelta(days=valid_days)
        return cls.objects.create(
            token=token,
            created_by=user,
            created_by_company=company,
            label_note=label_note,
            expires_at=expires_at
        )


class JobSeekerProfile(models.Model):
    """
    Worker / Candidate profile for the private invite-only job platform.
    Requires unique Iqama and unique Phone number for tamper-proof identity.
    Registration is strictly invite-only and requires Master Admin verification.
    """
    STATUS_CHOICES = [
        ('pending_approval', 'Pending Master Admin Verification (بانتظار التحقق والموافقة)'),
        ('active', 'Verified & Active (معتمد ونشط)'),
        ('hired', 'Hired / Contracted (تم التوظيف / على رأس العمل)'),
        ('suspended', 'Suspended / Blacklisted (موقوف / محظور)'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='jobseeker_profile')
    iqama_number = models.CharField(max_length=20, unique=True, db_index=True, verbose_name="Iqama / National ID Number")
    phone_number = models.CharField(max_length=30, unique=True, db_index=True, verbose_name="Mobile / WhatsApp Number")
    full_name = models.CharField(max_length=150, verbose_name="Full Name")
    nationality = models.CharField(max_length=50, verbose_name="Nationality")
    trade = models.CharField(max_length=100, verbose_name="Trade / Craft / Position")
    experience_years = models.PositiveIntegerField(default=1, verbose_name="Years of Experience")
    current_city = models.CharField(max_length=100, verbose_name="Current City / Region")
    iqama_transferable = models.BooleanField(default=True, verbose_name="Transferable Iqama (نقل كفالة)")
    expected_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Expected Salary (SAR)")
    bio_skills = models.TextField(blank=True, null=True, verbose_name="Skills & Certifications")
    cv_document = models.FileField(upload_to='candidate_cvs/', null=True, blank=True, verbose_name="CV / Resume / Certificates")
    
    # Anti-Crime / Accountability Tracking
    referred_by_link = models.ForeignKey(OneTimeReferralLink, on_delete=models.SET_NULL, null=True, blank=True, related_name='registered_jobseekers')
    
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='pending_approval')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_jobseekers')
    approved_at = models.DateTimeField(null=True, blank=True)
    admin_review_notes = models.TextField(blank=True, null=True)

    # Onboarding link
    hired_by_company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='hired_network_workers')
    hired_as_employee = models.OneToOneField('Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='network_candidate_profile')
    hired_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Job Seeker Candidate"
        verbose_name_plural = "Job Seeker Candidates"

    def __str__(self):
        return f"{self.full_name} ({self.trade} - Iqama: {self.iqama_number})"


class JobPost(models.Model):
    """
    Manpower job requirements posted by contracting companies.
    Requires Master Admin review & approval before being published to the private social feed.
    """
    TRADE_CHOICES = [
        ('welding', 'Welding & Fabrication (لحام وحدادة)'),
        ('electrical', 'Electrical & Instrumentation (كهرباء وتحكم)'),
        ('civil_masonry', 'Civil & Masonry (بناء وتلييس وبلاط)'),
        ('carpentry', 'Carpentry & Shuttering (نجارة وحدادة مسلحة)'),
        ('plumbing', 'Plumbing & Pipefitting (سباكة وتمديدات)'),
        ('driving_heavy', 'Heavy Driver / Equipment Operator (سائق ثقيل ومشغل معدات)'),
        ('driving_light', 'Light Driver / Delivery (سائق خفيف وتوصيل)'),
        ('mechanical', 'Mechanical / HVAC (ميكانيكا وتكييف)'),
        ('safety_hse', 'Safety & HSE Officer (مشرف سلامة وصحة مهنية)'),
        ('engineering', 'Engineering & Supervision (هندسة وإشراف فني)'),
        ('general_labor', 'General Contracting Labor (عمالة مهنية ومساعدة)'),
        ('other', 'Other Specialized Trade (مهن تخصصية أخرى)'),
    ]

    STATUS_CHOICES = [
        ('pending_approval', 'Pending Master Admin Review (بانتظار موافقة الإدارة)'),
        ('published', 'Approved & Published (معتمد ومنشور في الشبكة)'),
        ('rejected', 'Rejected / Revision Requested (مرفوض)'),
        ('closed', 'Filled / Closed (مكتمل ومغلق)'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='job_posts', verbose_name="Contracting Company")
    title = models.CharField(max_length=150, verbose_name="Job Title / Requirement")
    trade_category = models.CharField(max_length=30, choices=TRADE_CHOICES, default='general_labor', verbose_name="Trade Category")
    workers_needed = models.PositiveIntegerField(default=1, verbose_name="Number of Workers Needed")
    work_location = models.CharField(max_length=120, verbose_name="Project Location / City (e.g. Riyadh, Neom, Jubail)")
    project_name = models.CharField(max_length=150, blank=True, null=True, verbose_name="Client Project Site / Subcontract")
    
    # Financials & Allowances
    salary_min = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Minimum Salary (SAR)")
    salary_max = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Maximum Salary (SAR)")
    accommodation_provided = models.BooleanField(default=True, verbose_name="Accommodation Provided Free")
    food_provided = models.BooleanField(default=False, verbose_name="Food or Food Allowance Provided")
    transportation_provided = models.BooleanField(default=True, verbose_name="Transportation to Site Provided")
    iqama_transfer_required = models.BooleanField(default=True, verbose_name="Transferable Iqama or Supply Agreement")
    
    experience_years = models.PositiveIntegerField(default=1, verbose_name="Min Years of Experience")
    description = models.TextField(verbose_name="Job Description & Required Certifications")
    
    # Moderation & Visibility
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='pending_approval')
    rejection_reason = models.TextField(blank=True, null=True, verbose_name="Rejection / Moderation Feedback")
    is_featured = models.BooleanField(default=False, verbose_name="Hot / Urgent Requirement")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_jobposts')
    approved_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_featured', '-created_at']
        verbose_name = "Manpower Job Posting"
        verbose_name_plural = "Manpower Job Postings"

    def __str__(self):
        return f"{self.title} ({self.workers_needed} workers) - {self.company.name}"


class JobApplication(models.Model):
    """
    Worker interest / application for a published job posting.
    """
    STATUS_CHOICES = [
        ('applied', 'Applied / Interested (متقدم / مهتم)'),
        ('contacted', 'Contacted / Interviewing (تم التواصل)'),
        ('accepted', 'Accepted for Onboarding (مقبول للتعاقد)'),
        ('declined', 'Declined / Not Suitable (غير مناسب)'),
    ]

    job_post = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name='applications')
    candidate = models.ForeignKey(JobSeekerProfile, on_delete=models.CASCADE, related_name='applications')
    cover_message = models.TextField(blank=True, null=True, verbose_name="Message / Availability Note")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='applied')
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-applied_at']
        unique_together = ('job_post', 'candidate')
        verbose_name = "Job Application / Match"
        verbose_name_plural = "Job Applications / Matches"

    def __str__(self):
        return f"{self.candidate.full_name} -> {self.job_post.title} ({self.status})"
