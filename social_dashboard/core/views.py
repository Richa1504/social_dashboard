from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from .forms import CustomUserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm, AuthenticationForm
from django.contrib.auth import update_session_auth_hash, authenticate
from django import forms
from .models import CustomUser
from core.models import SocialToken
import requests
from django.conf import settings


@login_required
def dashboard_view(request):
    return render(request, 'core/dashboard.html')


def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'core/register.html', {'form': form})

def login_view(request):
    form = AuthenticationForm(request, data=request.POST or None)  # Use Django's built-in AuthenticationForm
    if request.method == "POST":
        if form.is_valid():  # Validate the form
            user = form.get_user()  # Get the authenticated user
            login(request, user)  # Log the user in
            return redirect("dashboard")  # Redirect to the dashboard or home page
        else:
            return render(request, "core/login.html", {"form": form, "error": "Invalid credentials"})
    return render(request, "core/login.html", {"form": form})  # Pass the form to the template for GET requests

def logout_view(request):
    logout(request)
    return redirect('login_view')




# Profile Form
class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'profile_picture']

@login_required
def profile_settings_view(request):
    if request.method == 'POST':
        profile_form = ProfileUpdateForm(request.POST, instance=request.user)
        password_form = PasswordChangeForm(request.user, request.POST)

        if 'update_profile' in request.POST and profile_form.is_valid():
            profile_form.save()
            messages.success(request, 'Profile updated successfully.')

        elif 'change_password' in request.POST and password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully.')

    else:
        profile_form = ProfileUpdateForm(instance=request.user)
        password_form = PasswordChangeForm(request.user)

    return render(request, 'core/settings.html', {
        'profile_form': profile_form,
        'password_form': password_form
    })


@login_required
def facebook_login(request):
    fb_login_url = (
        f"https://www.facebook.com/v19.0/dialog/oauth"
        f"?client_id={settings.FACEBOOK_APP_ID}"
        f"&redirect_uri={settings.REDIRECT_URI}"
        f"&scope=public_profile,email,pages_show_list,instagram_basic,pages_read_engagement"
        f"&response_type=code"
    )
    return redirect(fb_login_url)


@login_required
def facebook_callback(request):
    code = request.GET.get('code')
    if not code:
        return render(request, 'core/error.html', {"message": "No code returned"})

    # Exchange code for access token
    token_url = "https://graph.facebook.com/v19.0/oauth/access_token"
    params = {
        "client_id": settings.FACEBOOK_APP_ID,
        "redirect_uri": settings.REDIRECT_URI,
        "client_secret": settings.FACEBOOK_APP_SECRET,
        "code": code
    }
    token_res = requests.get(token_url, params=params).json()
    access_token = token_res.get("access_token")

    # Optional: Save token to the database per user
    request.user.socialtoken_set.update_or_create(
        provider="facebook",
        defaults={"access_token": access_token}
    )

    return redirect('dashboard')


@login_required
def facebook_feed_view(request):
    try:
        social_token = request.user.socialtoken_set.get(provider='facebook')
        facebook_feed = []
        return render(request, 'core/facebook_feed.html', {'feed': facebook_feed}) 
    except SocialToken.DoesNotExist:
        return render(request, 'core/error.html', {"message": "Facebook not connected."})
    
    access_token = social_token.access_token

    # Step 1: Get pages connected to the user
    pages_url = f"https://graph.facebook.com/v19.0/me/accounts"
    pages_res = requests.get(pages_url, params={"access_token": access_token}).json()

    if "error" in pages_res:
        return render(request, 'core/error.html', {"message": pages_res["error"]["message"]})

    pages = pages_res.get("data", [])

    # Step 2: Get posts from the first page (for now)
    posts = []
    if pages:
        page = pages[0]
        page_id = page["id"]
        page_token = page["access_token"]
        feed_url = f"https://graph.facebook.com/v19.0/{page_id}/posts"
        fields = "message,created_time,permalink_url,full_picture,likes.summary(true),comments.summary(true)"
        feed_res = requests.get(feed_url, params={
            "access_token": page_token,
            "fields": fields
            }).json()

        

    return render(request, 'core/facebook_feed.html', {
        "pages": pages,
        "posts": posts
    })
