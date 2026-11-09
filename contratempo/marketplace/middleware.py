from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect


class BloquearContaSuspensa:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.status_conta == "suspenso":
            logout(request)
            messages.error(request, "Esta conta está suspensa. Fale com o suporte pela página de contato.")
            return redirect("login")
        return self.get_response(request)
