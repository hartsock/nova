# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 IBM Corp.
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

from oslo.config import cfg
import webob.exc

from nova.api.openstack import extensions
from nova.api.openstack import wsgi
from nova.api.openstack import xmlutil
from nova import compute
from nova import exception
from nova.openstack.common.gettextutils import _
from nova import servicegroup
from nova import utils

ALIAS = "os-services"
authorize = extensions.extension_authorizer('compute', 'v3:' + ALIAS)
CONF = cfg.CONF
CONF.import_opt('service_down_time', 'nova.service')


class ServicesIndexTemplate(xmlutil.TemplateBuilder):
    def construct(self):
        root = xmlutil.TemplateElement('services')
        elem = xmlutil.SubTemplateElement(root, 'service', selector='services')
        elem.set('binary')
        elem.set('host')
        elem.set('zone')
        elem.set('status')
        elem.set('state')
        elem.set('updated_at')
        elem.set('disabled_reason')

        return xmlutil.MasterTemplate(root, 1)


class ServiceUpdateTemplate(xmlutil.TemplateBuilder):
    def construct(self):
        root = xmlutil.TemplateElement('service', selector='service')
        root.set('host')
        root.set('binary')
        root.set('status')
        root.set('disabled_reason')

        return xmlutil.MasterTemplate(root, 1)


class ServiceController(object):

    def __init__(self):
        self.host_api = compute.HostAPI()
        self.servicegroup_api = servicegroup.API()

    def _get_services(self, req):
        context = req.environ['nova.context']
        authorize(context)
        services = self.host_api.service_get_all(
            context, set_zones=True)

        host = ''
        if 'host' in req.GET:
            host = req.GET['host']
        binary = ''
        if 'binary' in req.GET:
            binary = req.GET['binary']
        if host:
            services = [s for s in services if s['host'] == host]
        if binary:
            services = [s for s in services if s['binary'] == binary]

        return services

    def _get_service_detail(self, svc):
        alive = self.servicegroup_api.service_is_up(svc)
        state = (alive and "up") or "down"
        active = 'enabled'
        if svc['disabled']:
            active = 'disabled'
        service_detail = {'binary': svc['binary'], 'host': svc['host'],
                     'zone': svc['availability_zone'],
                     'status': active, 'state': state,
                     'updated_at': svc['updated_at'],
                     'disabled_reason': svc['disabled_reason']}

        return service_detail

    def _get_services_list(self, req):
        services = self._get_services(req)
        svcs = []
        for svc in services:
            svcs.append(self._get_service_detail(svc))

        return svcs

    def _is_valid_as_reason(self, reason):
        try:
            utils.check_string_length(reason.strip(), 'Disabled reason',
                                      min_length=1, max_length=255)
        except exception.InvalidInput:
            return False

        return True

    @extensions.expected_errors(())
    @wsgi.serializers(xml=ServicesIndexTemplate)
    def index(self, req):
        """
        Return a list of all running services. Filter by host & service name.
        """
        services = self._get_services_list(req)

        return {'services': services}

    @extensions.expected_errors((400, 404))
    @wsgi.serializers(xml=ServiceUpdateTemplate)
    def update(self, req, id, body):
        """Enable/Disable scheduling for a service."""
        context = req.environ['nova.context']
        authorize(context)

        if id == "enable":
            disabled = False
            status = "enabled"
        elif id in ("disable", "disable-log-reason"):
            disabled = True
            status = "disabled"
        else:
            raise webob.exc.HTTPNotFound("Unknown action")
        try:
            host = body['service']['host']
            binary = body['service']['binary']
            ret_value = {
                'service': {
                    'host': host,
                    'binary': binary,
                    'status': status,
                },
            }
            status_detail = {'disabled': disabled}
            if id == "disable-log-reason":
                reason = body['service']['disabled_reason']
                if not self._is_valid_as_reason(reason):
                    msg = _('Disabled reason contains invalid characters '
                            'or is too long')
                    raise webob.exc.HTTPBadRequest(detail=msg)

                status_detail['disabled_reason'] = reason
                ret_value['service']['disabled_reason'] = reason
        except (TypeError, KeyError):
            msg = _('Invalid attribute in the request')
            if 'host' in body and 'binary' in body:
                msg = _('Missing disabled reason field')
            raise webob.exc.HTTPBadRequest(detail=msg)

        try:
            self.host_api.service_update(context, host, binary, status_detail)
        except exception.ServiceNotFound as e:
            raise webob.exc.HTTPNotFound(explanation=e.format_message())

        return ret_value


class Services(extensions.V3APIExtensionBase):
    """Services support."""

    name = "Services"
    alias = ALIAS
    namespace = "http://docs.openstack.org/compute/ext/services/api/v3"
    version = 1

    def get_resources(self):
        resources = [extensions.ResourceExtension(ALIAS,
                                               ServiceController())]
        return resources

    def get_controller_extensions(self):
        return []
