from functools import partial

from ..models.nodb import nodb_context, nodb_serializer
from ..models.pool import CephPool
from ..tools import ApiController, RESTController


pool_serializer = partial(nodb_serializer, CephPool)


@ApiController('pool')
class Pool(RESTController):
    """Represents the pool API endpoint."""

    def list(self):
        with nodb_context(self):
            return map(pool_serializer, CephPool.objects.all())
