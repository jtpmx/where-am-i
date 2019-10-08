
# -*- coding: utf-8 -*-
"""
Where Am I?

Where Am I is a geocode resolution service that provides longitude and 
latitude coordinates corresponding to your search query. Search queries
can be in the form of a street address, or a landmark for example. 

Example:

    To run a geocode query using the command line, you can use the following
    syntax::

        $ python where_am_i.py "123 Elm Street, Seattle"
        $ python where_am_i.py --rest_host http://localhost:5000 MIT

Where Am I is just a proxy service--the actual geocode lookup is performed
by a third-party service and the results are transformed into a unified result.
This transformation was done so that a user of this service would not need
write different transcoding logic for each individual service.

If the first service is unreachable or the query returns no results, the query
will be attempted against the next service in the list. This list is
specified in the YAML configuration file and is ordered from most preferable to
least. If all services are exhausted, an error is returned.

"""
import sys
import yaml
import json
import argparse
from urllib.error import URLError, HTTPError
from urllib.request import urlopen
from urllib.parse import urlencode, quote


class GeoLookupError(Exception):
    """
    General GeoLookupService exception
    """
    pass


class GeoLookupService(object):
    """
    Base class for a proxied geocoding service
    """
    def __init__(self, service_name, credentials):
        """
        Initialize the proxied geocoding service

        Args:
          service_name: A human-readable name for this geocoding service
          credentials: a dict of API parameters required for auth

        """
        self._service_name = service_name

    def __repr__(self):
        """
        Printable representation of GeoLookupService
        """
        return self._service_name

    def lookup(self, search_term):
        """
        Perform a geocode resolution against a third-party service

        Args:
            search_term: A street, place, landmark
        Raises:
            GeoLookupError: bad search term, HTTP error, etc
        Returns:
            a dict containing the long/lat result
        """
        pass

    def _build_successful_response(self, lng, lat):
        """
        Wrap the long/lat information with additional metadata

        Args:
            lng: Longitude
            lat: Latitude
        Returns:
            a dict containing the long/lat, a status code, and the
            human-friendly service name.
        """
        return {
            'status': 'success',
            'result': {
                'service': self._service_name,
                'location': {'lng': lng, 'lat': lat}
            }
        }


class GeoLookupGoogle(GeoLookupService):
    """
    An interface to the Google Maps API geocode service. For instructions
    on obtaining a key, please see the following documentation:

      developers.google.com/maps/documentation/javascript/get-api-key

    """
    def __init__(self, service_name, credentials):
        """
        Initialize the Google geocoding proxy

        Args:
          service_name: YAML configuration name for the Google API service
          credentials: a dict containing a single value, the Google Maps api_key

        """
        super().__init__(service_name, credentials)
        self.api_key = credentials['api_key']
        self.url = 'https://maps.googleapis.com/maps/api/geocode/json'

    def lookup(self, search_term):
        """
        Perform a geocode resolution against the Google Maps geocode service

        Args:
            search_term: A street, place, landmark
        Raises:
            GeoLookupError: bad search term, HTTP error, etc
        Returns:
            a dict containing the long/lat result
        """
        get_params = {
            'address': search_term,
            'key': self.api_key}

        try:
            response = urlopen("{}?{}".format(self.url, urlencode(get_params)))
        except (URLError, HTTPError):
            raise GeoLookupError("Connection error")

        result = json.loads(response.read())

        try:
            if result['status'] == 'REQUEST_DENIED':
                raise GeoLookupError("Invalid {} credentials".format(self))
            if len(result["results"]) == 0:
                raise GeoLookupError("No result found")
            location = result["results"][0]["geometry"]["location"]
        except KeyError:
            raise GeoLookupError("Unexpected response from {}".format(self))

        return self._build_successful_response(
            lng=location['lng'],
            lat=location['lat'])


