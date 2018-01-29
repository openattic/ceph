from functools import partial

from ..models.nodb import nodb_context
from ..models.cluster import CephCluster
from ..tools import ApiController, RESTController


def nodb_serializer(model, obj):
    # pylint: disable=W0212
    return {field.attname: getattr(obj, field.attname) for field in model._meta.fields}


cluster_serializer = partial(nodb_serializer, CephCluster)


@ApiController('cluster')
class Cluster(RESTController):

    def list(self):
        with nodb_context(self):
            map(cluster_serializer, CephCluster.objects.all())

    def get(self, _):
        with nodb_context(self):
            return cluster_serializer(CephCluster.objects.get())
