"""
Created on 19.12.2017

@author: tzhboda4
"""
import logging
from kombu import Connection, Exchange, Queue
from kombu.mixins import ConsumerMixin


class Worker(ConsumerMixin):
    def __init__(self, conf, connection):
        self.logger = logging.getLogger(__name__)
        self.connection = connection
        self.exchange = Exchange(conf['amqp'].get('exchange'), conf['amqp'].get('type'))
        self.queue_arguments = {'x-message-ttl': conf['amqp'].get('message-ttl'),
                                'x-dead-letter-exchange': conf['amqp'].get('dl-exchange')}
        self.logger.debug(conf['amqp']['queues'].get('queue'))
        self.queues = [Queue(conf['amqp']['queues'].get('queue'), self.exchange, message_ttl=300, queue_arguments=self.queue_arguments)]
        Queue()

    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=self.queues,
                         callbacks=[self.on_message])]

    def on_message(self, body, message):
        print('Got message: {0}'.format(body))
        print('message : {0}'.format(message.headers))
        message.ack()
