# -*- coding: utf-8 -*-
from __future__ import absolute_import

import json

from ..tools import ApiController, RESTController, AuthRequired
from .. import logger


@ApiController('rgw')
@AuthRequired()
class Rgw(RESTController):
    pass


@ApiController('rgw/daemon')
@AuthRequired()
class RgwDaemon(RESTController):

    def list(self):
        daemons = []
        for server in self.mgr.list_servers():
            for service in server['services']:
                if service['type'] == 'rgw':
                    metadata = self.mgr.get_metadata('rgw', service['id'])
                    status = self.mgr.get_daemon_status('rgw', service['id'])
                    if 'json' in status:
                        try:
                            status = json.loads(status['json'])
                        except ValueError:
                            logger.warning("%s had invalid status json", service['id'])
                            status = {}
                    else:
                        logger.warning('%s has no key "json" in status', service['id'])

                    # extract per-daemon service data and health
                    daemon = {
                        'id': service['id'],
                        'version': metadata['ceph_version'],
                        'server_hostname': server['hostname'],
                        'service': service,
                        'server': server,
                        'metadata': metadata,
                        'status': status,
                        'url': "{0}/api/rgw/daemon/{1}".format(
                            self.mgr.url_prefix, service['id'])
                    }

                    daemons.append(daemon)

        return sorted(daemons, key=lambda k: k['id'])

    def get(self, svc_id):
        daemon = {
            'rgw_metadata': [],
            'rgw_id': svc_id,
            'rgw_status': []
        }
        for server in self.mgr.list_servers():
            for service in server['services']:
                if service['type'] == 'rgw' and service['id'] == svc_id:
                    metadata = self.mgr.get_metadata('rgw', service['id'])
                    status = self.mgr.get_daemon_status('rgw', service['id'])
                    if 'json' in status:
                        try:
                            status = json.loads(status['json'])
                        except ValueError:
                            logger.warning("%s had invalid status json", service['id'])
                            status = {}
                    else:
                        logger.warning('%s has no key "json" in status', service['id'])

                    daemon['rgw_metadata'] = metadata
                    daemon['rgw_status'] = status

                    break
        return daemon