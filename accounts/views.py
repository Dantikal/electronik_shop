from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db.models import Q
from django.contrib.auth.models import User

from .forms import CustomUserCreationForm, UserUpdateForm, UserProfileUpdateForm
from .models import UserProfile


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('shop:home')


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('shop:home')
    
    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)


class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('accounts:login')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Регистрация прошла успешно! Теперь вы можете войти.')
        return response


@login_required
def profile_view(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    return render(request, 'accounts/profile.html', {'profile': profile})


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = 'accounts/profile_edit.html'
    success_url = reverse_lazy('accounts:profile')
    
    def get_object(self):
        return self.request.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        context['profile_form'] = UserProfileUpdateForm(instance=profile)
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        profile_form = context['profile_form']
        
        if profile_form.is_valid():
            profile_form.save()
            messages.success(self.request, 'Профиль успешно обновлен!')
            return super().form_valid(form)
        else:
            return self.form_invalid(form)


def profile_orders(request):
    print(f"Request method: {request.method}")
    print(f"User authenticated: {request.user.is_authenticated}")
    
    if request.user.is_authenticated:
        from shop.models import Order
        orders = Order.objects.filter(user=request.user).order_by('-created_at')
        return render(request, 'accounts/profile_orders.html', {'orders': orders})
    else:
        from django.contrib.auth.views import redirect_to_login
        from django.contrib.messages import messages
        messages.info(request, 'Пожалуйста, войдите в аккаунт для просмотра заказов')
        return redirect_to_login(request.get_full_path())
