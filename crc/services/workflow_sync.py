import json
from json import JSONDecodeError
from typing import List, Optional

import requests

from crc import app
from crc.api.common import ApiError


class WorkflowSyncService(object):

    @staticmethod
    def get_remote_file_by_hash(remote,md5_hash):
        url = remote+'/v1.0/file/'+md5_hash+'/hash_data'
        return WorkflowSyncService.__make_request(url,return_contents=True)

    @staticmethod
    def get_remote_workflow_spec_files(remote,workflow_spec_id):
        url = remote+'/v1.0/workflow_sync/'+workflow_spec_id+'/files'
        return WorkflowSyncService.__make_request(url)

    @staticmethod
    def get_remote_workflow_spec(remote, workflow_spec_id):
        """
        this just gets the details of a workflow spec from the
        remote side.
        """
        url = remote+'/v1.0/workflow_sync/'+workflow_spec_id+'/spec'
        return WorkflowSyncService.__make_request(url)

    @staticmethod
    def get_all_remote_workflows(remote):
        url = remote + '/v1.0/workflow_sync/all'
        return WorkflowSyncService.__make_request(url)

    @staticmethod
    def __make_request(url,return_contents=False):
        try:
            response = requests.get(url,headers={'X-CR-API-KEY':app.config['API_TOKEN']})
        except:
            raise ApiError("workflow_sync_error",url)
        if response.ok and response.text:
            if return_contents:
                return response.content
            else:
                return json.loads(response.text)
        else:
            raise ApiError("workflow_sync_error",
                           "Received an invalid response from the protocol builder (status %s): %s when calling "
                           "url '%s'." %
                           (response.status_code, response.text, url))
