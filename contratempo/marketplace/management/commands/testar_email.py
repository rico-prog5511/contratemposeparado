from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand

from marketplace.emails import explicar_erro_email


class Command(BaseCommand):
    help = "Envia um e-mail de teste e mostra o diagnóstico da configuração."

    def add_arguments(self, parser):
        parser.add_argument("destino", help="E-mail que vai receber o teste")

    def handle(self, *args, **opcoes):
        backend = settings.EMAIL_BACKEND.rsplit(".", 2)[-2]
        senha = settings.EMAIL_HOST_PASSWORD
        self.stdout.write(f"Backend ........ {backend}")
        if backend == "email_brevo":
            self.stdout.write(f"Remetente ...... {settings.DEFAULT_FROM_EMAIL}  (precisa estar confirmado no Brevo)")
            self.stdout.write(f"Chave Brevo .... {len(settings.BREVO_API_KEY)} caracteres")
        else:
            self.stdout.write(f"Conta Gmail .... {settings.EMAIL_HOST_USER or '(não definida)'}")
            self.stdout.write(f"Senha de app ... {'(não definida)' if not senha else f'{len(senha)} caracteres'}")

        usuario = settings.EMAIL_HOST_USER
        if usuario and (usuario.count("@") != 1 or "=" in usuario or " " in usuario):
            self.stdout.write(self.style.ERROR(
                f"\nEMAIL_HOST_USER não parece um e-mail: {usuario!r}. No .env a linha deve ser exatamente "
                "EMAIL_HOST_USER=seuemail@gmail.com (sem repetir o nome da variável, sem espaços nem aspas)."
            ))

        if backend == "email_brevo":
            if not settings.EMAIL_HOST_USER:
                self.stdout.write(self.style.WARNING(
                    "\nEMAIL_HOST_USER está vazio: o Brevo precisa de um remetente confirmado. "
                    "Coloque no .env o e-mail que você confirmou no Brevo."
                ))
        elif backend == "console":
            self.stdout.write(self.style.WARNING(
                "\nEMAIL_HOST_USER e/ou EMAIL_HOST_PASSWORD não estão definidas NESTE terminal, então os "
                "e-mails só são impressos aqui, não enviados. Defina as duas no mesmo terminal em que "
                "roda o runserver:\n"
                '  $env:EMAIL_HOST_USER = "suaconta@gmail.com"\n'
                '  $env:EMAIL_HOST_PASSWORD = "abcdefghijklmnop"\n'
            ))
        elif len(senha) != 16:
            self.stdout.write(self.style.WARNING(
                f"\nA senha tem {len(senha)} caracteres; senhas de app do Google têm 16. "
                "Confira se não usou a senha normal da conta."
            ))

        try:
            send_mail(
                "Teste de e-mail | contratempo",
                "Se você recebeu esta mensagem, o envio de e-mails do contratempo está funcionando.",
                None,
                [opcoes["destino"]],
            )
        except Exception as erro:
            self.stdout.write(self.style.ERROR(f"\nFALHOU: {type(erro).__name__}: {erro}"))
            self.stdout.write(explicar_erro_email(erro))
            return

        if backend == "console":
            self.stdout.write(self.style.WARNING("\nMensagem impressa acima (nada foi enviado)."))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"\nEnviado para {opcoes['destino']}. Confira a caixa de entrada e o spam."
            ))
