from django.contrib import admin
from osis_common.models import message_template, message_history, document_file

admin.site.register(message_template.MessageTemplate,
                    message_template.MessageTemplateAdmin)
admin.site.register(message_history.MessageHistory,
                    message_history.MessageHistoryAdmin)
admin.site.register(document_file.DocumentFile,
                    document_file.DocumentFileAdmin)
