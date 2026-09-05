from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('employees', '0006_rename_starting_date_employee_joining_date_and_more'),
    ]
    operations = [
        migrations.RemoveField(
            model_name='property',
            name='employee_salary',
        ),
    ]
