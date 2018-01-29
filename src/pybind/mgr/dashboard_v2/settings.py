# -*- coding: utf-8 -*-
from __future__ import absolute_import

import errno
import inspect
from six import with_metaclass


class Options(object):
    """
    If you need to store some configuration value please add the config option
    name as a class attribute to this class.
    """
    # Grafana settings
    GRAFANA_API_HOST = ('localhost', str)
    GRAFANA_API_PORT = (3000, int)
    GRAFANA_API_USERNAME = ('admin', str)
    GRAFANA_API_PASSWORD = ('admin', str)
    GRAFANA_API_SCHEME = ('http', str)

    # RGW settings
    RGW_API_HOST = ('', str)
    RGW_API_PORT = (80, int)
    RGW_API_ACCESS_KEY = ('', str)
    RGW_API_SECRET_KEY = ('', str)
    RGW_API_ADMIN_RESOURCE = ('admin', str)
    RGW_API_USER_ID = ('', str)
    RGW_API_SCHEME = ('http', str)


class SettingsMeta(type):

    def __getattribute__(cls, attr):
        if not attr.startswith('_') and hasattr(Options, attr):
            default, stype = getattr(Options, attr)
            return stype(SettingsMeta.mgr.get_config(attr, default))
        return SettingsMeta.__dict__.get(attr, None)

    def __setattr__(cls, attr, value):
        if not attr.startswith('_') and hasattr(Options, attr):
            SettingsMeta.mgr.set_config(attr, str(value))
        else:
            setattr(SettingsMeta, attr, value)


# pylint: disable=no-init
class Settings(with_metaclass(SettingsMeta, object)):
    pass


def _options_command_map():
    def filter_attr(member):
        return not inspect.isroutine(member)

    cmd_map = {}
    for option, value in inspect.getmembers(Options, filter_attr):
        if option.startswith('_'):
            continue
        key_get = 'dashboard get-{}'.format(option.lower().replace('_', '-'))
        key_set = 'dashboard set-{}'.format(option.lower().replace('_', '-'))
        cmd_map[key_get] = {'name': option, 'type': None}
        cmd_map[key_set] = {'name': option, 'type': value[1]}
    return cmd_map


_OPTIONS_COMMAND_MAP = _options_command_map()


def options_command_list():
    """
    This function generates a list of ``get`` and ``set`` commands
    for each declared configuration option in class ``Options``.
    """
    def py2ceph(pytype):
        if pytype == str:
            return 'CephString'
        elif pytype == int:
            return 'CephInt'
        return 'CephString'

    cmd_list = []
    for cmd, opt in _OPTIONS_COMMAND_MAP.items():
        if not opt['type']:
            cmd_list.append({
                'cmd': '{}'.format(cmd),
                'desc': 'Get the {} option value'.format(opt['name']),
                'perm': 'r'
            })
        else:
            cmd_list.append({
                'cmd': '{} name=value,type={}'
                       .format(cmd, py2ceph(opt['type'])),
                'desc': 'Set the {} option value'.format(opt['name']),
                'perm': 'w'
            })

    return cmd_list


def handle_option_command(cmd):
    if cmd['prefix'] not in _OPTIONS_COMMAND_MAP:
        return (-errno.EINVAL, '', "Command not found '{}'"
                                   .format(cmd['prefix']))

    opt = _OPTIONS_COMMAND_MAP[cmd['prefix']]
    if not opt['type']:
        # get option
        return 0, str(getattr(Settings, opt['name'])), ''

    # set option
    setattr(Settings, opt['name'], opt['type'](cmd['value']))
    return 0, 'Option {} updated'.format(opt['name']), ''
