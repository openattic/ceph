# -*- coding: utf-8 -*-
from __future__ import absolute_import

import cherrypy

from ..tools import ApiController, AuthRequired, RESTController, BaseController


@ApiController('ping')
@AuthRequired()
class Ping(BaseController):
    @cherrypy.expose
    def default(self):
        return 'pong'


@ApiController('echo1')
class EchoArgs(RESTController):
    prefix = None

    def init(self):
        self.prefix = "ea"

    @RESTController.args_from_json
    def create(self, msg):
        return {'echo': "{}: {}".format(self.prefix, msg)}


@ApiController('echo2')
class Echo(RESTController):
    def create(self, data):
        return {'echo': data['msg']}
