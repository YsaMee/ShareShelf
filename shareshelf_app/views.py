from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .forms import LoginForm, SignUpForm
from .models import UserProfile

# Global Context Processor for user profile
def profile_context(request):
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        return {'profile': request.user.profile}
    return {'profile': None}


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].lower().strip()
            password = form.cleaned_data['password']
            user = authenticate(request, username=email, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, "Logged in successfully!")
                return redirect('dashboard')
            else:
                form.add_error(None, "Invalid email or password.")
                messages.error(request, "Invalid email or password.")
    else:
        form = LoginForm()

    return render(request, 'shelf/login.html', {
        'mode': 'login',
        'form': form,
    })


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            name = form.cleaned_data['name']
            program = form.cleaned_data['program']

            user = User.objects.create_user(username=email, email=email, password=password)
            UserProfile.objects.create(user=user, full_name=name, program=program)

            login(request, user)
            messages.success(request, f"Welcome to ShareShelf, {name}!")
            return redirect('dashboard')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = SignUpForm()

    return render(request, 'shelf/login.html', {
        'mode': 'signup',
        'form': form,
    })


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, "Logged out successfully.")
    return redirect('login')


def dashboard_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'shelf/dashboard.html', {'greeting': 'Good day'})