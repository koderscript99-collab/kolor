import django
from django.shortcuts import render, redirect
from .models import detail

# Create your views here.
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .form import DetailForm
from django.contrib.auth.decorators import login_required

@login_required
def home(request):
    if request.method == "POST":
        form = DetailForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            print("✅ SAVED")  # DEBUG
            return redirect('success')
        else:
            print(form.errors)  # DEBUG
    else:
        form = DetailForm()

    return render(request, 'home.html', {'form': form})


def success(request):
    return render(request, 'success.html')


from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib import messages

def signup(request):
    if request.method == "POST": 
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('login')

        User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        messages.success(request, "Account created successfully")
        return redirect('login')

    return render(request, 'signup.html')

from django.contrib.auth import authenticate, login

def login_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Invalid credentials")
            return redirect('login')

    return render(request, 'login.html')

from django.contrib.auth import logout

def logout_view(request):
    logout(request)
    return redirect('login')

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .form import DetailForm
from django.contrib.auth.decorators import login_required

@login_required
def home(request):
    if request.method == "POST":
        form = DetailForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('success')
    else:
        form = DetailForm()

    return render(request, 'home.html', {'form': form})