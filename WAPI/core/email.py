from django.core.mail import send_mail
from django.conf import settings
from urllib.parse import quote
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def _full_name(user):
    return f"{user.first_name} {user.last_name}".strip() or user.username

def send_verification_email(user, token):
    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
    token_str = str(token)  
    from_email = settings.DEFAULT_FROM_EMAIL
    verification_url = f"{frontend_url}/api/v1/verify-email/?token={token_str}"
    
    text_body = f"Hi {_full_name(user)},\n\nVerify your email: {verification_url}\n\nThis link expires in 48 hours."

    html_body = f"""<p>Hi {_full_name(user)},</p>
<p>Please verify your email by clicking below:</p>
<p><a href="{verification_url}" style="padding:10px 15px;background:#4CAF50;color:white;text-decoration:none;">Verify Email</a></p>
<p>This link expires in 48 hours.</p>"""

    email = EmailMultiAlternatives(
        subject='Verify your email address',
        body=text_body,
        from_email=from_email,
        to=[user.email],
    )
    email.attach_alternative(html_body, "text/html")
    
    # Let Django handle the encoding. Just send the email.
    email.send()

def send_password_reset_email(user, token):
    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
    reset_url = f"{frontend_url}/auth/reset-password?token={token}"
    subject = 'Reset your password'
    from_email = settings.DEFAULT_FROM_EMAIL
    to = user.email

    text_content = (
        f"Hi {_full_name(user)},\n\n"
        f"You requested a password reset. Please copy and paste the link below into your browser:\n\n"
        f"{reset_url}\n\n"
        f"This link expires in 24 hours."
    )

    html_content = f"""
    <p>Hi {_full_name(user)},</p>
    <p>You requested a password reset. Click the button below to proceed:</p>
    <p>
        <a href="{reset_url}" 
           style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
           Reset Password
        </a>
    </p>
    <p>If the button doesn't work, copy and paste this link:</p>
    <p>{reset_url}</p>
    """
    
    msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
    msg.attach_alternative(html_content, "text/html")
    
    msg.send(fail_silently=False)

def send_password_changed_email(user):
    send_mail(
        subject='Your password has been changed',
        message=(
            f"Hi {_full_name(user)},\n\n"
            f"Your password was successfully changed.\n\n"
            f"If you did not make this change, contact support immediately."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )


