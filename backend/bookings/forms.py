from django import forms
from .models import Booking
import datetime


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = [
            'customer_name', 'customer_email', 'customer_phone',
            'event_date', 'event_end_date', 'event_time',
            'guest_count', 'special_requests',
        ]
        widgets = {
            'customer_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'customer_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}),
            'customer_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'event_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'min': str(datetime.date.today())}),
            'event_end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'event_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'guest_count': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'special_requests': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Any special requirements...'}),
        }
        labels = {
            'event_end_date': 'End Date (optional, for multi-day)',
            'event_time': 'Preferred Time (optional)',
        }

    def clean_event_date(self):
        date = self.cleaned_data['event_date']
        if date < datetime.date.today():
            raise forms.ValidationError('Event date cannot be in the past.')
        return date

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('event_date')
        end = cleaned.get('event_end_date')
        if start and end and end < start:
            self.add_error('event_end_date', 'End date must be after start date.')
        return cleaned
