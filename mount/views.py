import django
from django.shortcuts import render, redirect
from .models import detail

# Create your views here.
def home (request):
    if request.method == "POST":
        detail.objects.create(
            name=request.POST['name'],
            email=request.POST['email'],
            level=request.POST['level'] ,
            decription=request.POST['description']
        )
        return redirect('home')
    return render(request, 'home.html')


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
            return redirect('signup')

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

@login_required
def home(request):
    return render(request, 'home.html')
