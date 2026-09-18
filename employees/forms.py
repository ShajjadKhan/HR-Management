from datetime import date
from django import forms
from django.contrib.auth.models import User
from .models import (
    LeaveRequest, Employee, Property, Holiday, LeavePolicy, Company, 
    EmployeeExpense, ClientCompany, SalaryDisbursement,
    JobPost, OneTimeReferralLink, JobSeekerProfile, JobApplication
)

class CompanyOnboardForm(forms.ModelForm):
    admin_username = forms.CharField(
        max_length=150, 
        required=True, 
        label="Admin Username",
        help_text="Login username for this company's administrator",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. almadina_admin'})
    )
    admin_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter login password'}),
        required=True,
        label="Admin Password",
        help_text="Minimum 6 characters recommended"
    )
    admin_email = forms.EmailField(
        required=True,
        label="Admin Login Email",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'admin@company.com'})
    )

    class Meta:
        model = Company
        fields = [
            'name', 'cr_number', 'contact_person', 'phone', 'email', 'address',
            'plan', 'subscription_fee', 'billing_cycle', 'max_employees', 
            'subscription_expiry', 'is_active', 'notes'
        ]
        labels = {
            'name': 'Company Legal Name',
            'cr_number': 'CR Number (سجل تجاري)',
            'contact_person': 'Primary Contact Person',
            'phone': 'Contact Phone Number',
            'email': 'Official Contact Email',
            'address': 'Office Address / HQ',
            'plan': 'Subscription Tier / Plan',
            'subscription_fee': 'Subscription Fee (SAR)',
            'billing_cycle': 'Billing Frequency',
            'max_employees': 'Maximum Worker Quota',
            'subscription_expiry': 'Subscription Expiry Date',
            'is_active': 'Platform Access Enabled',
            'notes': 'Sales & Agreement Notes',
        }
        help_texts = {
            'subscription_fee': 'Recurring contract fee agreed with this company in SAR.',
            'billing_cycle': 'How frequently this fee is charged.',
            'subscription_expiry': 'Access is automatically suspended once this date passes unless renewed.',
            'max_employees': 'Maximum number of workers this company is permitted to register.',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Al-Madina Contracting Co.'}),
            'cr_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 1010892341'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+966 5X XXX XXXX'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'company@domain.com'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City, District, Street'}),
            'plan': forms.Select(attrs={'class': 'form-select'}),
            'subscription_fee': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 12000.00', 'step': '0.01'}),
            'billing_cycle': forms.Select(attrs={'class': 'form-select'}),
            'max_employees': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'subscription_expiry': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Contract agreement details, sales notes, payment terms...'}),
        }

    def clean_admin_username(self):
        username = self.cleaned_data.get('admin_username', '').strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(f"The username '{username}' is already taken. Please choose a different one.")
        return username

class CompanyEditForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = [
            'name', 'cr_number', 'contact_person', 'phone', 'email', 'address',
            'plan', 'subscription_fee', 'billing_cycle', 'max_employees', 
            'subscription_expiry', 'is_active', 'notes'
        ]
        labels = {
            'name': 'Company Legal Name',
            'cr_number': 'CR Number (سجل تجاري)',
            'contact_person': 'Primary Contact Person',
            'phone': 'Contact Phone Number',
            'email': 'Official Contact Email',
            'address': 'Office Address / HQ',
            'plan': 'Subscription Tier / Plan',
            'subscription_fee': 'Subscription Fee (SAR)',
            'billing_cycle': 'Billing Frequency',
            'max_employees': 'Maximum Worker Quota',
            'subscription_expiry': 'Subscription Expiry Date',
            'is_active': 'Platform Access Enabled',
            'notes': 'Sales & Agreement Notes',
        }
        help_texts = {
            'subscription_fee': 'Recurring contract fee agreed with this company in SAR.',
            'billing_cycle': 'How frequently this fee is charged.',
            'subscription_expiry': 'Access is automatically suspended once this date passes unless renewed.',
            'max_employees': 'Maximum number of workers this company is permitted to register.',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'cr_number': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'plan': forms.Select(attrs={'class': 'form-select'}),
            'subscription_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'billing_cycle': forms.Select(attrs={'class': 'form-select'}),
            'max_employees': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'subscription_expiry': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class CompanyPasswordResetForm(forms.Form):
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New Password'}),
        label="New Password",
        min_length=6
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm New Password'}),
        label="Confirm Password"
    )

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('new_password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['leave_type', 'start_date', 'end_date', 'is_half_day', 'reason', 'attachment']
        widgets = {
            'leave_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'is_half_day': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }

class EmployeeForm(forms.ModelForm):
    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            self.fields['assigned_client'].queryset = ClientCompany.objects.filter(company=company)
            # Pre-populate contract leave fields from company defaults for new workers
            if not self.instance.pk:
                policy = getattr(company, 'leave_policies', None)
                pol = company.leave_policies.first() if hasattr(company, 'leave_policies') else None
                if pol:
                    self.fields['contract_annual_leave'].initial = pol.yearly_leave
                    self.fields['contract_carry_forward'].initial = pol.carry_forward_limit
                    self.fields['contract_sick_leave'].initial = pol.sick_leave_per_year
                    self.fields['contract_emergency_leave'].initial = pol.emergency_leave_per_year
                    self.fields['contract_allow_negative'].initial = pol.allow_negative
                    self.fields['contract_negative_limit'].initial = pol.negative_limit
        elif self.instance and getattr(self.instance, 'client_company_id', None):
            self.fields['assigned_client'].queryset = ClientCompany.objects.filter(company_id=self.instance.client_company_id)

    class Meta:
        model = Employee
        exclude = ['user', 'payment_history', 'salary_paid', 'client_company']
        labels = {
            'name': 'Worker Full Name',
            'nationality': 'Nationality',
            'phone_number': 'Phone Number',
            'photo': 'Worker Photo',
            'iqama_number': 'Iqama Number / Civil ID',
            'passport_number': 'Passport Number',
            'iqama_expiry': 'Iqama Expiry Date',
            'joining_date': 'Joining Date',
            'transfer_dates': 'Sponsorship Transfer Date',
            'kafeel_name': 'Kafeel / Sponsor Name',
            'visa_status': 'Visa / Iqama Status',
            'assigned_client': 'Assigned Client Company',
            'deployment_status': 'Deployment / Bench Status',
            'deployment_date': 'Current Deployment Start Date',
            'unemployed_date': 'Demobilization / Job Loss Date',
            'unemployed_reason': 'Reason Unemployed / Demobilized',
            'company_name': 'Client Company (Contractor)',
            'client_project': 'Client Project Site / Work Location',
            'position': 'Job Designation / Trade',
            'basic_salary': 'Basic Salary (SAR)',
            'receiving_amount': 'Receiving Amount (SAR)',
            'salary_from_account': 'Salary From Account (IBAN / Bank)',
            'salary_payment_company': 'Salary Payment Company (Disbursing Entity)',
            'working_place': 'Working City / Province',
            'country': 'Country',
            'additional_note': 'Contract / HR Notes',
            'contract_annual_leave': 'Contract Annual Leave (Days/Year)',
            'contract_carry_forward': 'Carry Forward Limit (Days)',
            'contract_sick_leave': 'Paid Sick Leave (Days/Year)',
            'contract_emergency_leave': 'Emergency / Casual Leave (Days/Year)',
            'contract_allow_negative': 'Allow Advance / Negative Leave',
            'contract_negative_limit': 'Max Advance Leave (Days)',
            'contract_ticket_frequency': 'Flight Ticket Entitlement',
            'leave_contract_notes': 'Contract Leave Stipulations / Terms',
        }
        help_texts = {
            'basic_salary': 'Monthly base salary disbursed to worker (Cost to company).',
            'receiving_amount': 'Monthly contract billing rate invoiced to client (Revenue).',
            'salary_from_account': 'Company bank account / WPS IBAN from which payment originates.',
            'salary_payment_company': 'Legal entity name appearing on WPS / bank payment advice.',
            'deployment_status': 'Select "Deployed at Client" if actively working, or "Unemployed / On Bench" if waiting for placement.',
            'contract_annual_leave': 'Agreed annual leave days per year in this worker\'s individual contract (e.g. 21 standard, 30 for engineers, 42 for 2-year cycle).',
            'contract_carry_forward': 'Max unused days rolling into next calendar year.',
            'contract_sick_leave': 'Paid sick leave days committed in individual contract per year.',
            'contract_emergency_leave': 'Emergency or casual days allowed per contract year.',
            'contract_allow_negative': 'Permit worker to request advance leave before it is accrued.',
            'contract_negative_limit': 'Max advance days if negative balance is allowed.',
            'contract_ticket_frequency': 'Contractual obligation for home country return flight ticket.',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'nationality': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Bangladeshi, Indian, Pakistani'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+966 5X XXX XXXX'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
            'iqama_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10-digit Iqama / ID'}),
            'passport_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Passport Number'}),
            'iqama_expiry': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'joining_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'transfer_dates': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'kafeel_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Kafeel / Sponsor'}),
            'visa_status': forms.Select(attrs={'class': 'form-select'}),
            'assigned_client': forms.Select(attrs={'class': 'form-select'}),
            'deployment_status': forms.Select(attrs={'class': 'form-select'}),
            'deployment_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'unemployed_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'unemployed_reason': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Project completed, client cut manpower'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Subcontract Client / Project'}),
            'client_project': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Aramco Site A / Neom Station'}),
            'position': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Electrician, Welder, Driver'}),
            'basic_salary': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 1500.00', 'step': '0.01'}),
            'receiving_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 3500.00', 'step': '0.01'}),
            'salary_from_account': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Al Rajhi Bank IBAN SA4480000...'}),
            'salary_payment_company': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Al-Madina Contracting Co.'}),
            'working_place': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Riyadh, Jubail, Dammam'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Saudi Arabia'}),
            'additional_note': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Special agreements, overtime rates, safety certifications...'}),
            'contract_annual_leave': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'min': '0'}),
            'contract_carry_forward': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'min': '0'}),
            'contract_sick_leave': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'min': '0'}),
            'contract_emergency_leave': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'min': '0'}),
            'contract_allow_negative': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'contract_negative_limit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'min': '0'}),
            'contract_ticket_frequency': forms.Select(attrs={'class': 'form-select'}),
            'leave_contract_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Specific contractual leave agreement terms...'}),
        }


