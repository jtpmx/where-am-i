from flask import Flask, request
from json import dumps
from urllib.request import urlopen
from urllib.parse import urlencode
from abc import ABC, abstractmethod
import yaml
import json

class GeoLookupError(Exception):
   pass

class GeoLookup(ABC):
    @abstractmethod
    def lookup(self, address):
        pass

class GeoLookupGoogle(GeoLookup):
    def __init__(self, api_key):
        self.api_key = api_key
        self.url = 'https://maps.googleapis.com/maps/api/geocode/json'

    def lookup(self, address):
        args = {
            'address': address,
            'key': self.api_key}

        response = urlopen("{}?{}".format(self.url, urlencode(args)))
        result = json.loads(response.read())
        return result["results"][0]["geometry"]["location"]
   
class GeoLookupHere(GeoLookup):
    def __init__(self, app_id, app_code):
        self.app_id = app_id
        self.app_code = app_code
        self.url = 'https://geocoder.api.here.com/6.2/geocode.json'

    def lookup(self, address):
        args = {
            'searchtext': address,
            'app_id': self.app_id,
            'app_code': self.app_code,
            'gen': 9}

        response = urlopen("{}?{}".format(self.url, urlencode(args)))

        result = json.loads(response.read())
        display_pos = result["Response"]["View"][0]["Result"][0]["Location"]["DisplayPosition"]
        return {'lat': display_pos["Latitude"], 'lng': display_pos['Longitude']}

class GeoLookupAll(GeoLookup):
    def __init__(self, conf_path):
        with open(conf_path) as f:
            self.creds = yaml.load(f, Loader=yaml.FullLoader)['credentials']

        # services should be listed in order of preference: most prefered first to last
        self.serviceList = [
            GeoLookupHere(
                app_code=self.creds['here']['app_code'],
                app_id=self.creds['here']['app_id']),
            GeoLookupGoogle(
                api_key=self.creds['google']['key'])]

    def lookup(self, address):
        for geo_service in self.serviceList:
            try:
                return geo_service.lookup(address)
            except GeoLookupError:
                pass

        raise GeoLookupError("Exhausted all services")



app = Flask(__name__)

@app.route('/geocode.json', methods=['GET'])
def get_geocode():
    address = request.args.get('address')
    geo_lookup = GeoLookupAll(conf_path='config.yml')
    result = geo_lookup.lookup(address)
    return json.dumps({"Result": result})

if __name__ == '__main__':
     app.run(port='8000')