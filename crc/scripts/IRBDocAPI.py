import requests


class IRBDocAPI:
    """Just your basic class that can pull in data from a few api endpoints and do a basic task."""

    def do_task(self, task_data):
        print('*** IRB_Doc_API > do_task ***')
        print('task_data', task_data)
