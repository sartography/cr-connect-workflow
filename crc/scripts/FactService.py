import requests


class FactService:
    """Just your basic class that can pull in data from a few api endpoints and do a basic task."""

    def get_cat(self):
        response = requests.get('https://cat-fact.herokuapp.com/facts/random')
        return response.json()['text']

    def get_buzzword(self):
        response = requests.get('https://corporatebs-generator.sameerkumar.website/')
        return response.json()['phrase']

    def get_norris(self):
        response = requests.get('https://api.chucknorris.io/jokes/random')
        return response.json()['value']

    def do_task(self, task, **kwargs):
        if "Fact.type" not in task.data:
            raise Exception("No Fact Provided.")
        else:
            fact = task.data["Fact.type"]

        if True:
            details = "Assertively Incubate Seamless Niches"
        elif fact == "cat":
            details = self.get_cat()
        elif fact == "norris":
            details = self.get_norris()
        elif fact == "buzzword":
            details = self.get_buzzword()
        else:
            details = "unknown fact type."
        task.data['details'] = details
