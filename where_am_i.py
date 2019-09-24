import sys
import yaml
import json
from urllib.request import urlopen
from urllib.parse import urlencode
from abc import ABC, abstractmethod


class GeoLookupError(Exception):
    """
    General GeoLookupService exception
    """
    pass


class GeoLookupService(ABC):
    @abstractmethod
    def __init__(self, credentials):
        pass

    @abstractmethod
    def lookup(self, search_term):
        pass


class GeoLookupGoogle(GeoLookupService):
    def __init__(self, credentials):
        self.api_key = credentials['api_key']
        self.url = 'https://maps.googleapis.com/maps/api/geocode/json'

    def lookup(self, search_term):
        get_params = {
            'address': search_term,
            'key': self.api_key}

        response = urlopen("{}?{}".format(self.url, urlencode(get_params)))
        result = json.loads(response.read())

        if len(result["results"]) == 0:
            raise GeoLookupError("No result found")

        return {
            'service': 'Google',
            'status': 'success',
            'location': result["results"][0]["geometry"]["location"]
        }
   

class GeoLookupHere(GeoLookupService):
    def __init__(self, credentials):
        self.app_id = credentials['app_id']
        self.app_code = credentials['app_code']
        self.url = 'https://geocoder.api.here.com/6.2/geocode.json'

    def lookup(self, search_term):
        get_params = {
            'searchtext': search_term,
            'app_id': self.app_id,
            'app_code': self.app_code,
            'gen': 9}

        response = urlopen("{}?{}".format(self.url, urlencode(get_params)))
        result = json.loads(response.read())

        if len(result["Response"]["View"]) == 0:
            raise GeoLookupError("No result found")

        display_pos = result["Response"]["View"][0]["Result"][0]["Location"]["DisplayPosition"]

        return {
            'service': 'HERE',
            'status': "success",
            'location': {
                'lat': display_pos["Latitude"],
                'lng': display_pos['Longitude']
            }
        }


class WhereAmI(object):
    def __init__(self, config_yml):
        with open(config_yml) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)

        self._services = []
        for geo_service_name, geo_service_info in config['services'].items():
            if geo_service_name == 'Google':
                self._services.append(GeoLookupGoogle(geo_service_info['credentials']))
            elif geo_service_name == 'HERE':
                self._services.append(GeoLookupHere(geo_service_info['credentials']))
            else:
                raise RuntimeError("Unknown geocoding service specified: {}".format(geo_service_name))

    def geo_lookup(self, search_term):
        """
        Perform a geocode lookup
        """
        if len(self._services) == 0:
            raise GeoLookupError("There are no configured geocoding services")

        result = None
        for geo_service in self._services:
            try:
                return {"result": geo_service.lookup(search_term)}
            except GeoLookupError:
                pass

        raise GeoLookupError("No results found")
 

# Running the script directly provides a basic CLI search utility
if __name__ == '__main__':
    if len(sys.argv) == 2: 
        print(WhereAmI('config.yml').geo_lookup(sys.argv[1]))
    else:
        print('Usage: python {} "ADDRESS"'.format(sys.argv[0]))