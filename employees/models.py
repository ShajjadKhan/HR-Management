from datetime import timedelta
from django.db import models
from django.contrib.auth.models import User

class Company(models.Model):
    name = models.CharField(max_length=100)
    admin_account = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    def __str__(self): return self.name

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
    company_name = models.CharField(max_length=100)
    client_company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, related_name='employees')
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

    class Meta:
        ordering = ['-id']

    def __str__(self): return self.name

class Property(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='properties')
    property_name = models.CharField(max_length=255)
    charge_amount = models.DecimalField(max_digits=10, decimal_places=2, default=2700.00)
    employee_salary = models.DecimalField(max_digits=10, decimal_places=2, default=1200.00)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.property_name

class EmployeeProperty(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='property_assignments')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='assigned_employees')
    assigned_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"{self.employee.name} - {self.property.property_name}"

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
        return days
