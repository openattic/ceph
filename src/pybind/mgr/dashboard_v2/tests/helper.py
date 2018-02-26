# -*- coding: utf-8 -*-
# pylint: disable=W0212
from __future__ import absolute_import

import os
import subprocess
import unittest

import requests

from .. import logger


def authenticate(func):
    def decorate(self, *args, **kwargs):
        self._ceph_cmd(['dashboard', 'set-login-credentials', 'admin', 'admin'])
        self._post('/api/auth', {'username': 'admin', 'password': 'admin'})
        self.assertStatus(201)
        return func(self, *args, **kwargs)
    return decorate


class ControllerTestCase(unittest.TestCase):
    DASHBOARD_HOST = os.environ.get('DASHBOARD_V2_HOST', "localhost")
    DASHBOARD_PORT = os.environ.get('DASHBOARD_V2_PORT', 8080)

    def __init__(self, *args, **kwargs):
        self.dashboard_host = kwargs.pop('dashboard_host') \
            if 'dashboard_host' in kwargs else self.DASHBOARD_HOST
        self.dashboard_port = kwargs.pop('dashboard_port') \
            if 'dashboard_port' in kwargs else self.DASHBOARD_PORT
        super(ControllerTestCase, self).__init__(*args, **kwargs)
        self._session = requests.Session()
        self._resp = None

    def _request(self, url, method, data=None):
        url = "http://{}:{}{}".format(self.dashboard_host, self.dashboard_port,
                                      url)
        if method == 'GET':
            self._resp = self._session.get(url)
            return self._resp.json()
        elif method == 'POST':
            self._resp = self._session.post(url, json=data)
        elif method == 'DELETE':
            self._resp = self._session.delete(url, json=data)
        elif method == 'PUT':
            self._resp = self._session.put(url, json=data)
        return None

    def _get(self, url):
        return self._request(url, 'GET')

    def _post(self, url, data=None):
        self._request(url, 'POST', data)

    def _delete(self, url, data=None):
        self._request(url, 'DELETE', data)

    def _put(self, url, data=None):
        self._request(url, 'PUT', data)

    def cookies(self):
        return self._resp.cookies

    def jsonBody(self):
        return self._resp.json()

    def reset_session(self):
        self._session = requests.Session()

    def assertJsonBody(self, data):
        body = self._resp.json()
        self.assertEqual(body, data)

    def assertBody(self, body):
        self.assertEqual(self._resp.text, body)

    def assertStatus(self, status):
        self.assertEqual(self._resp.status_code, status)

    @classmethod
    def _cmd(cls, cmd, ignore_exit_status=False):
        logger.info('running %s', cmd)
        try:
            res = subprocess.check_output(cmd)
            return res.decode('utf-8').strip()
        except subprocess.CalledProcessError as e:
            if not ignore_exit_status:
                logger.error('Status : FAIL\nreturncode=%s\noutput=%s', e.returncode, e.output)
                raise
            return None

    @classmethod
    def _ceph_cmd(cls, cmd, ignore_exit_status=False):
        _cmd = ['ceph']
        _cmd.extend(cmd)
        return cls._cmd(_cmd, ignore_exit_status)

    @classmethod
    def set_config_key(cls, key, value):
        cls._ceph_cmd(['config-key', 'set', key, value])

    @classmethod
    def get_config_key(cls, key):
        return cls._ceph_cmd(['config-key', 'get', key])

    # pylint: disable=anomalous-backslash-in-string
    @classmethod
    def _run_multiple_cmds(cls, cmds):
        """
        :param cmds: list of commands.
            * newline divided
            * space at line start is ignored
            * ^\s*# = line ignored
            * ^\s*! = exit status ignored.
        """
        for cmd in cmds.splitlines():
            cmd = cmd.strip()
            if cmd and not cmd.startswith('#'):
                if cmd.startswith('!'):
                    cls._cmd(cmd[1:].split(' '), ignore_exit_status=True)
                else:
                    cls._cmd(cmd.split(' '))

    @classmethod
    def _rbd_cmd(cls, cmd):
        _cmd = ['rbd']
        _cmd.extend(cmd)
        return cls._cmd(_cmd)
