"""
Created on 06.12.2017

@author: TZHBODA4
"""
import requests
import logging
import xmltodict
from bte.vCloudDirectorAPI import vCloudDirectorAPI

"""def _login(self):
    self.logger.debug('Start log-in process')
    self.logger.debug('Username = %s' % self.username)
    self.logger.debug('password = %s' % self.password)
    url = "%s/api/sessions" % self.host
    self.logger.debug('URL = %s' % url)
    # headers = {'Accept':'application/*+xml;version=%s' %self.apiversion}
    resp = requests.post(url, headers=self.get_vcloud_headers(), auth=(self.username, self.password),
                         verify=self.verify)
    if resp.status_code == 200:
        self.logger.debug("Successfully logged in to vCD %s" % self.host)
        self.token = resp.headers['x-vcloud-authorization']
        self.logger.debug('Token set successfully to: %s' % self.token)
    else:
        self.logger.critical('failed to login to vCD %s with the following status:' % (resp.raise_for_status()))
        self.logger.debug(resp.status_code)
        self.logger.debug(resp.headers)
        self.logger.debug(resp.text)

https://datacenteri.swisscomcloud.com/api/vApp/vm-79265dee-d71f-41df-ab55-5d01c903d323/virtualHardwareSection/disks
https://datacenteri.swisscomcloud.com/api/vApp/vm-79265dee-d71f-41df-ab55-5d01c903d323/virtualHardwareSection/networkCards
https://datacenteri.swisscomcloud.com/api/vApp/vm-79265dee-d71f-41df-ab55-5d01c903d323/virtualHardwareSection/memory
https://datacenteri.swisscomcloud.com/api/vApp/vm-79265dee-d71f-41df-ab55-5d01c903d323/virtualHardwareSection/cpu
"""
logger = logging.getLogger (__name__)


def get_vm_config(vmid):
    url = '%s/api/vApp/vm-%s/virtualHardwareSection' % (self.host, vmid)
    headers = self.get_vcloud_headers ()
    resp = vCloudDirectorAPI.get(url, logger=logger, retry=1)
    # headers = {'Accept':'application/*+xml;version=%s', 'x-vcloud-authorization':self.token %self.apiversion}
    # resp = requests.get(url, headers=headers, verify=self.verify)
    if resp.status_code == 200:
        self.logger.debug('VM %s found')
        output = xmltodict.parse (resp.text)
        self.logger.debug('This is the VM config: %s' % output)
        return output
    elif resp.status_code == 401:
        self.logger.info('Failed to retriev the VM configuration. Response: %s' % resp.status_code)
        self.logger.info('Failed to retriev the VM configuration.')
        return None


def get_vm_id(self, vappid):
    url = 'https://%s/api/query?type=vm&filter=(id==%s)' % (self.host, vappid)


"""
Check if session is still valid, if not get a new token



defdefeck_vcd_session(self):
        checkurl = '%s/api/catalogs/query?format=references' % self.host
        resp = requests.get(checkurl, headers=self.get_vcloud_headers(), verify=True)
        if (resp.status_code != 200):
            self.logger.info('VCD session check not ok, need to re login and get a new token')
            self._login()
        else:
            self.logger.debug('VCD session is still valid')
        return
"""
