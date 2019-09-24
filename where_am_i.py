
# -*- coding: utf-8 -*-
"""Where Am I?

Where Am I is a geocode resolution service that provides longitude and 
latitude coordinates which correspond to your search query. Search queries
can be a street address, or a landmark for example. A single coordinate is 
returned, unlike some APIs which return a polygon or bounding box.

Example:
    To run a geocode query from the command line, you can use the following
    syntax::

        $ python where_am_i.py "123 Elm Street, Seattle"
        $ python where_am_i.py "Empire State Building"

Where Am I supports more than one service. If the first service is unreachable,
or the query returns no results, a resolution will be attempted against the
next service in the list. This ordered list (most preferable first) is specified
in the YAML configuration file.

"""

import sys
import yaml
import json
from urllib.request import urlopen
from urllib.parse import urlencode


class GeoLookupError(Exception):
    """
    General GeoLookupService exception
    """
    pass


class GeoLookupService(object):
    def __init__(self, service_name, credentials):
        self._service_name = service_name

    def lookup(self, search_term):
        pass

    def _build_successful_response(self, lng, lat):
        return {
            'status': 'success',
            'result': {
                'service': self._service_name,
                'location': {'lng': lng, 'lat': lat}
            }
        }


class GeoLookupGoogle(GeoLookupService):
    def __init__(self, service_name, credentials):
        super().__init__(service_name, credentials)
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

        location = result["results"][0]["geometry"]["location"]
        return self._build_successful_response(
            lng=location['lng'],
            lat=location['lat'])


class GeoLookupHere(GeoLookupService):
    def __init__(self, service_name, credentials):
        super().__init__(service_name, credentials)
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
        else:
            top_result = result["Response"]["View"][0]["Result"][0]

        return self._build_successful_response(
           lng=top_result["Location"]["DisplayPosition"]['Longitude'],
           lat=top_result["Location"]["DisplayPosition"]['Latitude'])


class WhereAmI(object):
    def __init__(self, config_yml):
        with open(config_yml) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)

        geo_name_to_obj = {
            "Google Maps API": GeoLookupGoogle,
            "HERE": GeoLookupHere
        }

        self._services = []
        for geo_service_name, geo_service_info in config['services'].items():
            if geo_service_name in geo_name_to_obj.keys():
                geo_obj = geo_name_to_obj[geo_service_name](
                    geo_service_name, geo_service_info['credentials'])
                self._services.append(geo_obj)
            else:
                raise RuntimeError(
                    "Unknown geocoding service: {}".format(geo_service_name))

    def geo_lookup(self, search_term):
        """
        Perform a geocode lookup
        """
        if len(self._services) == 0:
            raise GeoLookupError("There are no configured geocoding services")

        for geo_service in self._services:
            try:
                return geo_service.lookup(search_term)
            except GeoLookupError:
                pass

        raise GeoLookupError("No results found")


# Running the script directly provides a basic CLI search utility
if __name__ == '__main__':
    if len(sys.argv) == 2:
        print(WhereAmI('config.yml').geo_lookup(sys.argv[1]))
    else:
        print('Usage: python {} "address"'.format(sys.argv[0]))
