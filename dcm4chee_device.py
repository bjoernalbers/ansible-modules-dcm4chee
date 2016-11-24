#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# (c) 2016, Björn Albers <bjoernalbers@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.


DOCUMENTATION = '''
module: dcm4chee_device
author: 'Björn Albers <bjoernalbers@gmail.com>'
version_added: '2.3'
short_description: Manage DCM4CHEE Devices
description:
    - Manage DICOM devices on DCM4CHEE Archive 5 Light
options:
    api_url:
        required: true
        description:
            - Base-URL of DCM4CHEE API, i.e. http://1.2.3.4:8080/dcm4chee-arc/
    name:
        required: true
        description:
            - Name of device
        aliases: [ 'device' ]
    host:
        required: true
        description:
            - Address / Hostname of device
    port:
        required: true
        description:
            - TCP Port of device
    aetitle:
        required: true
        description:
            - AETitle of device
    state:
        required: true
        choices: [ 'present', 'absent' ]
        description:
            - State of device, which is either C(present) or C(absent)
requirements:
    - a working installation of DCM4CHEE Archive 5 Light
'''

RETURN = '''
# These values will be returned on success...
name:
    description: Name of device
    type: string
    sample: 'workstation42'
state:
    description: Current state of the device
    type: string
    sample: 'present'
changed:
    description: Was the device changed?
    type: boolean
    sample: True
'''

EXAMPLES = '''
- name: add dicom devices
  dcm4chee_device:
      api_url: http://1.2.3.4:8080/dcm4chee-arc/
      name:    '{{ item.name }}'
      host:    '{{ item.host }}'
      port:    '{{ item.aetitle }}'
      aetitle: '{{ item.aetitle }}'
      state: present
  with_items:
  - name:    workstation23
    host:    192.168.0.100
    port:    11112
    aetitle: HELLOWORLD
  - name:    workstationw42
    host:    192.168.0.200
    port:    11112
    aetitle: CHUNKYBACON
'''


try:
      import json
except ImportError:
      import simplejson as json

import urllib2

        
class DeviceAPI:
    def __init__(self, api_url, name):
        self.url = api_url + 'devices' + '/' + name

    def create(self, device):
        request = self.__request__(device.to_json(), 'POST')
        response = self.__urlopen__(request, ignore_error=409)
        return True if response else False

    def read(self):
        request = self.__request__()
        response = self.__urlopen__(request, ignore_error=404)
        return Device.from_json(response.read()) if response else None

    def update(self, device):
        request = self.__request__(device.to_json(), 'PUT')
        response = self.__urlopen__(request, ignore_error=404)
        return True if response else False

    def delete(self):
        request = self.__request__(None, 'DELETE')
        response = self.__urlopen__(request, ignore_error=404)
        return True if response else False

    def __request__(self, data=None, method='GET'):
        request = urllib2.Request(self.url, data)
        request.add_header('Content-Type', 'application/json')
        request.get_method = lambda: method
        return request

    def __urlopen__(self, request, ignore_error=None):
        try:
            response = urllib2.urlopen(request)
        except urllib2.HTTPError as error:
            if error.code == ignore_error:
                return None
            else:
                raise
        else:
            return response

    def __str__(self):
        return str(self.__dict__)


class Device:
    def __init__(self, name, host, port, aetitle):
        self.name    = name
        self.host    = host
        self.port    = port
        self.aetitle = aetitle

    @classmethod
    def from_json(cls, string):
        data = json.loads(string)
        return cls(
            name = data['dicomDeviceName'],
            host = data['dicomNetworkConnection'][0]['dicomHostname'],
            port = data['dicomNetworkConnection'][0]['dicomPort'],
            aetitle = data['dicomNetworkAE'][0]['dicomAETitle'])

    def to_json(self):
        return json.dumps({
            'dicomDeviceName': self.name,
            'dicomInstalled': True,
            'dicomNetworkConnection': [
                {
                'cn': 'dicom',
                'dicomHostname': self.host,
                'dicomPort': self.port
                }
            ],
            'dicomNetworkAE': [
                {
                    'dicomAETitle': self.aetitle,
                    'dicomAssociationInitiator': True,
                    'dicomAssociationAcceptor': True,
                    'dicomNetworkConnectionReference': [
                        '/dicomNetworkConnection/0'
                    ]
                }
            ]
        })

    def __str__(self):
        return str(self.__dict__)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self.__eq__(other)


def main():

    module = AnsibleModule(
        argument_spec = dict(
            api_url = dict(
                required = True,
                type = 'str'
            ),
            name = dict(
                required = True,
                type = 'str',
                aliases  = [ 'device' ]
            ),
            host = dict(
                required = True,
                type = 'str'
            ),
            port = dict(
                required = True,
                type = 'int'
            ),
            aetitle = dict(
                required = True,
                type = 'str'
            ),
            state = dict(
                required = True,
                type = 'str',
                choices  = [ 'present', 'absent' ]
            ),
        ),
        supports_check_mode = False
    )

    name  = module.params['name']
    host  = module.params['host']
    port  = module.params['port']
    aetitle  = module.params['aetitle']
    state = module.params['state']
    api_url = module.params['api_url']

    api = DeviceAPI(api_url, name)
    expected_device = Device(name, host, port, aetitle)
    changed = False

    if state == 'present':
        actual_device = api.read()
        if not actual_device:
            changed = api.create(expected_device)
        elif actual_device != expected_device:
            changed = api.update(expected_device)
        else:
            changed = False
    elif state == 'absent':
        changed = api.delete()

    module.exit_json(name=name, state=state, changed=changed) 


# import module snippets
from ansible.module_utils.basic import *
main()
