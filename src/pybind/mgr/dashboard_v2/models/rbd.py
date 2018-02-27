from __future__ import absolute_import
import itertools

from contextlib import contextmanager
from six.moves import reduce
import mock

# If you see something like lib.2/rbd.so: undefined symbol: rbd_snap_get_timestamp
# Make sure, LD_LIBRARY_PATH is set correctly. E.g. ceph/build/lib
import rbd

from .send_command_api import logged, undoable
from .nodb import NodbModel, CharField, IntegerField, JsonField, BooleanField,\
    bulk_attribute_setter, NodbManager


# pylint: disable=W0613


# -------------
# FIXME
# while waiting for https://github.com/openattic/ceph/pull/55

CephPool = mock.Mock()
_instance = CephPool()
_instance.name = 'rbd'
_instance.id = 2
CephPool.objects.get.return_value = _instance
CephPool.objects.all.return_value = [_instance]

# -------------


class RbdApi(object):
    """
    http://docs.ceph.com/docs/master/rbd/librbdpy/

    Exported features are defined here:
       https://github.com/ceph/ceph/blob/master/src/tools/rbd/ArgumentTypes.cc
    """

    # FIXME: we have to make sure, we don't block the UI.
    RBD_DELETION_TIMEOUT = 3600

    @staticmethod
    def get_feature_mapping():
        ret = {
            getattr(rbd, feature): feature[12:].lower().replace('_', '-')
            for feature
            in dir(rbd)
            if feature.startswith('RBD_FEATURE_')
        }
        if not ret:
            # If this fails, make sure, PYTHONPATH is set to the rbd module. E.g.
            # PYTHONPATH=/ceph/build/lib/cython_modules/lib.2
            raise ImportError('Unable to find features')
        return ret

    @classmethod
    def bitmask_to_list(cls, features):
        """
        :type features: int
        :rtype: list[str]
        """
        return [
            cls.get_feature_mapping()[key]
            for key
            in cls.get_feature_mapping().keys()
            if key & features == key
        ]

    @classmethod
    def list_to_bitmask(cls, features):
        """
        :type features: list[str]
        :rtype: int
        """
        return reduce(lambda l, r: l | r,
                      [
                          list(cls.get_feature_mapping().keys())[
                              list(cls.get_feature_mapping().values()).index(value)]
                          for value
                          in cls.get_feature_mapping().values()
                          if value in features
                      ],
                      0)

    def __init__(self, cluster, pool_name):
        self.cluster = cluster
        self.rbd_inst = rbd.RBD()
        self.ioctx = cluster.open_ioctx(pool_name)
        self.ioctx.require_ioctx_open()

    # pylint: disable=R0913
    @logged
    @undoable
    def create(self, image_name, size, old_format=True, features=None,
               order=None, stripe_unit=None, stripe_count=None, data_pool_name=None):
        """
        .. example::
                >>> api = RbdApi()
                >>> api.create('mypool', 'myimage',  4 * 1024 ** 3) # 4 GiB
                >>> api.remove('mypool', 'myimage')

        :param features: see :method:`image_features`. The Linux kernel module doesn't support
            all features.
        :param order: obj_size will be 2**order
        :type features: list[str]
        :param old_format: Some features are not supported by the old format.
        :type stripe_unit: int
        :type stripe_count: int
        :type data_pool_name: str | None
        """
        default_features = 0 if old_format else 61  # FIXME: hardcoded int
        feature_bitmask = (RbdApi.list_to_bitmask(features) if features is not None else
                           default_features)
        self.rbd_inst.create(self.ioctx, image_name, size, old_format=old_format,
                             features=feature_bitmask, order=order,
                             stripe_unit=stripe_unit, stripe_count=stripe_count,
                             data_pool=data_pool_name)

        yield
        self.remove(image_name)

    def remove(self, image_name):
        self.rbd_inst.remove(self.ioctx, image_name)

    def list(self):
        """
        :returns: list -- a list of image names
        :rtype: list[str]
        """
        return self.rbd_inst.list(self.ioctx)


