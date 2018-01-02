"""
Created on 20.12.2017

@author: tzhboda4
"""
import logging
import requests
import lxml.etree as etree


class vCDAPI(object):
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
                self.password = file.read()  # .replace('\\n', '')
                file.close()
        except Exception as err:
            self.logger.debug('Error: %s' % err)
        self.verify = conf['vcd'].get('verify') if conf['vcd'].get('verify') else True
        self.max_retries = conf['vcd'].get('retries') if conf['vcd'].get('retries') else 2
        self.token = None
        self.request_exceptions = (requests.exceptions.Timeout, requests.exceptions.ConnectionError,
                                   requests.exceptions.HTTPError)
        self._login()
        self.namespace = {'rasd': 'http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData',
                          'vcloud': 'http://www.vmware.com/vcloud/v1.5',
                          'ovf': 'http://schemas.dmtf.org/ovf/envelope/1'}

    """
    Define some HTTP methods used for vCD API
        _log_requests() and _log_response() used for logging the request and/or response 
        post(), get(), put() and delete() implementing their equivalents in requests but also try to re login after
        a 401 or 403 response code
    """

    @staticmethod
    def _log_request(logger, data=None, headers=None, url=None):
        if logger is not None:
            logger.debug('request url: %s' % url)
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
                logger.debug('response header: %s:%s', header, response.headers[header])
            logger.debug('[%d] %s', response.status_code, response.text)

    def get(self, url, max_retries=1, data=None, **kwargs):
        self.logger.debug('<----- GET request start ----->')
        self._log_request(self.logger, data=data, headers=kwargs.get('headers', None), url=url)
        for i in range(max_retries):
            try:
                response = requests.get(url, data=data, **kwargs)
                if response.status_code == 200:
                    break  # Break and go to final task if request was successful (any status code 200-299)
                elif response.status_code in [401, 403]:
                    self.logger.info(
                        'Try to re-login after HTTP error: %s and send request again' % response.status_code)
                    self._login(logging=False)
                    response.raise_for_status()
                else:
                    response.raise_for_status()  # raise for any other HTTP status than the ones handled above
            except self.request_exception:
                continue
            finally:
                self._log_response(self.logger, response)
                self.logger.debug('<----- GET request end ----->')
                return response

    def post(self, url, max_retries=0, data=None, json=None, **kwargs):
        self.logger.debug('<----- POST request start ----->')
        self._log_request(self.logger, data=data, headers=kwargs.get('headers', None), url=url)
        for i in range(max_retries):
            try:
                response = requests.post(url, data=data, json=json, **kwargs)
                if response.status_code == 200:
                    break  # Break and go to final task if request was successful (any status code 200-299)
                elif response.status_code in [401, 403]:
                    self.logger.info(
                        'Try to re-login after HTTP error: %s and send request again' % response.status_code)
                    self._login(logging=False)
                    response.raise_for_status()
                else:
                    response.raise_for_status()  # raise for any other HTTP status than the ones handled above
            except self.request_exceptions:
                continue
            finally:
                self._log_response(self.logger, response)
                self.logger.debug('<----- POST request end ----->')
                return response

    def put(self, url, max_retries=0, data=None, **kwargs):
        self.logger.debug('<----- PUT request start ----->')
        self._log_request(self.logger, data=data, headers=kwargs.get('headers', None), url=url)
        for i in range(max_retries):
            try:
                response = requests.put(url, data=data, **kwargs)
                if response.status_code < 300:
                    break  # Break and go to final task if request was successful (any status code 200-299)
                elif response.status_code in [401, 403]:
                    self.logger.info(
                        'Try to re-login after HTTP error: %s and send request again' % response.status_code)
                    self._login(logging=False)
                    response.raise_for_status()
                else:
                    response.raise_for_status()  # raise for any other HTTP status than the ones handled above
            except requests.exceptions.HTTPError:
                continue
            finally:
                self._log_response(self.logger, response)
                self.logger.debug('<----- PUT request end ----->')
                return response

    def delete(self, url, max_retries=0, data=None, **kwargs):
        self.logger.debug('<----- DELETE request start ----->')
        self._log_request(self.logger, data=data, headers=kwargs.get('headers', None), url=url)
        for i in range(max_retries):
            try:
                response = requests.delete(url, **kwargs)
                if response.status_code == 200:
                    break  # Break and go to final task if request was successful (any status code 200-299)
                elif response.status_code in [401, 403]:
                    self.logger.info(
                        'Try to re-login after HTTP error: %s and send request again' % response.status_code)
                    self._login(logging=False)
                    response.raise_for_status()
                else:
                    response.raise_for_status()  # raise for any other HTTP status than the ones handled above
            except requests.exceptions.HTTPError:
                continue
            finally:
                self._log_response(self.logger, response)
                self.logger.debug('<----- DELETE request end ----->')
                return response

    """
    Define all functions that are relevant regarding the vCD API
    """

    def get_vcloud_headers(self) -> object:  # returns vcd specific headers
        headers = {"x-vcloud-authorization": self.token, "Accept": "application/*+xml;version=" + self.apiversion}
        return headers

    def _login(self, logging=True):
        url = '%s/api/sessions' % self.host
        if logging:
            self.logger.debug('Start log-in process')
            self.logger.debug('username: %s and password: %s ' % (self.username, self.password))
            self._log_request(self.logger, headers=self.get_vcloud_headers(), url=url)
        for i in range(self.max_retries):
            try:
                response = requests.post(url, headers=self.get_vcloud_headers(), auth=(self.username, self.password),
                                         verify=self.verify)
                if response.status_code == 200:
                    self.token = response.headers['x-vcloud-authorization']
                    self.logger.info("Successfully logged in to vCD %s" % self.host)
                    self.logger.debug('Token successfully set to: %s' % self.token)
                else:
                    response.raise_for_status()
            except self.request_exceptions as error:
                self.logger.critical('Error: %s - going to retry login' % error)
                continue
            finally:
                if logging:
                    self._log_response(self.logger, response)

    def _logout(self):
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
                    self.logger.critical('failed to logout from vCD %s with the following status: %s' % (
                    self.host, response.status_code))
                    response.raise_for_status()
            except self.request_exceptions as error:
                self.logger.debug('Error: %s - going to retry logout' % error)
                continue

    def get_vm_cpu_config(self, vmid):
        url = '%s/api/vApp/vm-%s/virtualHardwareSection/cpu' % (self.host, vmid)
        response = self.get(url, headers=self.get_vcloud_headers(), verify=self.verify)
        if response.status_code == 200:
            self.logger.debug('VM %s found')
            xml_doc = etree.fromstring(response.content)
            self.logger.debug('This is the VM config: %s' % xml_doc)
            return xml_doc
        elif response.status_code == 401:
            self.logger.info('Failed to retrieve the VM configuration. Response: %s' % response.status_code)
            self.logger.info('Failed to retrieve the VM configuration.')
            return None

    def get_vm_memory_config(self, vmid):
        url = '%s/api/vApp/vm-%s/virtualHardwareSection/memory' % (self.host, vmid)
        response = self.get(url, max_retries=self.max_retries, headers=self.get_vcloud_headers())
        # resp = requests.get(url, headers=headers, verify=self.verify)
        if response.status_code == 200:
            self.logger.debug('VM %s found')
            xml_doc = etree.fromstring(response.content)
            self.logger.debug('This is the VM config: %s' % xml_doc)
            return recs
        elif response.status_code == 401:
            self.logger.info('Failed to retrieve the VM configuration. Response: %s' % response.status_code)
            self.logger.info('Failed to retrieve the VM configuration.')
            return None

    def get_vm_disk_config(self, vmid):
        url = '%s/api/vApp/vm-%s/virtualHardwareSection/disks' % (self.host, vmid)
        response = self.get(url, max_retries=self.max_retries, headers=self.get_vcloud_headers())
        # resp = requests.get(url, headers=headers, verify=self.verify)
        if response.status_code == 200:
            self.logger.debug('VM %s found')
            xml_doc = etree.fromstring(response.content)
            recs = xml_doc.xpath('//x:Item', namespaces={'x': self.namespace})
            # vmconfig = [el.attrib for el in recs]
            self.logger.debug('This is the VM config: %s' % xml_doc)
            return recs
        elif response.status_code == 401:
            self.logger.info('Failed to retrieve the VM configuration. Response: %s' % response.status_code)
            self.logger.info('Failed to retrieve the VM configuration.')
            return None

    def get_vm_network_config(self, vmid):
        url = '%s/api/vApp/vm-%s/virtualHardwareSection/networkCards' % (self.host, vmid)
        response = self.get(url, max_retries=self.max_retries, headers=self.get_vcloud_headers())
        # resp = requests.get(url, headers=headers, verify=self.verify)
        if response.status_code == 200:
            self.logger.debug('VM %s found')
            xml_doc = etree.fromstring(response.content)
            recs = xml_doc.xpath('//x:Item', namespaces={'x': self.namespace})
            # vmconfig = [el.attrib for el in recs]
            self.logger.debug('This is the VM config: %s' % xml_doc)
            return recs
        elif response.status_code == 401:
            self.logger.info('Failed to retrieve the VM configuration. Response: %s' % response.status_code)
            self.logger.info('Failed to retrieve the VM configuration.')
            return None

    def get_vm_href(self, urn):
        url = '%s/api/entity/%s' % (self.host, urn)
        response = self.get(url, max_retries=self.max_retries, headers=self.get_vcloud_headers())
        xml_doc = etree.fromstring(response.content)
        link_lst = xml_doc.xpath('//x:Link', namespaces={'x': self.namespace['vcloud']})
        vmhrefs = [el.attrib['href'] for el in link_lst if el.attrib['type'] == 'application/vnd.vmware.vcloud.vm+xml']
        return vmhrefs

    def get_blocking_task_by_id(self, taskid):
        url = '%s/api/admin/extension/blockingTask/%s' % (self.host, taskid)
        response = self.get(url, max_retries=self.max_retries, headers=self.get_vcloud_headers(), logger=self.logger)

    def take_action_on_blockingtask(self, taskid, action, msg):
        self.logger.info("Taking action %s on task %s" % (action, taskid))
        """ construct url with the given task ID and action and prepare body """
        url = '%s/api/admin/extension/blockingTask/%s/action/%s' % (self.host, taskid, action.lower())
        body = '<?xml version="1.0" encoding="UTF-8"?><BlockingTaskOperationParams xmlns="http://www.vmware.com/vcloud/extension/v1.5"><Message>%s</Message></BlockingTaskOperationParams>' % msg
        response = self.post(url, max_retries=self.max_retries, headers=self.get_vcloud_headers(), data=body,
                             logger=self.logger)
        if response.status_code == 200:
            self.logger.info("Action %s on task %s executed successfully" % (action, taskid))
