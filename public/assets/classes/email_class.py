import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

class EmailClass:
    def __init__(self, sender_email: str, sender_password: str, smtp_server: str = "smtp.gmail.com", smtp_port: int = 465):
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port

    def send_email(self, receiver_email: str, subject: str, message: str, pdf_bytes: bytes = None, pdf_filename: str = "reporte.pdf"):
        try:
            msg = MIMEMultipart()
            msg["From"] = self.sender_email
            msg["To"] = receiver_email
            msg["Subject"] = subject
            msg.attach(MIMEText(message, "html"))

            if pdf_bytes:
                part = MIMEApplication(pdf_bytes, _subtype="pdf")
                part.add_header('Content-Disposition', f'attachment; filename="{pdf_filename}"')
                msg.attach(part)

            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, receiver_email, msg.as_string())

            return "Correo enviado correctamente"

        except smtplib.SMTPAuthenticationError:
            return "Error de autenticación: Verifica tu email y contraseña (usa una contraseña de aplicación si es Gmail)"
        except smtplib.SMTPException as e:
            return f"Error al enviar el correo: {str(e)}"
        except Exception as e:
            return f"Error inesperado al enviar el correo: {str(e)}"