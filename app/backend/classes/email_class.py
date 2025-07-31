import smtplib
from typing import List, Optional
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

class EmailClass:
    def __init__(self, sender_email: str, sender_name: str, sender_password: str):
        self.sender_email = sender_email
        self.sender_name = sender_name
        self.sender_password = sender_password
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 465

    def send_email(
        self,
        receiver_email: str,
        cc: Optional[List[str]] = None,
        subject: str = "",
        message: str = "",
        pdf_bytes: Optional[bytes] = None,
        pdf_filename: str = "reporte.pdf"
    ) -> str:
        try:
            msg = MIMEMultipart()
            msg["From"] = self.sender_email
            msg["To"] = receiver_email
            msg["Subject"] = subject

            # Validar y agregar destinatarios en copia (cc)
            valid_cc = [email for email in (cc or []) if email]
            if valid_cc:
                msg["Cc"] = ", ".join(valid_cc)

            # Agregar contenido HTML
            msg.attach(MIMEText(message, "html"))

            # Adjuntar PDF si se entrega
            if pdf_bytes:
                part = MIMEApplication(pdf_bytes, _subtype="pdf")
                part.add_header('Content-Disposition', f'attachment; filename="{pdf_filename}"')
                msg.attach(part)

            # Combinar destinatario principal y copias
            all_recipients = [receiver_email] + valid_cc

            # Enviar correo
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, all_recipients, msg.as_string())

            return "Correo enviado correctamente"

        except smtplib.SMTPAuthenticationError:
            return "Error de autenticación: Verifica tu email y contraseña (usa una contraseña de aplicación si es Gmail)"
        except smtplib.SMTPException as e:
            return f"Error al enviar el correo: {str(e)}"
        except Exception as e:
            return f"Error inesperado al enviar el correo: {str(e)}"
