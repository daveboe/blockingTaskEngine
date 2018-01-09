"""
Created on 19.12.2017

@author: tzhboda4
"""
import os
import json
import logging.config
import lxml.etree as etree
#from rabbitMQ import Worker
from kombu import Connection, Exchange, Queue
from kombu.mixins import ConsumerMixin
from vCloudDirectorAPI import vCDAPI


def setup_logging(
        default_path='logging.json',
        default_level=logging.DEBUG,
        env_key='LOG_CFG'
):
    """
    Setup logging configuration
    """
    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = json.load(f)
            logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)


def read_config(default_path='config.json'):
    path = default_path
    try:
        with open(path) as f:
            config = json.load(f)
            logger.info("successfully loaded JSON config")
        return config
    except Exception:
        logger.info('error while loading JSON config')
        logger.debug("Error while parsing JSON ", exc_info=True)


class BlockingTaskEngineWorker(ConsumerMixin):

    def __init__(self, conf, connection):
        self.vcd=vCDAPI(conf)
        self.namespaces = conf['vcd'].get('namespaces')
        self.filters = conf['bte'].get('filters')
        self.connection = connection
        self.exchange = Exchange(conf['amqp'].get('exchange'), conf['amqp'].get('type'))
        self.queue_arguments = {'x-message-ttl': conf['amqp'].get('message-ttl'),
                                'x-dead-letter-exchange': conf['amqp'].get('dl-exchange')}
        self.queues = [Queue(conf['amqp']['queues'].get('queue'), self.exchange, message_ttl=300, queue_arguments=self.queue_arguments)]

    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=self.queues,
                         callbacks=[self.on_message])]

    def on_message(self, body, message):
        self.handle_blocking_task(body)
        message.ack()

    @staticmethod
    def extract_id(amqp_body, attrib_type, namespace):
        xml_doc = etree.fromstring(amqp_body.content)
        link_lst = xml_doc.xpath('//x:Link', namespaces={'x': namespace})
        result = [el.attrib['id'] for el in link_lst if el.attrib['type'] == attrib_type]
        id = result[0].split(':')
        return id[id.__len__()-1]




    def handle_blocking_task(self, body):
        blocking_task = self.vcd.get_blocking_task_by_id(self.extract_id(body, 'vcloud:blocking', self.namespaces))
        vm_id = self.extract_id(body, 'vcloud:vm', self.namespaces)
        for filter in self.filters:
            if filter == 'vmMaxMemory':
                return



if __name__ == '__main__':

    """
    start Program        
    """


    setup_logging('configuration/logging.json')
    logger = logging.getLogger('blockingTaskEngine')
    logger.info("Completed configuring logger().")
    config = read_config('configuration/config.json')

    vcdapi = vCDAPI(config)
    """
    vmconfig = vcdapi.get_vm_cpu_config('79265dee-d71f-41df-ab55-5d01c903d323')
    ns = {'rasd': 'http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData',
          'vcloud': 'http://www.vmware.com/vcloud/v1.5', 'ovf': 'http://schemas.dmtf.org/ovf/envelope/1',
          'vmext': 'http://www.vmware.com/vcloud/extension/v1.5'}
    logger.info(':::: read config ::::')
    for item in vmconfig.findall('ovf:Item', ns):
        elem = item.find('rasd:Description', ns)
        print(elem.text)
        qty = item.find('rasd:VirtualQuantity', ns)
        print(' |--> ', qty.text)
    logger.info(':::: read config done ::::')
    vmhref = vcdapi.resolve_vm_entity('urn:vcloud:vm:965c2aac-8c5b-4ba7-87a8-72cafa759609')
    logger.info(vmhref)

    #xml_doc = etree.XML('msg.xml')
    #link_lst = xml_doc.xpath('//x:Link', namespaces={'x': ns})
    result = ['urn:vcloud:vm:7ac537dd-f582-459f-90eb-05c9dcc0aae6']
    vmid = result[0].split(':')
    logger.info(vmid[vmid.__len__()-1])

    with Connection(config['amqp'].get('host'), userid=config['amqp'].get('username'),
                    password=config['amqp'].get('password'), heartbeat=4,) as conn:
        worker = Worker(config, conn)
        worker.run()
    """
    print(vcdapi.check_vm_network('79265dee-d71f-41df-ab55-5d01c903d323'))