class GeoLookupHere(GeoLookupService):
    """
    An interface to the HERE geocode service. For instructions on obtaining a
    key, please see the following documentation:

      developer.here.com/map/API‎

    """
    def __init__(self, service_name, credentials):
        """
        Initialize the HERE geocoding proxy

        Args:
          service_name: YAML configuration name for HERE service
          credentials: a dict containing an app_code, and app_id

        """
        super().__init__(service_name, credentials)
        self.app_id = credentials['app_id']
        self.app_code = credentials['app_code']
        self.url = 'https://geocoder.api.here.com/6.2/geocode.json'

    def lookup(self, search_term):
        """
        Perform a geocode resolution against the HERE geocode service

        Args:
            search_term: A street, place, or landmark
        Raises:
            GeoLookupError: bad search term, HTTP error, etc
        Returns:
            a dict containing the long/lat result
        """
        get_params = {
            'searchtext': search_term,
            'app_id': self.app_id,
            'app_code': self.app_code,
            'gen': 9}

        try:
            response = urlopen("{}?{}".format(self.url, urlencode(get_params)))
        except HTTPError as e:
            if e.code == 400:
                raise GeoLookupError("Bad query string")
            elif e.code == 401:
                raise GeoLookupError("Invalid {} credentials".format(self))   
            else:
                raise GeoLookupError("HTTP error")
        except URLError:
            raise GeoLookupError("{} connection error".format(self))

        result = json.loads(response.read())

        try:
            if len(result["Response"]["View"]) == 0:
                raise GeoLookupError("No result found")
            top_result = result["Response"]["View"][0]["Result"][0]
        except KeyError:
            raise GeoLookupError("Unexpected response from {}".format(self))

        return self._build_successful_response(
           lng=top_result["Location"]["DisplayPosition"]['Longitude'],
           lat=top_result["Location"]["DisplayPosition"]['Latitude'])


"""
When adding a new GeoLookup service, add a human-friendly name mapping to the
GEO_NAME_TO_CLASS_MAPPING dictionary. This is how the servivce will be
referenced from the YAML configuration file.
"""
GEO_NAME_TO_CLASS_MAPPING = {
    "Google Maps API": GeoLookupGoogle,
    "HERE": GeoLookupHere
}


class WhereAmI(object):
    """
    Where Am I - performs a proxied geocode query against multiple 
    third-party services

    Args:
        config_yml: file system path to 'config.yml'
    """
    def __init__(self, config_yml):
        with open(config_yml) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)

        self._services = []
        for geo_service_name, geo_service_info in config['services'].items():
            if geo_service_name in GEO_NAME_TO_CLASS_MAPPING.keys():
                geo_obj = GEO_NAME_TO_CLASS_MAPPING[geo_service_name](
                    geo_service_name, geo_service_info['credentials'])
                self._services.append(geo_obj)
            else:
                raise RuntimeError(
                    "{} is an invalid service name".format(geo_service_name))

    def geo_lookup(self, search_term):
        """
        Perform a geocode lookup against multiple services. Once a successful
        result is found, stop progressing through the list and return the
        geocoded result.

        Args:
            search_term: A street, place, or landmark
        Raises:
            GeoLookupError: If no geocode services are configured
        Returns:
            On success, returns a long/lat result, including metadata

        """
        num_services = len(self._services)

        if num_services == 0:
            raise GeoLookupError("There are no configured geocoding services")

        for i, geo_service in enumerate(self._services):
            try:
                return geo_service.lookup(search_term)
            except GeoLookupError:
                if i < num_services - 1:
                    pass
                else:
                    # This is the last service in our list. Throw an error.
                    raise


# Running the script directly provides a basic CLI search utility
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Get the location of a street or landmark')
    parser.add_argument(
        'query',
        type=str,
        help='Street name or landmark')
    parser.add_argument(
        '--config', 
        default="config.yml",
        type=str,
        help='WhereAmI configuration file')
    parser.add_argument(
        '--rest_host', 
        required=False,
        type=str,
        help='Use the RESTful service to perform the query instead')

    args = parser.parse_args()

    if args.rest_host:
        url = "{}/geo/{}".format(args.rest_host, quote(args.query))
        json_response = json.loads(urlopen(url).read())
        geo_result = json.dumps(json_response)
    else:
        geo_result = WhereAmI(args.config).geo_lookup(args.query)
    
    print(geo_result)