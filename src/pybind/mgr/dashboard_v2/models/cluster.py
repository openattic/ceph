from ..models.send_command_api import SendCommandApiMixin
from ..tools import ExternalCommandError
from .nodb import *
from ..tools import RESTController  # pylint: disable=W0611


class CephCluster(NodbModel, SendCommandApiMixin):
    """Represents a Ceph cluster."""
    # TODO: Lost functionality compared to stand alone oA:
    # * Keyring path and username, keyring_candidates
    # * Cluster name handling

    fsid = CharField(primary_key=True, editable=False)
    health = CharField(editable=False)
    osd_flags = JsonField(base_type=list,
                          help_text='supported flags: full|pause|noup|nodown|noout|noin|nobackfill|'
                                    'norebalance|norecover|noscrub|nodeep-scrub|notieragent|'
                                    'sortbitwise|recovery_deletes|require_jewel_osds|'
                                    'require_kraken_osds')

    @classmethod
    def get_name(cls, fsid):
        return cls.objects.get(fsid=fsid).name

    @classmethod
    def get_file_path(cls, fsid):
        return cls.objects.get(fsid=fsid).config_file_path

    @property
    def status(self):
        val = self.send_command_api.status()
        if 'timechecks' not in val:
            try:
                val['timechecks'] = self.send_command_api.time_sync_status()
            except Exception:  # pylint: disable=W0703
                # TODO: find out, which Exception is thrown.
                # logger.exception('time_sync_status failed.')
                val['timechecks'] = {}
        val['health'] = self.send_command_api.health('detail')
        return val

    @staticmethod
    def get_all_objects(api_controller, query):
        """:type api_controller: RESTController"""
        # TODO: make sure, this works:
        fsid = json.loads(api_controller.mgr.get("mon_status")['json'])['monmap']['fsid']
        return [CephCluster(fsid=fsid)]

    # Added all arguments to make pylint happy:
    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        """
        This method implements three purposes.

        1. Implements the functionality originally done by django (e.g. setting id on self)
        2. Modify the Ceph state-machine in a sane way.
        3. Providing a RESTful API.
        """
        insert = self._state.adding  # there seems to be no id field.

        if insert and not force_update:
            raise ValidationError('Cannot create Ceph cluster.')

        diff, original = self.get_modified_fields(update_fields=update_fields)

        for key, value in diff.items():
            if key == 'osd_flags':
                api = self.send_command_api
                for flag in set(original.osd_flags) - set(value):
                    api.osd_unset(flag)
                for flag in set(value) - set(original.osd_flags):
                    api.osd_set(flag)
            else:
                pass
                #  logger.warning('Tried to set "{}" to "{}" on rbd "{}", which is not '
                #               'supported'.format(key, value, self.config_file_path))

        super(CephCluster, self).save(force_insert=force_insert, force_update=force_update,
                                      using=using, update_fields=update_fields)

    def get_crushmap(self):
        return CrushmapVersion.objects.get()

    @bulk_attribute_setter(['health'])
    def set_cluster_health(self, objects, field_names):  # pylint: disable=W0613
        try:
            health = self.send_command_api.health()
            # Ceph Luminous > 12.1 renamed `overall_status` to `status`
            self.health = health['status']
        except (TypeError, ExternalCommandError):  # TODO: which ObjectNotFound Exception?
            logger.exception('failed to get ceph health')
            self.health = 'HEALTH_ERR'

    # Also catch ObjectNotFound:
    @bulk_attribute_setter(['osd_flags'], catch_exceptions=(TypeError, ExternalCommandError))
    def set_osd_flags(self, objects, field_names):  # pylint: disable=W0613
        flags = self.send_command_api.osd_dump()['flags'].split(',')

        if 'pauserd' in flags and 'pausewr' in flags:
            # 'pause' is special:
            # To set this flag, call `ceph osd set pause`
            # To unset this flag, call `ceph osd unset pause`
            # But, `ceph osd dump | jq '.flags'` will contain 'pauserd,pausewr' if pause is set.
            # Let's pretend to the API that 'pause' is in fact a proper flag.
            flags = list((set(flags) - {'pauserd', 'pausewr'}).union({'pause'}))

        self.osd_flags = flags

    def __str__(self):
        return self.fsid

    def __unicode__(self):
        return self.fsid


class CrushmapVersion(NodbModel):
    # pylint: disable=E1136
    crushmap = JsonField(base_type=dict)

    @staticmethod
    def get_all_objects(api_controller, query):
        """:type context: ceph.restapi.FsidContext"""

        # TODO: make sure this works:
        crushmap = SendCommandApiMixin().send_command_api.osd_crush_dump()

        return [CrushmapVersion(id=1, crushmap=crushmap)]

    def get_tree(self):
        """Get the (slightly modified) CRUSH tree.

        Returns the CRUSH tree for the cluster. The `items` array of the `buckets` are modified so
        that they don't contain the OSDs anymore, but the children buckets.
        """

        crushtree = dict(self.crushmap, buckets=[])

        parentbucket = {}

        for cbucket in self.crushmap["buckets"]:

            for member in cbucket["items"]:
                # Creates an array with all children using their IDs as keys and themselves as
                # values. This already excludes the root buckets!
                parentbucket[member["id"]] = cbucket

            # Clears the items of `crushmap['buckets']`.
            cbucket["items"] = []

        buckets = self.crushmap["buckets"][:]  # Make a copy of the `buckets` array.
        while buckets:
            cbucket = buckets.pop(0)

            if cbucket["id"] in parentbucket:  # If the current bucket has a parent.

                # Add the child (cbucket) to the `items` array of the parent object.
                parentbucket[cbucket["id"]]["items"].append(cbucket)

            else:  # Has to be a root bucket.

                # Add the root bucket to the `buckets` array. It would be empty otherwise!
                crushtree["buckets"].append(cbucket)

        return crushtree
