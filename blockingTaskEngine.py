"""
Created on 19.12.2017

@author: tzhboda4
"""
import os
import json
import logging.config
#import bte.vCD
from bte.rabbitMQ import AMQP
from bte.vCloudDirectorAPI import vCDAPI
#import time


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


if __name__ == '__main__':

    """
    start Program        
    """

    setup_logging('configuration/logging.json')
    logger = logging.getLogger('blockingTaskEngine')
    logger.info("Completed configuring logger().")
    conf = read_config('configuration/config.json')
    vcdapi = vCDAPI(conf)
    #vmconfig = vCDAPI.get_vm_config('79265dee-d71f-41df-ab55-5d01c903d323')
    #logger.info(vmconfig)
    amqp = AMQP(conf)

"""
    while True:
        logger.debug('checking VCD session...')
        vcd.checkVCDSession()
        time.sleep(15)
"""
