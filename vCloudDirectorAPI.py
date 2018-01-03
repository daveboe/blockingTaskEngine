"""
Created on 20.12.2017

@author: tzhboda4
"""
import logging
import requests
import lxml.etree as etree

logger = logging.getLogger(__name__)
debug, info, warning, error, critical = logger.debug, logger.info, logger.warning, logger.error, logger.critical


class vCDAPI(object):
    """
    classdocs
    """

    def __init__(self, conf):
        """
        Create a VCD connection
        """
        # self.logger = logging.getLogger(__name__)
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
            debug('Error: %s' % err)
        self.verify = conf['vcd'].get('verify') if conf['vcd'].get('verify') else True
        self.max_retries = conf['vcd'].get('retries') if conf['vcd'].get('retries') else 2
        self.token = None
        self.request_exceptions = (requests.exceptions.Timeout, requests.exceptions.ConnectionError,
                                   requests.exceptions.HTTPError)
        self._login()
        self.namespace = conf['vcd'].get('namespaces')

    """
    Define some HTTP methods used for vCD API
        _log_requests() and _log_response() used for logging the request and/or response 
        post(), get(), put() and delete() implementing their equivalents in requests but also try to re login after
        a 401 or 403 response code
    """

    @staticmethod
    def _log_request(data=None, headers=None, url=None):
        if logger is not None:
            debug('request url: %s' % url)
            if headers is not None:
                for header in headers:
                    debug(
                        'request header: %s: %s',
                        header,
                        headers[header])
            if data is not None:
                debug('request data:\n %s', data)

    @staticmethod
    def _log_response(response):
        if logger is not None:
            for header in response.headers:
                debug('response header: %s:%s', header, response.headers[header])
            debug('[%d] %s', response.status_code, response.request)

    def get(self, url, max_retries=1, data=None, **kwargs):
        debug('<----- GET request start ----->')
        self._log_request(data=data, headers=kwargs.get('headers', None), url=url)
        for i in range(max_retries):
            try:
                response = requests.get(url, data=data, **kwargs)
                if response.status_code == 200:
                    break  # Break and go to final task if request was successful (any status code 200-299)
                elif response.status_code in [401, 403]:
                    info('Try to re-login after HTTP error: %s and send request again' % response.status_code)
                    self._login(log=False)
                    response.raise_for_status()
                else:
                    response.raise_for_status()  # raise for any other HTTP status than the ones handled above
            except self.request_exceptions:
                continue
            finally:
                self._log_response(response)
                debug('<----- GET request end ----->')
                return response

    def post(self, url, max_retries=0, data=None, json=None, **kwargs):
        debug('<----- POST request start ----->')
        self._log_request(data=data, headers=kwargs.get('headers', None), url=url)
        for i in range(max_retries):
            try:
                response = requests.post(url, data=data, json=json, **kwargs)
                if response.status_code == 200:
                    break  # Break and go to final task if request was successful (any status code 200-299)
                elif response.status_code in [401, 403]:
                    info('Try to re-login after HTTP error: %s and send request again' % response.status_code)
                    self._login(log=False)
                    response.raise_for_status()
                else:
                    response.raise_for_status()  # raise for any other HTTP status than the ones handled above
            except self.request_exceptions:
                continue
            finally:
                self._log_response(response)
                debug('<----- POST request end ----->')
                return response

    def put(self, url, max_retries=0, data=None, **kwargs):
        debug('<----- PUT request start ----->')
        self._log_request(data=data, headers=kwargs.get('headers', None), url=url)
        for i in range(max_retries):
            try:
                response = requests.put(url, data=data, **kwargs)
                if response.status_code < 300:
                    break  # Break and go to final task if request was successful (any status code 200-299)
                elif response.status_code in [401, 403]:
                    info('Try to re-login after HTTP error: %s and send request again' % response.status_code)
                    self._login(log=False)
                    response.raise_for_status()
                else:
                    response.raise_for_status()  # raise for any other HTTP status than the ones handled above
            except requests.exceptions.HTTPError:
                continue
            finally:
                self._log_response(response)
                debug('<----- PUT request end ----->')
                return response

    def delete(self, url, max_retries=0, data=None, **kwargs):
        debug('<----- DELETE request start ----->')
        self._log_request(data=data, headers=kwargs.get('headers', None), url=url)
        for i in range(max_retries):
            try:
                response = requests.delete(url, **kwargs)
                if response.status_code == 200:
                    break  # Break and go to final task if request was successful (any status code 200-299)
                elif response.status_code in [401, 403]:
                    info('Try to re-login after HTTP error: %s and send request again' % response.status_code)
                    self._login(log=False)
                    response.raise_for_status()
                else:
                    response.raise_for_status()  # raise for any other HTTP status than the ones handled above
            except requests.exceptions.HTTPError:
                continue
            finally:
                self._log_response(response)
                debug('<----- DELETE request end ----->')
                return response

    """
    Define all functions that are relevant regarding the vCD API
    """

    def get_vcloud_headers(self) -> object:  # returns vcd specific headers
        headers = {"x-vcloud-authorization": self.token, "Accept": "application/*+xml;version=" + self.apiversion}
        return headers

    def _login(self, log=True):
        url = '%s/api/sessions' % self.host
        if log:
            debug('<----- Start login process ----->')
            debug('username: %s and password: %s ' % (self.username, self.password))
            self._log_request(headers=self.get_vcloud_headers(), url=url)
        for i in range(self.max_retries):
            try:
                response = requests.post(url, headers=self.get_vcloud_headers(), auth=(self.username, self.password),
                                         verify=self.verify)
                if response.status_code == 200:
                    self.token = response.headers['x-vcloud-authorization']
                    info("Successfully logged in to vCD %s" % self.host)
                    debug('Token successfully set to: %s' % self.token)
                    break
                else:
                    response.raise_for_status()
            except self.request_exceptions as err:
                critical('Error: %s - going to retry login' % err)
                continue
            finally:
                if log:
                    self._log_response(response)
                    debug('<----- End login process ----->')

    def _logout(self):
        debug('logout from VCD %s' % self.host)
        url = '%s/api/sessions' % self.host
        for i in range(self.max_retries):
            try:
                debug('username: %s and password: ' % self.password)
                self._log_request(headers=self.get_vcloud_headers(), url=url)
                response = self.delete(url, max_retries=self.max_retries, headers=self.get_vcloud_headers())
                self._log_response(response)
                if response.status_code == 200:
                    debug("Successfully logged in to vCD %s" % self.host)
                    self.token = response.headers['x-vcloud-authorization']
                    debug('Token set successfully to: %s' % self.token)
                    break
                else:
                    critical('failed to logout from vCD %s with the following status: %s' % (
                        self.host, response.status_code))
                    response.raise_for_status()
            except self.request_exceptions as err:
                debug('Error: %s - going to retry logout' % err)
                continue

    def get_vm_cpu_config(self, vmid):
        url = '%s/api/vApp/vm-%s/virtualHardwareSection/cpu' % (self.host, vmid)
        response = self.get(url, headers=self.get_vcloud_headers(), verify=self.verify)
        if response.status_code == 200:
            debug('VM %s found')
            xml_doc = etree.fromstring(response.content)
            debug('This is the VM config: %s' % xml_doc)
            return xml_doc
        elif response.status_code == 401:
            info('Failed to retrieve the VM configuration. Response: %s' % response.status_code)
            info('Failed to retrieve the VM configuration.')
            return None

    def get_vm_memory_config(self, vmid):
        url = '%s/api/vApp/vm-%s/virtualHardwareSection/memory' % (self.host, vmid)
        response = self.get(url, max_retries=self.max_retries, headers=self.get_vcloud_headers())
        # resp = requests.get(url, headers=headers, verify=self.verify)
        if response.status_code == 200:
            debug('VM %s found')
            xml_doc = etree.fromstring(response.content)
            debug('This is the VM config: %s' % xml_doc)
            return xml_doc
        elif response.status_code == 401:
            info('Failed to retrieve the VM configuration. Response: %s' % response.status_code)
            info('Failed to retrieve the VM configuration.')
            return None

    def get_vm_disk_config(self, vmid):
        url = '%s/api/vApp/vm-%s/virtualHardwareSection/disks' % (self.host, vmid)
        response = self.get(url, max_retries=self.max_retries, headers=self.get_vcloud_headers())
        # resp = requests.get(url, headers=headers, verify=self.verify)
        if response.status_code == 200:
            debug('VM %s found')
            xml_doc = etree.fromstring(response.content)
            recs = xml_doc.xpath('//x:Item', namespaces={'x': self.namespace})
            # vmconfig = [el.attrib for el in recs]
            debug('This is the VM config: %s' % xml_doc)
            return recs
        elif response.status_code == 401:
            info('Failed to retrieve the VM configuration. Response: %s' % response.status_code)
            info('Failed to retrieve the VM configuration.')
            return None

    def get_vm_network_config(self, vmid):
        url = '%s/api/vApp/vm-%s/virtualHardwareSection/networkCards' % (self.host, vmid)
        response = self.get(url, max_retries=self.max_retries, headers=self.get_vcloud_headers())
        # resp = requests.get(url, headers=headers, verify=self.verify)
        if response.status_code == 200:
            debug('VM %s found')
            xml_doc = etree.fromstring(response.content)
            recs = xml_doc.xpath('//x:Item', namespaces={'x': self.namespace})
            # vmconfig = [el.attrib for el in recs]
            debug('This is the VM config: %s' % xml_doc)
            return recs
        elif response.status_code == 401:
            info('Failed to retrieve the VM configuration. Response: %s' % response.status_code)
            info('Failed to retrieve the VM configuration.')
            return None

    def resolve_vm_entity(self, urn):
        url = '%s/api/entity/%s' % (self.host, urn)
        try:
            response = self.get(url, max_retries=self.max_retries, headers=self.get_vcloud_headers())
            if response.status_code == 200:
                debug('Entity with ID: %s found' % urn)
                return response
            else:
                response.raise_for_status()
        except self.request_exceptions as err:
            error('Error: %s' % err)
            return None

    def get_blocking_task_by_id(self, taskid):
        url = '%s/api/admin/extension/blockingTask/%s' % (self.host, taskid)
        response = self.get(url, max_retries=self.max_retries, headers=self.get_vcloud_headers())

    def take_action_on_blockingtask(self, taskid, action, msg):
        info("Taking action %s on task %s" % (action, taskid))
        """ construct url with the given task ID and action and prepare body """
        url = '%s/api/admin/extension/blockingTask/%s/action/%s' % (self.host, taskid, action.lower())
        body = '<?xml version="1.0" encoding="UTF-8"?><BlockingTaskOperationParams xmlns="http://www.vmware.com/vcloud/extension/v1.5"><Message>%s</Message></BlockingTaskOperationParams>' % msg
        response = self.post(url, max_retries=self.max_retries, headers=self.get_vcloud_headers(), data=body)
        if response.status_code == 200:
            info("Action %s on task %s executed successfully" % (action, taskid))
