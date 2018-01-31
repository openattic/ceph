# -*- coding: utf-8 -*-
# pylint: disable=W0212
from __future__ import absolute_import

import json

from cherrypy.test import helper
from more_itertools import always_iterable

from ..module import Module


class RequestHelper(object):
    def _request(self, url, method, data=None):
        if not data:
            b = None
            h = None
        else:
            b = json.dumps(data)
            h = [('Content-Type', 'application/json'),
                 ('Content-Length', str(len(b)))]
        self.getPage(url, method=method, body=b, headers=h)

    def _get(self, url):
        self._request(url, 'GET')

    def _post(self, url, data=None):
        self._request(url, 'POST', data)

    def _delete(self, url, data=None):
        self._request(url, 'DELETE', data)

    def _put(self, url, data=None):
        self._request(url, 'PUT', data)

    def assertJsonBody(self, data, msg=None):
        """Fail if value != self.body."""
        body_str = self.body.decode('utf-8') if isinstance(self.body, bytes) else self.body
        json_body = json.loads(body_str)
        if data != json_body:
            if msg is None:
                msg = 'expected body:\n%r\n\nactual body:\n%r' % (
                    data, json_body)
            self._handlewebError(msg)


class ControllerTestCase(helper.CPWebCase, RequestHelper):
    @classmethod
    def setup_server(cls):
        module = Module('dashboard', None, None)
        cls._mgr_module = module
        module.configure_module(True)
        cls.setup_test()

    @classmethod
    def setup_test(cls):
        pass