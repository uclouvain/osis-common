from django.contrib import admin

from osis_common.models import message_template, message_history, document_file, queue_exception, application_notice, \
    message_queue_cache

admin.site.register(message_template.MessageTemplate,
                    message_template.MessageTemplateAdmin)
admin.site.register(message_history.MessageHistory,
                    message_history.MessageHistoryAdmin)
admin.site.register(message_queue_cache.MessageQueueCache,
                    message_queue_cache.MessageQueueCacheAdmin)
admin.site.register(document_file.DocumentFile,
                    document_file.DocumentFileAdmin)
admin.site.register(queue_exception.QueueException,
                    queue_exception.QueueExceptionAdmin)
admin.site.register(application_notice.ApplicationNotice,
                    application_notice.ApplicationNoticeAdmin)
