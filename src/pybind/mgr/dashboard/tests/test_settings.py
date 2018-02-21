# -*- coding: utf-8 -*-
from __future__ import absolute_import

from .helper import ControllerTestCase


class SettingsTest(ControllerTestCase):
    def setUp(self):
        val = self._ceph_cmd(['dashboard', 'get-grafana-api-port'])
        if val != '3000':
            self._ceph_cmd(['dashboard', 'set-grafana-api-port', '3000'])

    def test_get_setting(self):
        val = self._ceph_cmd(['dashboard', 'get-grafana-api-port'])
        self.assertEqual(val, '3000')

    def test_set_setting(self):
        self._ceph_cmd(['dashboard', 'set-grafana-api-port', '4000'])
        val = self._ceph_cmd(['dashboard', 'get-grafana-api-port'])
        self.assertEqual(val, '4000')
