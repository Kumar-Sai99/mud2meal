from django import forms
from django.contrib.auth.models import User
from .models import Crop, FarmerProfile, BuyerProfile


class RegisterForm(forms.Form):
    username   = forms.CharField(max_length=150)
    email      = forms.EmailField()
    first_name = forms.CharField(max_length=50)
    last_name  = forms.CharField(max_length=50)
    password1  = forms.CharField(widget=forms.PasswordInput)
    password2  = forms.CharField(widget=forms.PasswordInput)
    phone      = forms.CharField(max_length=15)
    district   = forms.CharField(max_length=100)
    state      = forms.CharField(max_length=100)
    role       = forms.ChoiceField(choices=[('farmer','Farmer'),('buyer','Buyer')])

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Passwords do not match!')
        return cleaned_data

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Username already taken!')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Email already registered!')
        return email


class LoginForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)


class CropForm(forms.ModelForm):
    class Meta:
        model  = Crop
        fields = [
            'name', 'category', 'price', 'unit',
            'quantity', 'description', 'district',
            'state', 'status', 'is_featured', 'photo'
        ]

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if not price:
            raise forms.ValidationError('Price is required!')
        return price

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            raise forms.ValidationError('Crop name is required!')
        return name


class FarmerProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=50)
    last_name  = forms.CharField(max_length=50)
    email      = forms.EmailField()

    class Meta:
        model  = FarmerProfile
        fields = ['phone', 'district', 'state', 'farm_id', 'specialty', 'bio', 'photo', 'upi_id']


class BuyerProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=50)
    last_name  = forms.CharField(max_length=50)
    email      = forms.EmailField()

    class Meta:
        model  = BuyerProfile
        fields = ['phone', 'district', 'state', 'delivery_address']