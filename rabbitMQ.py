import logging.config
from time import sleep

import lxml.etree as etree
from kombu import Exchange, Queue
from kombu.mixins import ConsumerMixin
from vCloudDirectorAPI import vCDAPI

logger = logging.getLogger(__name__)
debug, info, warning, error, critical = logger.debug, logger.info, logger.warning, logger.error, logger.critical


class BlockingTaskEngineWorker(ConsumerMixin):

    def __init__(self, conf, connection):
        self.vcd = vCDAPI(conf)
        self.namespaces = conf['vcd'].get('namespaces')
        self.filters = conf['bte'].get('filters')
        self.connection = connection
        self.exchange = Exchange(conf['amqp'].get('exchange'), conf['amqp'].get('type'))
        self.queue_arguments = {'x-message-ttl': conf['amqp'].get('message-ttl'),
                                'x-dead-letter-exchange': conf['amqp'].get('dl-exchange')}
        self.queues = [Queue(conf['amqp']['queues'].get('queue'), self.exchange, message_ttl=60, queue_arguments=self.queue_arguments)]

    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=self.queues,
                         callbacks=[self.on_message])]

    def on_message(self, body, message):
        debug('Got message from RabbitMQ: %s' % message.headers)
        info('Start handling of blocking task with ID: %s' % message.headers.get('notification.entityUUID'))
        self.handle_blocking_task(body, message.headers.get('notification.entityUUID'))
        message.ack()

    @staticmethod
    def extract_id(amqp_body, attrib_type, namespace):
        xml_doc = etree.fromstring(amqp_body)
        link_lst = xml_doc.xpath('//x:EntityLink', namespaces={'x': namespace})
        result = [el.attrib['id'] for el in link_lst if el.attrib['type'] == attrib_type]
        id = result[0].split(':')
        return id[id.__len__()-1]

    def handle_blocking_task(self, amqp_body, blocking_task_id):
        amqp_body = bytes(amqp_body, encoding='UTF-8')
        #blocking_task_id = self.extract_id(amqp_body, 'vcloud:blockingTask', self.namespaces.get('vmext'))
        vm_id = self.extract_id(amqp_body, 'vcloud:vm', self.namespaces.get('vmext'))
        # self.vcd.check_vm_network(vm_id, blocking_task_id)
        print('BlockingTask ID: %s' % blocking_task_id)
        print('VM ID: %s' % vm_id)
        info('%s - checking VM(%s) against the following filters: %s' % (blocking_task_id, vm_id, self.filters))
        for fltr in self.filters:
            result = self.vcd.check_vm_configuration(vm_id, blocking_task_id, fltr)
            if not result[0]:
                info('%s - VM(%s) configuration check failed during %s check' % (blocking_task_id, vm_id, fltr))
                message = result[1]
                self.vcd.take_action_on_blockingtask(blocking_task_id, 'abort', message)
                break
            else:
                continue
        else:
            info('%s - VM(%s) passed all checks' % (blocking_task_id, vm_id))
            message = 'VM(%s) passed all checks - resume blocking task'
            info('blocking task message = %s' % message)
            self.vcd.take_action_on_blockingtask(blocking_task_id, 'resume', message)
