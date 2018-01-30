# -*- coding: utf-8 -*-
from __future__ import absolute_import

import time
import sys

import bcrypt
import cherrypy

from ..tools import ApiController, RESTController


@ApiController('auth')
class Auth(RESTController):
    """
    Provide login and logout actions.

    Supported config-keys:

      | KEY             | DEFAULT | DESCR                                     |
      ------------------------------------------------------------------------|
      | username        | None    | Username                                  |
      | password        | None    | Password encrypted using bcrypt           |
      | session-expire  | 1200    | Session will expire after <expires>       |
      |                           | seconds without activity                  |
    """

    SESSION_KEY = '_username'
    SESSION_KEY_TS = '_username_ts'

    DEFAULT_SESSION_EXPIRE = 1200.0

    @RESTController.args_from_json
    def create(self, username, password):
        now = time.time()
        config_username = self.mgr.get_localized_config('username', None)
        config_password = self.mgr.get_localized_config('password', None)
        hash_password = Auth.password_hash(password,
                                           config_password)
        if username == config_username and hash_password == config_password:
            cherrypy.session.regenerate()
            cherrypy.session[Auth.SESSION_KEY] = username
            cherrypy.session[Auth.SESSION_KEY_TS] = now
            self.logger.debug('Login successful')
            return {'username': username}

        cherrypy.response.status = 403
        self.logger.debug('Login failed')
        return {'detail': 'Invalid credentials'}

    def bulk_delete(self):
        self.logger.debug('Logout successful')
        cherrypy.session[Auth.SESSION_KEY] = None
        cherrypy.session[Auth.SESSION_KEY_TS] = None

    @staticmethod
    def password_hash(password, salt_password=None):
        if not salt_password:
            salt_password = bcrypt.gensalt()
        if sys.version_info > (3, 0):
            return bcrypt.hashpw(password, salt_password)
        return bcrypt.hashpw(password.encode('utf8'), salt_password)

    @staticmethod
    def check_auth():
        username = cherrypy.session.get(Auth.SESSION_KEY)
        if not username:
            Auth.logger.debug('Unauthorized access to {}'.format(cherrypy.url(
                relative='server')))
            raise cherrypy.HTTPError(401, 'You are not authorized to access '
                                          'that resource')
        now = time.time()
        expires = float(Auth.mgr.get_localized_config(
            'session-expire', Auth.DEFAULT_SESSION_EXPIRE))
        if expires > 0:
            username_ts = cherrypy.session.get(Auth.SESSION_KEY_TS, None)
            if username_ts and float(username_ts) < (now - expires):
                cherrypy.session[Auth.SESSION_KEY] = None
                cherrypy.session[Auth.SESSION_KEY_TS] = None
                Auth.logger.debug('Session expired')
                raise cherrypy.HTTPError(401,
                                         'Session expired. You are not '
                                         'authorized to access that resource')
        cherrypy.session[Auth.SESSION_KEY_TS] = now

    @staticmethod
    def set_login_credentials(username, password):
        Auth.mgr.set_localized_config('username', username)
        hashed_passwd = Auth.password_hash(password)
        Auth.mgr.set_localized_config('password', hashed_passwd)