class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = [
            'property_name', 'housing_type', 'location', 'capacity',
            'cost_to_company', 'charge_to_client', 'worker_deduction'
        ]
        labels = {
            'property_name': 'Accommodation / Camp Name *',
            'housing_type': 'Housing Provider / Arrangement *',
            'location': 'Camp Location / Site Address',
            'capacity': 'Bed / Resident Capacity (Total Beds)',
            'cost_to_company': 'Camp Rent / Cost Paid by Our Company (SAR/month)',
            'charge_to_client': 'Housing Invoiced to Client Company (SAR/month)',
            'worker_deduction': 'Worker Salary Deduction (SAR/month)',
        }
        help_texts = {
            'housing_type': 'Select Client-Provided Site Camp (SAR 0.00) or Company-Rented Camp.',
            'cost_to_company': 'Rent or compound fee paid by our company. Enter 0.00 if client-provided.',
            'charge_to_client': 'Monthly amount billed to client for accommodation. Enter 0.00 if included in contract rate.',
            'worker_deduction': 'Deduction from worker salary. Enter 0.00 if accommodation is free.',
            'capacity': 'Total number of bed spaces available.',
        }
        widgets = {
            'property_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. NEOM Site Camp Block 3, Jeddah Port Labor Camp'}),
            'housing_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_housing_type'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Tabuk / NEOM, Riyadh Industrial City, Jubail'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'placeholder': 'e.g. 50'}),
            'cost_to_company': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'charge_to_client': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'worker_deduction': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
        }


