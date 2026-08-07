from django import forms
from .models import Employee

class EmployeeForm(forms.ModelForm):
    iqama_expiry = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
        label='Iqama Expiry Date',
        required=True
    )
    starting_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
        label='Starting Date',
        required=True
    )
    transfer_dates = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
        label='Join Date',
        required=False
    )

    class Meta:
        model = Employee
        exclude = ['payment_history']
        error_messages = {
            'iqama_number': {
                'unique': "DUPLICATE ENTRY: An employee with this Iqama Number already exists in your database!",
            },
            'passport_number': {
                'unique': "DUPLICATE ENTRY: An employee with this Passport Number already exists in your database!",
            }
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['iqama_expiry', 'starting_date', 'transfer_dates']:
            if field_name in self.fields:
                self.fields[field_name].widget.format = '%Y-%m-%d'
