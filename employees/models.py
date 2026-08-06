from django.db import models

class Employee(models.Model):
    # Personal
    name = models.CharField(max_length=100)
    nationality = models.CharField(max_length=50)
    photo = models.ImageField(upload_to='photos/', null=True, blank=True)

    # Documents
    iqama_number = models.CharField(max_length=50, unique=True)
    passport_number = models.CharField(max_length=50, unique=True)

    # Dates & Alerts
    iqama_expiry = models.DateField()
    starting_date = models.DateField()
    transfer_dates = models.TextField(blank=True, null=True)

    # Job Placement
    company_name = models.CharField(max_length=100)
    position = models.CharField(max_length=100)

    # Financials
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2)
    receiving_amount = models.DecimalField(max_digits=10, decimal_places=2)
    salary_paid = models.BooleanField(default=False)

    def __str__(self):
        return self.name
