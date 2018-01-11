"""
Created on 19.12.2017

@author: tzhboda4
"""
import os
import json
import logging.config
from kombu import Connection
from rabbitMQ import BlockingTaskEngineWorker


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
            bteconfig = json.load(f)
            logging.config.dictConfig(bteconfig)
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
    config = read_config('configuration/config.json')

    try:
        with open(config['amqp'].get('passwordFile'), 'rt') as file:
            password = file.read()  # .replace('\\n', '')
            file.close()
    except Exception as err:
        logger.debug('Error: %s' % err)
    with Connection(config['amqp'].get('host'), userid=config['amqp'].get('username'),
                    password=password, heartbeat=4,) as conn:
        worker = BlockingTaskEngineWorker(config, conn)
        worker.run()