@contextmanager
def rbd_image(rbd_api, image_name, snapshot=None):
    """
    :type rbd_api: RbdApi
    :type image_name: str
    """
    # pylint: disable=I1101
    with rbd.Image(rbd_api.ioctx, name=image_name, snapshot=snapshot) as image:
        yield image


# pylint: disable=R0902
class CephRbd(NodbModel):
    id = CharField(primary_key=True, editable=False,
                   help_text='pool-name/image-name')
    name = CharField()
    pool = IntegerField()
    data_pool = IntegerField(null=True, blank=True)
    size = IntegerField(help_text='Bytes, where size modulo obj_size === 0',
                        default=4 * 1024 ** 3)
    obj_size = IntegerField(null=True, blank=True, help_text='obj_size === 2^n',
                            default=2 ** 22)
    num_objs = IntegerField(editable=False)
    block_name_prefix = CharField(editable=False)
    features = JsonField(base_type=list, null=True, blank=True, default=[],
                         help_text='For example: [{}]'.format(
                             ', '.join(['"{}"'.format(v) for v
                                        in RbdApi.get_feature_mapping().values()])))
    old_format = BooleanField(default=False, help_text='should always be false')
    used_size = IntegerField(editable=False)
    stripe_unit = IntegerField(blank=True, null=True)
    stripe_count = IntegerField(blank=True, null=True)

    @staticmethod
    def make_key(pool, image_name):
        """
        :type pool: CephPool
        :type image_name: str | unicode
        :rtype: unicode
        """
        return u'{}/{}'.format(pool.name, image_name)

    @staticmethod
    def get_all_objects(api_controller, query):
        def rbds(pool):
            for image_name in RbdApi(api_controller.mgr.rados, pool.name).list():
                yield dict(name=image_name,
                           pool=pool.id,
                           id=CephRbd.make_key(pool, image_name))

        rbds = itertools.chain.from_iterable([rbds(pool) for pool in CephPool.objects.all()])
        return [CephRbd(**CephRbd.make_model_args(rbd)) for rbd in rbds]

    @bulk_attribute_setter(['num_objs', 'obj_size', 'size', 'data_pool_id', 'features',
                            'old_format', 'block_name_prefix'])
    def set_image_info(self, objects, field_names):
        """
        `rbd info` and `rbd.Image.stat` are really similar: The first one calls the second one.
        As the first one is the only provider of the data_pool, we have to call `rbd info` anyway.
        For performance reasons, let's use it as much as possible. Although, I still prefer a
        native Python API.

        Also, the format of `features` is compatible to our format.
        """
        context = NodbManager.nodb_context
        pool = CephPool.objects.get(id=self.pool)
        with rbd_image(RbdApi(context.mgr.rados, pool.name), self.name) as image:  # type: rbd.Image
            stat = image.stat()
            self.size = stat['size']
            self.obj_size = stat['obj_size']
            self.num_objs = stat['num_objs']
            self.block_name_prefix = stat['block_name_prefix']
            self.old_format = image.old_format()
            self.features = RbdApi.bitmask_to_list(image.features())

            # FIXME: Make the data pool available in rbd.pyx
            # data_pool_name = image.data_pool():
            # if data_pool_name:
            #    self.data_pool = CephPool.objects.get(name=data_pool_name).name

    @bulk_attribute_setter(['used_size'])
    def set_disk_usage(self, objects, field_names):
        self.used_size = None

        if self.features is None or 'fast-diff' in self.features:
            pass
            # FIXME: Make the disk usage available in rbd.pyx
            # context = NodbManager.nodb_context
            # with rbd_image(context.mgr.rados, self.pool.name) as image:  # type: rbd.Image
            #     self.used_size = image.disk_usage()

    @bulk_attribute_setter(['stripe_unit', 'stripe_count'])
    def set_stripe_info(self, objects, field_names):
        if 'stripingv2' in self.features:
            context = NodbManager.nodb_context
            with rbd_image(context.mgr.rados, self.pool.name) as image:  # type: rbd.Image
                self.stripe_count = image.stripe_count()
                self.stripe_unit = image.stripe_unit()
        else:
            self.stripe_count = None
            self.stripe_unit = None