class ClientCompanyForm(forms.ModelForm):
    class Meta:
        model = ClientCompany
        fields = [
            'name', 'contact_person', 'phone', 'email',
            'project_name', 'project_location', 'cr_number',
            'contract_number', 'contract_start', 'contract_end',
            'status', 'notes'
        ]
        labels = {
            'name': 'Client Company Name *',
            'contact_person': 'Contact Person / Project Manager',
            'phone': 'Contact Phone / Mobile',
            'email': 'Contact Email',
            'project_name': 'Project / Site Name',
            'project_location': 'Project Location / City',
            'cr_number': 'CR / Tax Number (Optional)',
            'contract_number': 'Contract / Agreement Ref #',
            'contract_start': 'Contract Start Date',
            'contract_end': 'Contract End Date',
            'status': 'Contract Status',
            'notes': 'Commercial Terms & Operational Notes',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Saudi Aramco, Red Sea Global, Nesma & Partners'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Eng. Khalid Al-Mutairi'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+966 5X XXX XXXX'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'procurement@client.com'}),
            'project_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Riyadh Metro Extension, NEOM Spine Site'}),
            'project_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Riyadh, NEOM, Ras Tanura, Jeddah'}),
            'cr_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10-digit CR'}),
            'contract_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. CON-2026-089'}),
            'contract_start': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'contract_end': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Billing payment terms (Net 30/60), safety equipment requirements, supply rates...'}),
        }


class EmployeeAssignClientForm(forms.Form):
    client_id = forms.ModelChoiceField(
        queryset=ClientCompany.objects.none(),
        label="Select Client Company *",
        widget=forms.Select(attrs={'class': 'form-select', 'required': 'required'})
    )
    deployment_date = forms.DateField(
        label="Deployment Start Date *",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'required': 'required'})
    )
    project_site = forms.CharField(
        required=False,
        label="Specific Work / Project Site (Optional)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Site Camp Gate 2, Substation 4'})
    )
    notes = forms.CharField(
        required=False,
        label="Deployment Notes",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Transferred from bench pool to active project'})
    )

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            self.fields['client_id'].queryset = ClientCompany.objects.filter(company=company)


class EmployeeDemobilizeForm(forms.Form):
    reason = forms.CharField(
        label="Demobilization / Job Loss Reason *",
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'e.g. Client finished project contract, client reduced workforce, site closed',
            'required': 'required'
        })
    )
    unemployed_date = forms.DateField(
        label="Demobilization Date *",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'required': 'required'})
    )
    notes = forms.CharField(
        required=False,
        label="Demobilization Remarks",
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 2, 
            'placeholder': 'Worker returned to accommodation, available for redeployment to other clients'
        })
    )


class EmployeeExpenseForm(forms.ModelForm):
    class Meta:
        model = EmployeeExpense
        fields = ['expense_type', 'amount', 'expense_date', 'notes', 'deduct_from_salary']
        labels = {
            'expense_type': 'Expense / Spending Category',
            'amount': 'Amount (SAR)',
            'expense_date': 'Expense Date',
            'notes': 'Description / Reference Notes',
            'deduct_from_salary': 'Deduct from monthly salary payroll',
        }
        help_texts = {
            'amount': 'Cost in SAR. Enter 0.00 if covered by client company or free.',
            'deduct_from_salary': 'Check this box if this spending (e.g. salary advance) should reduce the worker payout.',
        }
        widgets = {
            'expense_type': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'expense_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Advance cash, bus ticket, medical clinic...'}),
            'deduct_from_salary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class IqamaRenewalForm(forms.Form):
    new_expiry = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="New Iqama Expiry Date",
        required=True
    )
    renewal_cost = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        initial=0.00,
        min_value=0,
        required=True,
        label="Renewal Cost / Government Fee (SAR)",
        help_text="Manual amount paid for renewal. Enter 0 if covered by client company.",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': '0.00'})
    )
    notes = forms.CharField(
        required=False,
        label="Payment Notes / Invoice Ref",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Jawazat + Maktab Amal 1-Year renewal fee'})
    )

