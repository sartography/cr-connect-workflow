import requests


class LoadStudies:
    """Just your basic class that can pull in data from a few api endpoints and do a basic task."""

    def do_task(self, task_data):
        print('*** LoadStudies > do_task ***')
        print('task_data', task_data)

class LoadStudy:
    """Just your basic class that can pull in data from a few api endpoints and do a basic task."""

    def do_task(self, task_data):
        print('*** LoadStudies > do_task ***')
        print('task_data', task_data)
        irb_study = {
            'tbd': 0,
            'protocol_builder_available': True,
            'irb_review_type': 'Full Board',
            'irb_requires': True,
        }

        return irb_study
