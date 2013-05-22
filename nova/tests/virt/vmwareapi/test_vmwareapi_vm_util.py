# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2013 Hewlett-Packard Development Company, L.P.
# Copyright 2013 Canonical Corp.
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

from collections import namedtuple

from nova import exception
from nova import test
from nova.virt.vmwareapi import fake
from nova.virt.vmwareapi import vm_util


class fake_session(object):
    def __init__(self, ret=None):
        self.ret = ret

    def _call_method(self, *args):
        return self.ret


class VMwareVMUtilTestCase(test.TestCase):
    def setUp(self):
        super(VMwareVMUtilTestCase, self).setUp()
        fake.reset()

    def tearDown(self):
        super(VMwareVMUtilTestCase, self).tearDown()
        fake.reset()

    def test_get_datastore_ref_and_name(self):
        result = vm_util.get_datastore_ref_and_name(
            fake_session([fake.Datastore()]))

        self.assertEquals(result[1], "fake-ds")
        self.assertEquals(result[2], 1024 * 1024 * 1024 * 1024)
        self.assertEquals(result[3], 1024 * 1024 * 500 * 1024)

    def test_get_datastore_ref_and_name_with_regex(self):
        # Test with a regex that matches with a datastore
        datastore_valid_regex = re.compile("^openstack.*\d$")
        result = vm_util.get_datastore_ref_and_name(
            fake_session([fake.Datastore("openstack-ds0"),
                          fake.Datastore("fake-ds0"),
                          fake.Datastore("fake-ds1")]),
            None, None, datastore_valid_regex)
        self.assertEquals("openstack-ds0", result[1])

    def test_get_datastore_ref_and_name_with_list(self):
        # Test with a regex containing whitelist of datastores
        datastore_valid_regex = re.compile("(openstack-ds0|openstack-ds2)")
        result = vm_util.get_datastore_ref_and_name(
            fake_session([fake.Datastore("openstack-ds0"),
                          fake.Datastore("openstack-ds1"),
                          fake.Datastore("openstack-ds2")]),
            None, None, datastore_valid_regex)
        self.assertNotEquals("openstack-ds1", result[1])

    def test_get_datastore_ref_and_name_with_regex_error(self):
        # Test with a regex that has no match
        datastore_invalid_regex = re.compile("unknown-ds")
        exp_message = _("Datastore regex %s did not match any datastores") \
                        % datastore_invalid_regex.pattern
        try:
            vm_util.get_datastore_ref_and_name(
                fake_session([fake.Datastore("fake-ds0"),
                fake.Datastore("fake-ds1")]),
                None, None, datastore_invalid_regex)
        except exception.DatastoreNotFound as e:
            self.assertEqual(exp_message, e.args[0])
        else:
            self.fail("DatastoreNotFound Exception was not raised with "
                      "message: %s" % exp_message)

    def test_get_datastore_ref_and_name_without_datastore(self):

        self.assertRaises(exception.DatastoreNotFound,
                vm_util.get_datastore_ref_and_name,
                fake_session(), host="fake-host")

        self.assertRaises(exception.DatastoreNotFound,
                vm_util.get_datastore_ref_and_name,
                fake_session(), cluster="fake-cluster")

    def test_get_host_ref_from_id(self):

        fake_host_sys = fake.HostSystem(
            fake.ManagedObjectReference("HostSystem", "host-123"))

        fake_host_id = fake_host_sys.obj.value
        fake_host_name = "ha-host"

        ref = vm_util.get_host_ref_from_id(
            fake_session([fake_host_sys]), fake_host_id, ['name'])

        self.assertIsInstance(ref, fake.HostSystem)
        self.assertEqual(fake_host_id, ref.obj.value)

        host_name = vm_util.get_host_name_from_host_ref(ref)

        self.assertEquals(fake_host_name, host_name)

    def test_get_host_name_for_vm(self):

        fake_vm = fake.ManagedObject(
            "VirtualMachine", fake.ManagedObjectReference(
                "vm-123", "VirtualMachine"))
        fake_vm.propSet.append(
            fake.Prop('name', 'vm-123'))

        vm_ref = vm_util.get_vm_ref_from_name(
                fake_session([fake_vm]), 'vm-123')

        self.assertIsNotNone(vm_ref)

        fake_results = [
            fake.ObjectContent(
                None, [
                    fake.Prop('runtime.host',
                              fake.ManagedObjectReference(
                                'host-123', 'HostSystem'))
                ])]

        host_id =\
            vm_util.get_host_id_from_vm_ref(
                fake_session(fake_results), vm_ref)

        self.assertEqual('host-123', host_id)

    def test_property_from_property_set(self):

        Property = namedtuple('Property', ['propSet'])
        Prop = namedtuple('Prop', ['name', 'val'])
        MoRef = namedtuple('Val', ['value'])

        properties_good = [
            Property(propSet=[Prop(name='name', val=MoRef(value='vm-123'))]),
            Property(propSet=[
                Prop(name='foo', val=MoRef(value='bar1')),
                Prop(name='runtime.host', val=MoRef(value='host-123')),
                Prop(name='foo', val=MoRef(value='bar2')),
            ]),
            Property(propSet=[
                Prop(name='something', val=MoRef(value='thing'))]), ]

        properties_bad = [
            Property(propSet=[
                Prop(name='name', val=MoRef(value='vm-123'))]),
            Property(propSet=[
                Prop(name='foo', val='bar1'),
                Prop(name='foo', val='bar2'), ]),
            Property(propSet=[
                Prop(name='something', val=MoRef(value='thing'))]), ]

        prop = vm_util.property_from_property_set(
                    'runtime.host', properties_good)
        self.assertIsNotNone(prop)
        value = prop.val.value
        self.assertEqual('host-123', value)

        prop2 = vm_util.property_from_property_set(
                    'runtime.host', properties_bad)
        self.assertIsNone(prop2)

        prop3 = vm_util.property_from_property_set('foo', properties_good)
        self.assertIsNotNone(prop3)
        val3 = prop3.val.value
        self.assertEqual('bar1', val3)

        prop4 = vm_util.property_from_property_set('foo', properties_bad)
        self.assertIsNotNone(prop4)
        self.assertEqual('bar1', prop4.val)
