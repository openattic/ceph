from __future__ import absolute_import

import json

import cherrypy
from cherrypy.lib.sessions import RamSession
from cherrypy.test import helper
from mock import patch

from ..tools import RESTController


class FooResource(RESTController):
    elems = []

    def list(self, *vpath, **params):
        return FooResource.elems

    def create(self, data, *args, **kwargs):
        FooResource.elems.append(data)
        return data

    def get(self, key, *args, **kwargs):
        return FooResource.elems[int(key)]

    def delete(self, key):
        del FooResource.elems[int(key)]

    def bulk_delete(self):
        FooResource.elems = []


class Root(object):
    foo = FooResource()

class RESTControllerTest(helper.CPWebCase):
    @staticmethod
    def setup_server():
        cherrypy.tree.mount(Root())

    def test_empty(self):
        self.getPage("/foo", method='DELETE')
        self.assertStatus(204)
        self.getPage("/foo")
        self.assertStatus('200 OK')
        self.assertHeader('Content-Type', 'application/json')
        self.assertBody('[]')

    def test_fill(self):
        sess_mock = RamSession()
        with patch('cherrypy.session', sess_mock, create=True):
            body = json.dumps({'a': 'b'})
            for _ in range(5):

                self.getPage("/foo", method='POST', body=body, headers=[
                    ('Content-Type', 'application/json'),
                    ('Content-Length', str(len(body)))
                ])
                self.assertBody(body)
                self.assertStatus(201)
                self.assertHeader('Content-Type', 'application/json')

            self.getPage("/foo")
            self.assertStatus('200 OK')
            self.assertHeader('Content-Type', 'application/json')
            self.assertBody(json.dumps([{'a': 'b'}] * 5))
