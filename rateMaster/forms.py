from datetime import date, datetime
from django import forms

class MonthYearSelectionForm(forms.Form):
    # Month dropdown
    MONTH_CHOICES = [
        (1, 'January'), (2, 'February'), (3, 'March'),
        (4, 'April'), (5, 'May'), (6, 'June'),
        (7, 'July'), (8, 'August'), (9, 'September'),
        (10, 'October'), (11, 'November'), (12, 'December'),
    ]
    month = forms.ChoiceField(choices=MONTH_CHOICES, label="Select Month", widget=forms.Select(attrs={'class': 'form-control'}))
    
    # Year dropdown (current year to next 5 years for example)
    current_year = date.today().year  # Use date.today() correctly
    YEAR_CHOICES = [(year, str(year)) for year in range(current_year - 5, current_year + 6)]
    year = forms.ChoiceField(choices=YEAR_CHOICES, label="Select Year", widget=forms.Select(attrs={'class': 'form-control'}))