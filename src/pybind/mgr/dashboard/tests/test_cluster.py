import json
import unittest

import mock

from ..models.nodb import nodb_context


@unittest.skip("This tests need to be adapted, no more mgr_module available")
class CephClusterTestCase(unittest.TestCase):
    @mock.patch('dashboard_v2.models.send_command_api.SendCommandApi')
    def test_pause_flag(self, SendCommandApi_mock):
        SendCommandApi_mock.return_value.osd_dump.return_value = {
            'flags': 'pauserd,pausewr,sortbitwise,recovery_deletes'
        }
        from ..models.cluster import CephCluster
        with nodb_context(mock.Mock()):
            self.assertEqual(set(CephCluster(fsid='fsid').osd_flags), {
                'pause', 'sortbitwise', 'recovery_deletes'
            })

    @mock.patch('dashboard_v2.models.nodb.NodbModel.get_modified_fields')
    @mock.patch('dashboard_v2.models.send_command_api.SendCommandApi._call_mon_command')
    def test_save(self, _call_mon_command_mock, get_modified_fields_mock):
        api_controller = mock.MagicMock()
        api_controller.mgr.get.return_value = {'json': json.dumps({'monmap': {'fsid': 'xyz'}})}
        from ..models.cluster import CephCluster
        with nodb_context(api_controller):
            cluster = CephCluster.objects.get()
            get_modified_fields_mock.return_value = ({
                                                        'osd_flags': ['a', 'b'],
                                                     }, mock.Mock(osd_flags=['a', 'c']))
            cluster.osd_flags = ['a', 'b']

            cluster.save(force_update=True)
            self.assertEqual(_call_mon_command_mock.mock_calls, [
                mock.call('osd unset', {'key': 'c'}, output_format='string'),
                mock.call('osd set', {'key': 'b'}, output_format='string')
                         ])
