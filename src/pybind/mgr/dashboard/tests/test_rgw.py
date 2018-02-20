# -*- coding: utf-8 -*-
from __future__ import absolute_import

from .helper import ControllerTestCase, authenticate


class RgwControllerTest(ControllerTestCase):

    @authenticate
    def test_rgw_daemon_list(self):
        data = self._get('/api/rgw/daemon')
        self.assertStatus(200)

        self.assertEqual(len(data), 1)
        data = data[0]
        self.assertIn('id', data)
        self.assertIn('version', data)
        self.assertIn('server_hostname', data)
        self.assertIn('service', data)
        self.assertIn('server', data)
        self.assertIn('metadata', data)
        self.assertIn('status', data)
        self.assertIn('url', data)
        self.assertIn('zone_name', data['metadata'])
        self.assertEqual('rgw', data['service']['type'])
        self.assertEqual('/api/rgw/daemon/{}'.format(data['id']), data['url'])

    @authenticate
    def test_rgw_daemon_get(self):
        data = self._get('/api/rgw/daemon')
        self.assertStatus(200)
        data = self._get(data[0]['url'])
        self.assertStatus(200)

        self.assertIn('rgw_metadata', data)
        self.assertIn('rgw_id', data)
        self.assertIn('rgw_status', data)
        self.assertTrue(data['rgw_metadata'])
