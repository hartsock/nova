# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2013 VMware, Inc.
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
A VMware API utility module for vCenter inventory.
"""

#NOTE: only for utilities specifically for dealing with vCenter inventories

def get_datacenter_obj_for_a_host_ref(vim, host_ref):
    """ Get the one and only datacenter for a host.

    DataCenter objects only exist in vCenter, the naked ESXi host
    has no equivalent construct. So you should only use this
    algorithm when you *know* you are talking to a vCenter. Using
    it in another context will produce non-recoverable faults.

    This code uses a Traversal Spec to walk the inventory hierarchy
    no matter how tall, wide, or deep and find the appropriate
    datacenter object for the supplied host, no matter how many
    levels of indirection are between the host and the datacenter.

    :param vim: the VIM object for connection to vCenter
    :param host_ref: the host reference to research
    :return: the DataCenter object containing the host
    """
    client_factory = vim.client.factory

    folder_select_spec = client_factory.create('ns0:SelectionSpec')
    folder_select_spec.name = "VisitFolders"

    visit_folders_ts = client_factory.create('ns0:TraversalSpec')
    visit_folders_ts.type = 'Folder'
    visit_folders_ts.path = 'parent'
    visit_folders_ts.skip = False
    visit_folders_ts.name = "VisitFolders"
    visit_folders_ts.selectSet = [folder_select_spec]

    # Compute Resource (or CCR) to Folder
    cr_to_folder_ts = client_factory.create('ns0:TraversalSpec')
    cr_to_folder_ts.type = 'ComputeResource'
    cr_to_folder_ts.path = 'parent'
    cr_to_folder_ts.skip = False
    cr_to_folder_ts.name = 'crToFolder'
    cr_to_folder_ts.selectSet = [folder_select_spec]

    # Host to CR (or CCR)
    h_to_cr_ts = client_factory.create('ns0:TraversalSpec')
    h_to_cr_ts.skip = False
    h_to_cr_ts.type = 'HostSystem'
    h_to_cr_ts.path = 'parent'
    h_to_cr_ts.name = 'hToCr'
    h_to_cr_ts.selectSet = [cr_to_folder_ts]

    traversal_specs = [h_to_cr_ts, visit_folders_ts]

    prop_spec = client_factory.create('ns0:PropertySpec')
    prop_spec.all = False
    prop_spec.type = 'Datacenter'
    prop_spec.pathSet = ['name']

    object_spec = client_factory.create('ns0:ObjectSpec')
    object_spec.obj = host_ref
    object_spec.skip = True
    object_spec.selectSet = traversal_specs

    property_filter_spec = client_factory.create('ns0:PropertyFilterSpec')
    property_filter_spec.propSet = [prop_spec]
    property_filter_spec.objectSet = [object_spec]

    property_filter_specs = [property_filter_spec]

    property_collector = vim.get_service_content().propertyCollector

    retrieve_options = client_factory.create('ns0:RetrieveOptions')
    retrieve_options.maxObjects = 1

    result = vim.RetrievePropertiesEx(
        property_collector,
        specSet=property_filter_specs,
        options=retrieve_options)

    if not result:
        raise RuntimeError("Host %s has no datacenter." % (host_ref.value))
        return None

    # logically there will only be 1 datacenter
    # see docs for vmodl.query.PropertyCollector.RetrieveResult
    datacenter = result.objects[0]

    # always cancel the any retrieve you don't advance to its end
    if hasattr(result, 'token') and result.token is not None:
        vim.CancelRetrievePropertiesEx(property_collector, result.token)

    return datacenter
