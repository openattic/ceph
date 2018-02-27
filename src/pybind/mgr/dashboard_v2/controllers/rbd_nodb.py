from functools import partial

from .cluster import nodb_serializer
from ..models.nodb import nodb_context
from ..tools import ApiController, RESTController
from .. import logger

has_rbd = True
try:
    from ..models.rbd import CephRbd
except ImportError:
    logger.exception('failed to import rbd')
    has_rbd = False

if has_rbd:
    cluster_serializer = partial(nodb_serializer, CephRbd)

    @ApiController('rbdnodb')
    class RbdNodb(RESTController):

        def list(self):
            with nodb_context(self):
                return map(cluster_serializer, CephRbd.objects.all())

        def get(self, _):
            with nodb_context(self):
                return cluster_serializer(CephRbd.objects.get())
