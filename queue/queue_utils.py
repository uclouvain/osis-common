import pika
from django.conf import settings
import logging
from typing import Optional, Dict

if hasattr(settings, 'QUEUE_SSL_CONEXION') and settings.QUEUE_SSL_CONEXION:
    import ssl

logger = logging.getLogger(settings.DEFAULT_LOGGER)
queue_exception_logger = logging.getLogger(settings.QUEUE_EXCEPTION_LOGGER)


def get_pika_connexion_parameters(queue_name='', client_properties: Optional[Dict] = None) -> pika.ConnectionParameters:
    if hasattr(settings, 'QUEUE_SSL_CONEXION') and settings.QUEUE_SSL_CONEXION:
        logger.debug("Connecting to {0} (queue name = {1})... en SSL".format(settings.QUEUES.get('QUEUE_URL'),
                                                                             queue_name))
        context = ssl.create_default_context(cafile=settings.get('QUEUE_CLIENT_CA_CERT_PATH'))
        context.verify_mode = ssl.CERT_OPTIONAL
        context.load_cert_chain(certfile=settings.get('QUEUE_CLIENT_CERT_PATH'),
                                keyfile=settings.get('QUEUE_CLIENT_CERT_KEY_PATH'))
        ssl_options = pika.SSLOptions(context=context,
                                      server_hostname=settings.QUEUES.get('QUEUE_URL'))
        credentials = pika.PlainCredentials(username=settings.QUEUES.get('QUEUE_USER'),
                                            password=settings.QUEUES.get('QUEUE_PASSWORD'))
        conn_params = pika.ConnectionParameters(host=settings.QUEUES.get('QUEUE_URL'),
                                                port=settings.QUEUES.get('QUEUE_PORT'),
                                                virtual_host=settings.QUEUES.get('QUEUE_CONTEXT_ROOT'),
                                                ssl_options=ssl_options,
                                                credentials=credentials,
                                                client_properties=client_properties)
    else:
        logger.debug("Connecting to {0} (queue name = {1})...".format(settings.QUEUES.get('QUEUE_URL'), queue_name))
        credentials = pika.PlainCredentials(username=settings.QUEUES.get('QUEUE_USER'),
                                            password=settings.QUEUES.get('QUEUE_PASSWORD'))
        conn_params = pika.ConnectionParameters(host=settings.QUEUES.get('QUEUE_URL'),
                                                port=settings.QUEUES.get('QUEUE_PORT'),
                                                virtual_host=settings.QUEUES.get('QUEUE_CONTEXT_ROOT'),
                                                credentials=credentials,
                                                client_properties=client_properties)
    return conn_params
