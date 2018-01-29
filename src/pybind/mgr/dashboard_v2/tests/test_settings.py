# -*- coding: utf-8 -*-
from __future__ import absolute_import

import errno
import unittest

from ..module import Module
from ..settings import Settings


class SettingsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        module = Module('dashboard', None, None)
        module.configure_module(True)
        cls.module = module

    def setUp(self):
        if Settings.GRAFANA_API_HOST != 'localhost':
            Settings.GRAFANA_API_HOST = 'localhost'
        if Settings.GRAFANA_API_PORT != 3000:
            Settings.GRAFANA_API_PORT = 3000

    def test_get_setting(self):
        self.assertEqual(Settings.GRAFANA_API_HOST, 'localhost')

    def test_set_setting(self):
        Settings.GRAFANA_API_HOST = 'grafanahost'
        self.assertEqual(Settings.GRAFANA_API_HOST, 'grafanahost')

    def test_get_cmd(self):
        r, out, err = self.module.handle_command(
                {'prefix': 'dashboard get-grafana-api-port'})
        self.assertEqual(r, 0)
        self.assertEqual(out, '3000')
        self.assertEqual(err, '')

    def test_set_cmd(self):
        r, out, err = self.module.handle_command(
                {'prefix': 'dashboard set-grafana-api-port',
                 'value': '4000'})
        self.assertEqual(r, 0)
        self.assertEqual(out, 'Option GRAFANA_API_PORT updated')
        self.assertEqual(err, '')

    def test_inv_cmd(self):
        r, out, err = self.module.handle_command(
                {'prefix': 'dashboard get-non-existent-option'})
        self.assertEqual(r, -errno.EINVAL)
        self.assertEqual(out, '')
        self.assertEqual(err, "Command not found "
                              "'dashboard get-non-existent-option'")

    def test_sync(self):
        Settings.GRAFANA_API_PORT = 5000
        r, out, err = self.module.handle_command(
                {'prefix': 'dashboard get-grafana-api-port'})
        self.assertEqual(r, 0)
        self.assertEqual(out, '5000')
        self.assertEqual(err, '')
        r, out, err = self.module.handle_command(
                {'prefix': 'dashboard set-grafana-api-host',
                 'value': 'new-local-host'})
        self.assertEqual(r, 0)
        self.assertEqual(out, 'Option GRAFANA_API_HOST updated')
        self.assertEqual(err, '')
        self.assertEqual(Settings.GRAFANA_API_HOST, 'new-local-host')
