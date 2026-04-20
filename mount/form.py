from django import forms
from .models import detail

class DetailForm(forms.ModelForm):
    class Meta:
        model = detail
        fields = ['name', 'email', 'level',  'pics', 'active']