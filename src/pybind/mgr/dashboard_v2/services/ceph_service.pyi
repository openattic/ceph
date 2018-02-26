# -*- coding: utf-8 -*-
from __future__ import absolute_import

from ..module import Module


class CephServiceMixin(object):
    mgr = ... # type: Module

class CephPoolMixin(object):
    mgr = ... # type: Module

class CephDaemonMixin(object):
    mgr = ... # type: Module
