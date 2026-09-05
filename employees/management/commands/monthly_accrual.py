from django.core.management.base import BaseCommand
from django.utils import timezone
from employees.models import Employee, LeaveBalance, LeavePolicy
from datetime import datetime

class Command(BaseCommand):
    help = 'Run monthly leave accrual for all employees'

    def handle(self, *args, **options):
        today = timezone.now().date()
        current_year = today.year
        current_month = today.month

        employees = Employee.objects.all()
        for emp in employees:
            # Get the leave policy for this employee's company
            policy = LeavePolicy.objects.filter(company=emp.client_company).first()
            if not policy:
                continue
            yearly = policy.yearly_leave
            monthly_accrual = yearly / 12

            # Pro-rata: if joining in current year, count months from joining
            join_date = emp.joining_date
            if join_date.year < current_year:
                months_eligible = current_month
            elif join_date.year == current_year:
                months_eligible = max(0, current_month - join_date.month + 1)
            else:
                continue

            total_accrued = monthly_accrual * months_eligible

            # Get or create balance for this year
            balance, created = LeaveBalance.objects.get_or_create(
                employee=emp,
                year=current_year,
                defaults={'accrued_balance': 0}
            )
            # Update (we set it to the calculated value, not adding)
            balance.accrued_balance = total_accrued
            balance.save()

        self.stdout.write(self.style.SUCCESS('Monthly accrual completed.'))