class HolidayForm(forms.ModelForm):
    class Meta:
        model = Holiday
        fields = ['holiday_date', 'name']
        widgets = {
            'holiday_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }

class LeavePolicyForm(forms.ModelForm):
    class Meta:
        model = LeavePolicy
        fields = ['yearly_leave', 'carry_forward_limit', 'sick_leave_per_year', 'emergency_leave_per_year', 'allow_negative', 'negative_limit']
        widgets = {
            'yearly_leave': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'carry_forward_limit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'sick_leave_per_year': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'emergency_leave_per_year': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'allow_negative': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'negative_limit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
        }

class EmployeeLeaveContractForm(forms.ModelForm):
    sync_leave_balance = forms.BooleanField(
        required=False,
        initial=True,
        label="Sync Current Year Accrued Balance (تحديث الرصيد المستحق الحالي)",
        help_text="Automatically update worker's active calendar year leave quota to match this new contractual entitlement."
    )

    class Meta:
        model = Employee
        fields = [
            'contract_annual_leave',
            'contract_carry_forward',
            'contract_sick_leave',
            'contract_emergency_leave',
            'contract_allow_negative',
            'contract_negative_limit',
            'contract_ticket_frequency',
            'leave_contract_notes',
        ]
        labels = {
            'contract_annual_leave': 'Contract Annual Leave (Days/Year) *',
            'contract_carry_forward': 'Carry Forward Limit (Days)',
            'contract_sick_leave': 'Paid Sick Leave Allowed / Year (Days)',
            'contract_emergency_leave': 'Emergency Leave Allowed / Year (Days)',
            'contract_allow_negative': 'Allow Advance Leave (Negative Balance)',
            'contract_negative_limit': 'Max Negative / Advance Limit (Days)',
            'contract_ticket_frequency': 'Flight Ticket Entitlement',
            'leave_contract_notes': 'Contractual Leave Stipulations / Notes',
        }
        help_texts = {
            'contract_annual_leave': 'Committed annual leave days per year in this worker\'s contract (e.g. 21 standard, 30 for engineers/supervisors, 42 for 2-year cycle).',
            'contract_carry_forward': 'Max unused days rolling into next calendar year.',
            'contract_sick_leave': 'Paid sick leave quota committed in worker\'s contract.',
            'contract_emergency_leave': 'Emergency or casual days allowed per contract year.',
            'contract_allow_negative': 'Permit worker to take leave before it is accrued.',
            'contract_negative_limit': 'Max advance days if negative balance is allowed.',
            'contract_ticket_frequency': 'Contractual obligation for home country return flight ticket.',
            'leave_contract_notes': 'Specific agreement clauses, destination city, or exit re-entry terms.',
        }
        widgets = {
            'contract_annual_leave': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'min': '0'}),
            'contract_carry_forward': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'min': '0'}),
            'contract_sick_leave': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'min': '0'}),
            'contract_emergency_leave': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'min': '0'}),
            'contract_allow_negative': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'contract_negative_limit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'min': '0'}),
            'contract_ticket_frequency': forms.Select(attrs={'class': 'form-select'}),
            'leave_contract_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'e.g. Annual round-trip ticket to Dhaka/Manila, 30 days full pay sick leave per Article 117...'}),
        }


class SalaryDisbursementForm(forms.ModelForm):
    settle_advances = forms.BooleanField(
        required=False,
        initial=True,
        label="Deduct & Settle Collected Advances (خصم وتسوية السلف المعلقة)",
        help_text="Automatically mark pending advance salary records as settled upon disbursing this salary."
    )

    class Meta:
        model = SalaryDisbursement
        fields = [
            'month', 'year', 'disbursement_date',
            'amount_paid', 'payment_method',
            'disbursing_account', 'reference_number',
            'receipt_doc', 'notes'
        ]
        labels = {
            'month': 'Salary Month *',
            'year': 'Salary Year *',
            'disbursement_date': 'Payment Date *',
            'amount_paid': 'Disbursed Amount (SAR) *',
            'payment_method': 'Payment Channel / Method *',
            'disbursing_account': 'Disbursing Bank / Account',
            'reference_number': 'Transaction Ref / Voucher #',
            'receipt_doc': 'Attach Receipt / Transfer Voucher (Optional)',
            'notes': 'Payment Notes & Remarks',
        }
        help_texts = {
            'amount_paid': 'Actual net amount disbursed to the worker after deducting collected advances.',
            'disbursing_account': 'Originating bank account or IBAN.',
            'receipt_doc': 'Upload signed voucher, bank transfer advice, or cash voucher slip (PDF, JPG, PNG).',
        }
        widgets = {
            'month': forms.Select(
                choices=[(i, date(2026, i, 1).strftime('%B')) for i in range(1, 13)], 
                attrs={'class': 'form-select'}
            ),
            'year': forms.NumberInput(attrs={'class': 'form-control'}),
            'disbursement_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'amount_paid': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'disbursing_account': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Al Rajhi Bank IBAN SA4480000...'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. WPS-REF-889021 or Cash Slip #45'}),
            'receipt_doc': forms.FileInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Payment notes, overtime allowances, or special remarks...'}),
        }


