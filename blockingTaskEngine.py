"""
Created on 19.12.2017

@author: tzhboda4
"""
import os
import json
import logging.config
import lxml.etree as etree
from rabbitMQ import Worker
from kombu import Connection
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
            conf = json.load(f)
            logger.info("successfully loaded JSON config")
        return conf
    except Exception:
        logger.info('error while loading JSON config')
        logger.debug("Error while parsing JSON ", exc_info=True)


def extract_vm_id(amqp_body, namespace):
    xml_doc = etree.fromstring(amqp_body.content)
    link_lst = xml_doc.xpath('//x:Link', namespaces={'x': namespace})
    result = [el.attrib['id'] for el in link_lst if el.attrib['type'] == 'vcloud:vm']
    vm_id = result[0].strip()
    return vm_id[0]


if __name__ == '__main__':

    """
    start Program        
    """

    setup_logging('configuration/logging.json')
    logger = logging.getLogger('blockingTaskEngine')
    logger.info("Completed configuring logger().")
    conf = read_config('configuration/config.json')
    vcdapi = vCDAPI(conf)
    vmconfig = vcdapi.get_vm_cpu_config('79265dee-d71f-41df-ab55-5d01c903d323')
    ns = {'rasd': 'http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData',
          'vcloud': 'http://www.vmware.com/vcloud/v1.5', 'ovf': 'http://schemas.dmtf.org/ovf/envelope/1'}
    logger.info(':::: read config ::::')
    for item in vmconfig.findall('ovf:Item', ns):
        elem = item.find('rasd:Description', ns)
        print(elem.text)
        qty = item.find('rasd:VirtualQuantity', ns)
        print(' |--> ', qty.text)
    logger.info(':::: read config done ::::')
    vmhref = vcdapi.resolve_vm_entity('urn:vcloud:vm:965c2aac-8c5b-4ba7-87a8-72cafa759609')
    logger.info(vmhref)

    with Connection(conf['amqp'].get('host'), userid=conf['amqp'].get('username'),
                    password=conf['amqp'].get('password'), heartbeat=4,) as conn:
        worker = Worker(conf, conn)
        worker.run()

