import requests


class RandomFact:

    def get_cat(self):
        response = requests.get('https://cat-fact.herokuapp.com/facts/random')
        return response.json()['text']

    def get_buzzword(self):
        response = requests.get('https://corporatebs-generator.sameerkumar.website/')
        return response.json()['value']

    def get_norris(self):
        response = requests.get('https://api.chucknorris.io/jokes/random')
        return response.json()['phrase']

    def do_task(self, data, **kwargs):
        fact = data["fact"]
        if fact.type == "cat":
            fact.details = self.get_cat()
        elif fact.type == "norris":
            fact.details = self.get_norris()
        elif fact.type == "buzzword":
            fact.details = self.get_buzzword()
        else:
            fact.details = "unkown fact type."
        print ("The fact is : " + fact.type + " --> " + fact.details)