# ================== JOB POSTING & SOCIAL RECRUITMENT FORMS ==================

class JobPostForm(forms.ModelForm):
    class Meta:
        model = JobPost
        fields = [
            'title', 'trade_category', 'workers_needed', 'work_location', 'project_name',
            'salary_min', 'salary_max', 'accommodation_provided', 'food_provided', 
            'transportation_provided', 'iqama_transfer_required', 'experience_years', 'description'
        ]
        labels = {
            'title': 'Job Title / Requirement *',
            'trade_category': 'Trade / Skill Category *',
            'workers_needed': 'Workers Needed (Headcount) *',
            'work_location': 'Project City / Location (e.g. Riyadh, Neom, Jubail) *',
            'project_name': 'Project Site / Subcontract (Optional)',
            'salary_min': 'Min Basic Salary (SAR) *',
            'salary_max': 'Max Basic Salary (SAR)',
            'accommodation_provided': 'Accommodation Provided Free by Company',
            'food_provided': 'Food or Food Allowance Provided',
            'transportation_provided': 'Transportation to Project Site Provided',
            'iqama_transfer_required': 'Requires Transferable Iqama (نقل كفالة) or Ajeer Supply',
            'experience_years': 'Min Years Experience Required',
            'description': 'Job Requirements, Trade Certifications & Scope of Work *',
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Certified 6G Pipe Welders or Heavy Equipment Drivers'}),
            'trade_category': forms.Select(attrs={'class': 'form-select'}),
            'workers_needed': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'work_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Riyadh, Neom Base Camp, Jubail Industrial City'}),
            'project_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Aramco Subcontract Site 4B'}),
            'salary_min': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': 'e.g. 2500.00'}),
            'salary_max': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': 'e.g. 3500.00'}),
            'accommodation_provided': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'food_provided': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'transportation_provided': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'iqama_transfer_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'experience_years': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'List technical qualifications, required certifications (e.g. Aramco/TUV card, heavy license), shift hours...'}),
        }


