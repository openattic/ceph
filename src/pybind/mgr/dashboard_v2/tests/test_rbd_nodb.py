import json
from unittest import TestCase, skipUnless

import mock

from ..models.nodb import nodb_context

has_rbd = True
try:
    import rbd
except ImportError as e:
    if 'dynamic module does not define module export function (PyInit_rbd)' in str(e):
        has_rbd = False


if has_rbd:
    from ..models.rbd import CephPool, CephRbd


class CephRbdNodbTestCase(TestCase):

    @skipUnless(has_rbd, 'No rbd module')
    @mock.patch('dashboard_v2.models.rbd.RbdApi')
    def test_rbd_assert_lazy(self, rbd_api_mock):
        """
        We have to make sure, all interesting fields are lazy evaluated. Otherwise listing
        them is too slow.
        """
        CephPool.get_all_objects.return_value = [CephPool(name='pool', id=1)]
        rbd_api_mock.return_value.list.return_value = ['rbd1']
        api_controller = mock.MagicMock()
        api_controller.mgr.get.return_value = {'json': json.dumps({'monmap': {'fsid': 'xyz'}})}
        with nodb_context(api_controller):
            rbd_ = CephRbd.objects.get()
            self.assertEqual(rbd_.name, 'rbd1')
            self.assertEqual(rbd_.pool, 2)
            self.assertEqual(rbd_.id, 'rbd/rbd1')
            for field in ['num_objs', 'obj_size', 'size', 'data_pool_id', 'features', 'old_format',
                          'used_size', 'stripe_unit', 'stripe_count']:
                self.assertTrue(rbd_.attribute_is_unevaluated_lazy_property(field),
                                '{} is already evaluated'.format(field))
