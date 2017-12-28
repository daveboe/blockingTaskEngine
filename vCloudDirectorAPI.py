"""
Created on 20.12.2017

@author: tzhboda4
"""
import logging
import requests
import time
import xmltodict
from pip._vendor.retrying import retry
import bte.helper


class vCDAPI (object):
    """
    classdocs
    """

    def __init__(self, conf):
        """
        Create a VCD connection
        """
        self.logger = logging.getLogger(__name__)
        self.conf = conf
        self.host = conf['vcd'].get('host')
        if not (self.host.startswith('https://') or self.host.startswith('http://')):
            self.host = 'https://' + self.host
        self.apiversion = conf['vcd'].get('apiversion') if conf['vcd'].get('apiversion') else '9.0'
        self.username = conf['vcd'].get('username')
        try:
            with open('configuration/password.txt', 'rt') as file:
                self.password = file.read() #.replace('\\n', '')
                file.close()
        except Exception as err:
            self.logger.debug('Error: %s' % err)
        self.verify = conf['vcd'].get('verify') if conf['vcd'].get('verify') else True
        self.max_retries = conf['vcd'].get('retries') if conf['vcd'].get('retries') else 1
        self.token = None
        self._login()

    """
    Define some HTTP methods used for vCD API
        _log_requests() and _log_response() used for logging the request and/or response 
        post(), get(), put() and delete() implementing their equivalents in requests but also try to re login after
        a 401 or 403 response code
    """

    @staticmethod
    def _log_request(logger, data=None, headers=None, url=None):
        if logger is not None:
            logger.debug('url=%s' % url)
            if headers is not None:
                for header in headers:
                    logger.debug(
                        'request header: %s: %s',
                        header,
                        headers[header])
            if data is not None:
                logger.debug('request data:\n %s', data)

    @staticmethod
    def _log_response(logger, response):
        if logger is not None:
            for header in response.headers:
                logger.debug('response header: %s: %s', header, response.headers[header])
            logger.debug('[%d] %s', response.status_code, response.text)

    def get(self, url, max_retries=0, data=None, **kwargs):
        for i in range(max_retries):
            self.logger.debug('%s' % i.tostring())
            try:
                self._log_request(self.logger, data=data, headers=kwargs.get('headers', None), url=url)
                response = requests.get(url, data=data, **kwargs)
                self._log_response(self.logger, response)
                if response.status_code in [401, 403]:
                    self.logger.debug('try to re-login after HTTP error: %s' % response.status_code)
                    self.logger.info('try to POST the request again. remaining retries: %s' % (max_retries-i))
                    self._login()
                    response.raise_for_status()
                else:
                    return response
            except requests.exceptions.HTTPError:
                continue
            else:
                return response

    def post(self, url, max_retries=0, data=None, json=None, **kwargs):
        for i in range(max_retries):
            self.logger.debug('%i' % i)
            try:
                self._log_request(self.logger, data=data, headers=kwargs.get('headers', None), url=url)
                response = requests.post(url, data=data, json=json, **kwargs)
                self._log_response(self.logger, response)
                if response.status_code in [401, 403]:
                    self.logger.debug('try to re-login after HTTP error: %s' % response.status_code)
                    self.logger.info('try to POST the request again. remaining retries: %s' % (max_retries-i))
                    self._login()
                    response.raise_for_status()
                else:
                    return response
            except requests.exceptions.HTTPError:
                continue
            else:
                return response

    def put(self, url, max_retries=0, data=None, **kwargs):
        for i in range(max_retries):
            try:
                self._log_request(self.logger, data=data, headers=kwargs.get('headers', None), url=url)
                response = requests.get(url, data=data, **kwargs)
                self._log_response(self.logger, response)
                if response.status_code in [401, 403]:
                    self.logger.debug('try to re-login after HTTP error: %s' % response.status_code)
                    self.logger.info('try to POST the request again. remaining retries: %s' % (max_retries-i))
                    self._login()
                    response.raise_for_status()
                else:
                    return response
            except requests.exceptions.HTTPError:
                continue
            else:
                return response

    def delete(self, url, max_retries=0, data=None, **kwargs):
        for i in range(max_retries):
            try:
                self._log_request(self.logger, data=data, headers=kwargs.get('headers', None), url=url)
                response = requests.delete(url, data=data, **kwargs)
                self._log_response(self.logger, response)
                if response.status_code in [401, 403]:
                    self.logger.debug('try to re-login after HTTP error: %s' % response.status_code)
                    self.logger.info('try to POST the request again. remaining retries: %s' % (max_retries-i))
                    self._login()
                    response.raise_for_status()
                else:
                    return response
            except requests.exceptions.HTTPError:
                continue
            else:
                return response

    """
    Define all functions that are relevant regarding the vCD API
    """

    def get_vcloud_headers(self) -> object:  # returns vcd specific headers
        headers = {"x-vcloud-authorization": self.token, "Accept": "application/*+xml;version=" + self.apiversion}
        return headers

    def _login(self):
        request_exceptions = (requests.exceptions.Timeout, requests.exceptions.ConnectionError,
                              requests.exceptions.HTTPError)
        self.logger.debug('Start log-in process')
        url = '%s/api/sessions' % self.host
        for i in range(self.max_retries):
            try:
                self.logger.debug('username: %s and password: ' % self.password)
                self._log_request(self.logger, headers=self.get_vcloud_headers(), url=url)
                response = requests.post(url, headers=self.get_vcloud_headers(), auth=(self.username, self.password),
                             verify=self.verify)
                self._log_response(self.logger, response)
                if response.status_code == 200:
                    self.logger.debug("Successfully logged in to vCD %s" % self.host)
                    self.token = response.headers['x-vcloud-authorization']
                    self.logger.debug('Token set successfully to: %s' % self.token)
                else:
                    self.logger.critical('failed to login to vCD %s with the following status: %s' % (self.host, response.status_code))
                    self.logger.debug('login status: %s' % response.status_code)
                    response.raise_for_status()
            except request_exceptions as error:
                self.logger.debug('Error: %s - going to retry login' % error)
                continue

    def _logout(self):
        request_exceptions = (requests.exceptions.Timeout, requests.exceptions.ConnectionError,
                              requests.exceptions.HTTPError)
        self.logger.debug('logout from VCD %s' % self.host)
        url = '%s/api/sessions' % self.host
        for i in range(self.max_retries):
            try:
                self.logger.debug('username: %s and password: ' % self.password)
                self._log_request(self.logger, headers=self.get_vcloud_headers(), url=url)
                response = self.delete(url, max_retries=self.max_retries, headers=self.get_vcloud_headers())
                self._log_response(self.logger, response)
                if response.status_code == 200:
                    self.logger.debug("Successfully logged in to vCD %s" % self.host)
                    self.token = response.headers['x-vcloud-authorization']
                    self.logger.debug('Token set successfully to: %s' % self.token)
                else:
                    self.logger.critical('failed to logout from vCD %s with the following status: %s' % (self.host, response.status_code))
                    response.raise_for_status()
            except request_exceptions as error:
                self.logger.debug('Error: %s - going to retry logout' % error)
                continue

    def get_vm_config(self, vmid):
        url = '%s/api/vApp/vm-%s/virtualHardwareSection' % (self.host, vmid)
        resp = self.get(url, max_retries=self.max_retries, headers=self.get_vcloud_headers())
        # resp = requests.get(url, headers=headers, verify=self.verify)
        if resp.status_code == 200:
            self.logger.debug('VM %s found')
            output = xmltodict.parse(resp.text)
            self.logger.debug('This is the VM config: %s' % output)
            return output
        elif resp.status_code == 401:
            self.logger.info('Failed to retrieve the VM configuration. Response: %s' % resp.status_code)
            self.logger.info('Failed to retrieve the VM configuration.')
            return None

    def get_vm_id(self, vappid):
        url = '%s/api/query?type=vm&filter=(id==%s)' % (self.host, vappid)
        resp = self.get(url, max_retries=self.max_retries, headers=self.get_vcloud_headers(), logger=self.logger)

    def get_vcd_task_by_id(self, taskid):
        url = '%s/api/task/%s' % (self.host, taskid)
        resp = self.get(url, max_retries=self.max_retries, headers=self.get_vcloud_headers(), logger=self.logger)
