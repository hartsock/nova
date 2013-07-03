# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2013 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from nova.network import model as network_model
from nova import test
from nova.virt.vmwareapi import vmops


class VMwareVMOpsTestCase(test.TestCase):
    def setUp(self):
        super(VMwareVMOpsTestCase, self).setUp()
        subnet_4 = network_model.Subnet(cidr='192.168.0.1/24',
                                        dns=[network_model.IP('192.168.0.1')],
                                        gateway=
                                            network_model.IP('192.168.0.1'),
                                        ips=[
                                            network_model.IP('192.168.0.100')],
                                        routes=None)
        subnet_6 = network_model.Subnet(cidr='dead:beef::1/64',
                                        dns=None,
                                        gateway=
                                            network_model.IP('dead:beef::1'),
                                        ips=[network_model.IP(
                                            'dead:beef::dcad:beff:feef:0')],
                                        routes=None)
        network = network_model.Network(id=0,
                                        bridge='fa0',
                                        label='fake',
                                        subnets=[subnet_4, subnet_6],
                                        vlan=None,
                                        bridge_interface=None,
                                        injected=True)
        self.network_info = network_model.NetworkInfo([
                network_model.VIF(id=None,
                                  address='DE:AD:BE:EF:00:00',
                                  network=network,
                                  type=None,
                                  devname=None,
                                  ovs_interfaceid=None,
                                  rxtx_cap=3)
                ])

    def test_get_machine_id_str(self):
        result = vmops.VMwareVMOps._get_machine_id_str(self.network_info)
        self.assertEqual(result,
                         'DE:AD:BE:EF:00:00;192.168.0.100;255.255.255.0;'
                         '192.168.0.1;192.168.0.255;192.168.0.1#')

    def test_parse_metadata_from_instance_with_linked_clone_setting(self):
        # an example of some metadata collected from the CLI
        metadata_good = [{
            'instance_uuid': 'a9c99d21-bbd3-4ef4-abab-d439efe183cf',
            'deleted': 0, 'created_at': '2013-07-01T00:00:00.000000',
            'updated_at': None, 'value': 'True',
            'key': 'linked_clone', 'deleted_at': None, 'id': 123}]
        # a dummy instance, we only care about metadata
        instance = {'metadata': metadata_good}
        # pull the raw value from the metadata,
        # we don't care about type conversion yet.
        # validate that the value is not overriden by the default
        value = vmops.VMwareVMOps.get_instance_metadata_value(
                                            instance, 'linked_clone', False)
        self.assertEqual('True', value)
        # validate that the default value doesn't break on "None"
        value = vmops.VMwareVMOps.get_instance_metadata_value(
                                            instance, 'linked_clone', None)
        self.assertEqual('True', value)

    def test_parse_metadata_from_instance_without_linked_clone_setting(self):
        # here's some metadata that doesn't
        # have the value we're looking for...
        metadata_bad = [{
            'instance_uuid': 'a9c99d21-bbd3-4ef4-abab-d439efe183cf',
            'deleted': 0, 'created_at': '2013-07-01T00:00:00.000000',
            'updated_at': None, 'value': 'True',
            'key': 'something_else', 'deleted_at': None, 'id': 123}]
        instance = {'metadata': metadata_bad}
        # validate that the default instance shows through properly
        value = vmops.VMwareVMOps.get_instance_metadata_value(
                                    instance, 'linked_clone', 'False')
        self.assertEqual('False', value)
        # validate that 'None' shows through properly
        value = vmops.VMwareVMOps.get_instance_metadata_value(
                                    instance, 'linked_clone', None)
        self.assertEqual(None, value)
        # validate that a 'True' value shows through properly
        value = vmops.VMwareVMOps.get_instance_metadata_value(
                                    instance, 'linked_clone', 'True')
        self.assertEqual('True', value)

    def test_parse_metadata_from_instance_without_any_metadata(self):
        instance = {'metadata': []}
        # validate that an empty metadata list doesn't break things
        value = vmops.VMwareVMOps.get_instance_metadata_value(
                                    instance, 'linked_clone', 'False')
        self.assertEqual('False', value)
        value = vmops.VMwareVMOps.get_instance_metadata_value(
                                        instance, 'linked_clone', None)
        self.assertEqual(None, value)

    def test_get_instance_metadata_value_with_malformed_instance(self):
        instance = {'metadata': None}
        # validate that a malformed instance doesn't break things
        value = vmops.VMwareVMOps.get_instance_metadata_value(instance,
                                                              'linked_clone',
                                                              'False')
        self.assertEqual('False', value)

        # validate that a *really* malformed instance doesn't break things
        value = vmops.VMwareVMOps.get_instance_metadata_value(None,
                                                              'linked_clone',
                                                              'False')
        self.assertEqual('False', value)
