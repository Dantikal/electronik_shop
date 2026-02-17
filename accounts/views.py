from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('shop:home')


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('shop:home')
    
    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)
