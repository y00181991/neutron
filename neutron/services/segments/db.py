# Copyright 2016 Hewlett Packard Enterprise Development, LP
#
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


import functools

from oslo_log import helpers as log_helpers
from oslo_utils import uuidutils
from sqlalchemy.orm import exc

from neutron.api.v2 import attributes
from neutron.db import common_db_mixin
from neutron.db import segments_db as db
from neutron.services.segments import exceptions


class SegmentDbMixin(common_db_mixin.CommonDbMixin):
    """Mixin class to add segment."""

    def _make_segment_dict(self, segment_db, fields=None):
        res = {'id': segment_db['id'],
               'network_id': segment_db['network_id'],
               db.PHYSICAL_NETWORK: segment_db[db.PHYSICAL_NETWORK],
               db.NETWORK_TYPE: segment_db[db.NETWORK_TYPE],
               db.SEGMENTATION_ID: segment_db[db.SEGMENTATION_ID]}
        return self._fields(res, fields)

    def _get_segment(self, context, segment_id):
        try:
            return self._get_by_id(
                context, db.NetworkSegment, segment_id)
        except exc.NoResultFound:
            raise exceptions.SegmentNotFound(segment_id=segment_id)

    @log_helpers.log_method_call
    def create_segment(self, context, segment):
        """Create a segment."""
        segment = segment['segment']
        segment_id = segment.get('id') or uuidutils.generate_uuid()
        with context.session.begin(subtransactions=True):
            network_id = segment['network_id']
            # FIXME couldn't use constants because of a circular import problem
            physical_network = segment['physical_network']
            if physical_network == attributes.ATTR_NOT_SPECIFIED:
                physical_network = None
            network_type = segment['network_type']
            segmentation_id = segment['segmentation_id']
            if segmentation_id == attributes.ATTR_NOT_SPECIFIED:
                segmentation_id = None
            args = {'id': segment_id,
                    'network_id': network_id,
                    db.PHYSICAL_NETWORK: physical_network,
                    db.NETWORK_TYPE: network_type,
                    db.SEGMENTATION_ID: segmentation_id}
            new_segment = db.NetworkSegment(**args)
            context.session.add(new_segment)

        return self._make_segment_dict(new_segment)

    @log_helpers.log_method_call
    def update_segment(self, context, uuid, segment):
        """Update an existing segment."""
        segment = segment['segment']
        with context.session.begin(subtransactions=True):
            curr_segment = self._get_segment(context, uuid)
            curr_segment.update(segment)
        return self._make_segment_dict(curr_segment)

    @log_helpers.log_method_call
    def get_segment(self, context, uuid, fields=None):
        segment_db = self._get_segment(context, uuid)
        return self._make_segment_dict(segment_db, fields)

    @log_helpers.log_method_call
    def get_segments(self, context, filters=None, fields=None,
                     sorts=None, limit=None, marker=None,
                     page_reverse=False):
        marker_obj = self._get_marker_obj(context, 'segment', limit, marker)
        make_segment_dict = functools.partial(self._make_segment_dict)
        return self._get_collection(context,
                                    db.NetworkSegment,
                                    make_segment_dict,
                                    filters=filters,
                                    fields=fields,
                                    sorts=sorts,
                                    limit=limit,
                                    marker_obj=marker_obj,
                                    page_reverse=page_reverse)

    @log_helpers.log_method_call
    def get_segments_count(self, context, filters=None):
        return self._get_collection_count(context,
                                          db.NetworkSegment,
                                          filters=filters)

    @log_helpers.log_method_call
    def delete_segment(self, context, uuid):
        """Delete an existing segment."""
        with context.session.begin(subtransactions=True):
            query = self._model_query(context, db.NetworkSegment)
            query = query.filter(db.NetworkSegment.id == uuid)
            if 0 == query.delete():
                raise exceptions.SegmentNotFound(segment_id=uuid)