from django.contrib import admin

from WhatsPanel.models import *

admin.site.register(WhatsAppTemplate)
admin.site.register(WhatsAppUser)  
admin.site.register(WhatsAppMedia)  
admin.site.register(WhatsAppMessage)   
admin.site.register(WhatsAppReaction)  
admin.site.register(WhatsAppAdminUser)  
admin.site.register(EmailVerificationToken)
admin.site.register(PasswordResetToken)

