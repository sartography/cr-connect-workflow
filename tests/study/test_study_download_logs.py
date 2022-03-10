from tests.base_test import BaseTest

from crc.api.study import download_logs_for_study


class TestDownloadLogsForStudy(BaseTest):

    # TODO: finish writing tests
    def test_download_logs_for_study(self):

        study_id = 6
        result = download_logs_for_study(study_id)

        print('test_download_logs_for_study')