class JobSeekerRegisterForm(forms.Form):
    """
    Worker registration form guarded strictly by one-time referral link.
    Requires unique Iqama and unique Phone.
    """
    referral_token = forms.CharField(widget=forms.HiddenInput(), required=False)
    
    # Login credentials
    username = forms.CharField(
        max_length=150, 
        required=True, 
        label="Username (اسم المستخدم)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter strong password'}),
        label="Password (كلمة المرور)",
        required=True
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Re-enter password'}),
        label="Confirm Password (تأكيد كلمة المرور)",
        required=True
    )

    # Worker Identity & Skills
    full_name = forms.CharField(
        max_length=150, 
        label="Full Name (الاسم الكامل)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full legal name as per Iqama'})
    )
    iqama_number = forms.CharField(
        max_length=20, 
        label="Iqama / National ID Number (رقم الإقامة)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10-digit Iqama / ID number'}),
        help_text="Must be unique. Tamper-proof verification."
    )
    phone_number = forms.CharField(
        max_length=30, 
        label="Mobile / WhatsApp Number (رقم الجوال / واتساب)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 05X XXX XXXX or +9665XXXXXXXX'}),
        help_text="Must be unique. Used for two-matched entry onboarding."
    )
    nationality = forms.CharField(
        max_length=50,
        label="Nationality (الجنسية)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Pakistani, Indian, Egyptian, Filipino'})
    )
    trade = forms.CharField(
        max_length=100, 
        label="Primary Trade / Craft / Position (المهنة الأساسية)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 6G Welder, Electrician, Heavy Driver, Mason'})
    )
    experience_years = forms.IntegerField(
        min_value=0, 
        initial=2, 
        label="Years of Experience (سنوات الخبرة)",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    current_city = forms.CharField(
        max_length=100, 
        label="Current City in Saudi Arabia (المدينة الحالية)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Riyadh, Jeddah, Dammam, Jubail'})
    )
    iqama_transferable = forms.BooleanField(
        required=False, 
        initial=True, 
        label="Iqama is Transferable (الإقامة قابلة لنقل الكفالة)",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    expected_salary = forms.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        initial=2500.00,
        label="Expected Monthly Salary SAR (الراتب المتوقع)",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    bio_skills = forms.CharField(
        required=False,
        label="Skills, Certifications & Licenses (المهارات والشهادات)",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'e.g. Heavy driver license #..., Aramco certified badge, OSHA card...'})
    )
    cv_document = forms.FileField(
        required=False,
        label="Upload CV / Resume / Iqama Copy (Optional)",
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken. Please choose another.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        pw = cleaned_data.get('password')
        cpw = cleaned_data.get('confirm_password')
        if pw and cpw and pw != cpw:
            self.add_error('confirm_password', "Passwords do not match.")

        # Check unique Iqama
        iqama = cleaned_data.get('iqama_number')
        if iqama:
            iqama = iqama.strip()
            if JobSeekerProfile.objects.filter(iqama_number=iqama).exists():
                self.add_error('iqama_number', "A registered worker with this Iqama number already exists.")
            if Employee.objects.filter(iqama_number=iqama).exists():
                self.add_error('iqama_number', "An active company employee with this Iqama number already exists in the system.")

        # Check unique Phone
        phone = cleaned_data.get('phone_number')
        if phone:
            phone = phone.strip()
            if JobSeekerProfile.objects.filter(phone_number=phone).exists():
                self.add_error('phone_number', "A registered worker with this phone number already exists.")

        return cleaned_data


class ReferralLinkGenerateForm(forms.Form):
    label_note = forms.CharField(
        max_length=255, 
        required=False, 
        label="Recipient / Candidate Note (ملاحظة المستفيد)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Invite for Senior Electrician Mohammad / Riyadh'})
    )
    valid_days = forms.IntegerField(
        min_value=1, 
        max_value=90, 
        initial=14, 
        label="Link Validity (Days)",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )


class TwoMatchedOnboardForm(forms.Form):
    """
    Allows a contracting company to onboard a worker from the job network
    by matching BOTH Iqama Number and Phone Number.
    """
    iqama_number = forms.CharField(
        max_length=20, 
        required=True,
        label="1. Worker Iqama Number (رقم الإقامة) *",
        widget=forms.TextInput(attrs={'class': 'form-control fw-bold', 'placeholder': 'Enter 10-digit Iqama number'})
    )
    phone_number = forms.CharField(
        max_length=30, 
        required=True,
        label="2. Worker Mobile Number (رقم الجوال) *",
        widget=forms.TextInput(attrs={'class': 'form-control fw-bold', 'placeholder': 'Enter candidate mobile number'})
    )
    basic_salary = forms.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=True,
        label="Agreed Contract Basic Salary (SAR) *",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 2500.00', 'step': '0.01'})
    )
    receiving_amount = forms.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=False,
        initial=3500.00,
        label="Client Billing / Receiving Rate (SAR)",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 4000.00', 'step': '0.01'})
    )
    position = forms.CharField(
        max_length=100, 
        required=False,
        label="Position / Designation (Leave blank to use candidate trade)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 6G Welder'})
    )
    assigned_client = forms.ModelChoiceField(
        queryset=ClientCompany.objects.none(),
        required=False,
        label="Assign Directly to Client / Project (Optional)",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    joining_date = forms.DateField(
        initial=date.today,
        label="Joining Date *",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            self.fields['assigned_client'].queryset = ClientCompany.objects.filter(company=company)



