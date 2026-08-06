from django import forms
from .models import Employee

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = '__all__'
        widgets = {
            'iqama_expiry': forms.DateInput(attrs={'type': 'date'}),
            'starting_date': forms.DateInput(attrs={'type': 'date'}),
        }
