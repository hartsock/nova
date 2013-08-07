# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2013 Canonical Ltd.
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
"""
The VMware API disk operation utility methods.
"""


def extend_disk(session, name, instance, dc_ref, size, eagerZero=False):
    """Extend disk size to instance flavor size."""
    service_content = session._get_vim()._service_content
    vmdk_extend_task = session._call_method(
        session._get_vim(),
        "ExtendVirtualDisk_Task",
        service_content.virtualDiskManager,
        name=name,
        datacenter=dc_ref,
        newCapacityKb=size,
        eagerZero=eagerZero)
    session._wait_for_task(instance['uuid'], vmdk_extend_task)


def create_virtual_disk(session, dc_ref, disk_create_spec,
                                 instance, uploaded_disk_path):
    """Create a virtual disk of the size of flat vmdk file."""
    service_content = session._get_vim()._service_content
    vmdk_create_task = session._call_method(
        session._get_vim(),
        "CreateVirtualDisk_Task",
        service_content.virtualDiskManager,
        name=uploaded_disk_path,
        datacenter=dc_ref,
        spec=disk_create_spec)
    session._wait_for_task(instance['uuid'], vmdk_create_task)


def copy_disk(session, sourceName, dc_ref, destName, instance,
                                             disk_copy_spec):
    service_content = session._get_vim()._service_content
    vmdk_copy_task = session._call_method(
        session._get_vim(),
        "CopyVirtualDisk_Task",
        service_content.virtualDiskManager,
        sourceName=sourceName,
        sourceDatacenter=dc_ref,
        destName=destName,
        destSpec=disk_copy_spec)
    session._wait_for_task(instance['uuid'], vmdk_copy_task)
