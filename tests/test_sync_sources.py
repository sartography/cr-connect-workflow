import json
import os
import time

from crc.api.workflow_sync import get_sync_sources
from tests.base_test import BaseTest


def setup_test_environ():
    setup = [['CR_SYNC_SOURCE__0__url','https://my.target.com'],
             ['CR_SYNC_SOURCE__0__name','source name'],
             ['CR_SYNC_SOURCE__1__url','https://my.target2.com'],
             ['CR_SYNC_SOURCE__1__name','source2 name']]
    for thing in setup:
        os.environ[thing[0]] = thing[1]



class TestSyncsources(BaseTest):

    def test_sync_sources_from_env(self):
        setup_test_environ()
        parsed = get_sync_sources()
        self.assertEqual([{'url': 'https://my.target.com', 'name': 'source name'},
                          {'url': 'https://my.target2.com', 'name': 'source2 name'}],
                         parsed)


