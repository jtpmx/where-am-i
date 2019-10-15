
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
        $ python where_am_i.py --rest_url http://localhost:5000 MIT

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
import socket
from urllib.error import URLError, HTTPError
from urllib.request import urlopen
from urllib.parse import urlencode, quote
from http import HTTPStatus

class GeoLookupError(Exception):
    """
    General GeoLookupService exception
    """
    def __init__(self, msg, error_code):
        """
        Instantiate a GeoLookupError

        Args:
              msg: An error description
              error_code: Conventional HTTP error code
        """
        Exception.__init__(self, "{} - Error {}".format(msg, error_code))
        self.error_code = error_code


class GeoConfigError(RuntimeError):
    """
    Where Am I Configuration error
    """
    pass


class GeoLookupService(object):
    """
    Base class for a proxied geocoding service
    """
    def __init__(self, service_name, credentials, timeout):
        """
        Initialize the proxied geocoding service

        Args:
          service_name: A human-readable name for this geocoding service
          credentials: a dict of API parameters required for auth
          timeout: connection timeout in seconds

        """
        self._service_name = service_name
        self._timeout_sec = timeout

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
    def __init__(self, service_name, credentials, timeout):
        """
        Initialize the Google geocoding proxy

        Args:
          service_name: YAML configuration name for the Google API service
          credentials: a dict containing a single value, the Google Maps api_key
        Raises:
            GeoConfigError: Credentials missing

        """
        super().__init__(service_name, credentials, timeout)

        if 'api_key' in credentials:
            self.api_key = credentials['api_key']
        else:
            raise GeoConfigError(
                "'api_key' must be defined for {}".format(service_name))

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
            response = urlopen(
                url="{}?{}".format(self.url, urlencode(get_params)),
                timeout=self._timeout_sec)
        except socket.timeout:
            raise GeoLookupError(
                "{} timeout".format(self),
                HTTPStatus.REQUEST_TIMEOUT)    
        except URLError as e:
            if e.reason.errno == 65:  # Timeout errors manifest as this
                raise GeoLookupError(
                    "{}: no route to host".format(self),
                    HTTPStatus.REQUEST_TIMEOUT)
            else:
                raise GeoLookupError(
                    "{} invalid URL".format(self),
                    HTTPStatus.SERVICE_UNAVAILABLE)

        try:
            result = json.loads(response.read())
        except:
            raise GeoLookupError(
                "Error parsing JSON response from {}".format(self),
                HTTPStatus.PAYMENT_REQUIRED)          
      
        try:
            if result['status'] == 'REQUEST_DENIED':
                raise GeoLookupError(
                    "Invalid {} credentials".format(self),
                    HTTPStatus.UNAUTHORIZED)

            if len(result["results"]) == 0:
                raise GeoLookupError(
                    "No result found",
                    HTTPStatus.NOT_FOUND)

            location = result["results"][0]["geometry"]["location"]
        except KeyError:
            raise GeoLookupError(
                "Unexpected JSON response from {}".format(self),
                HTTPStatus.PAYMENT_REQUIRED)

        return self._build_successful_response(
            lng=location['lng'],
            lat=location['lat'])


class GeoLookupHere(GeoLookupService):
    """
    An interface to the HERE geocode service. For instructions on obtaining a
    key, please see the following documentation:

      developer.here.com/map/API‎

    """
    def __init__(self, service_name, credentials, timeout):
        """
        Initialize the HERE geocoding proxy

        Args:
          service_name: YAML configuration name for HERE service
          credentials: a dict containing an app_code, and app_id

        """
        super().__init__(service_name, credentials, timeout)
        self.url = 'https://geocoder.api.here.com/6.2/geocode.json'

        if 'app_id' in credentials:
            self.app_id = credentials['app_id']
        else:
            raise GeoConfigError(
                "'app_id' must be defined for {}".format(service_name))

        if 'app_code' in credentials:
            self.app_code = credentials['app_code']
        else:
            raise GeoConfigError(
                "'app_code' must be defined for {}".format(service_name))

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
            response = urlopen(
                url="{}?{}".format(self.url, urlencode(get_params)),
                timeout=self._timeout_sec)
        except HTTPError as e:
            if e.code == 400:
                raise GeoLookupError(
                    "Bad query string",
                    HTTPStatus.BAD_REQUEST)
            elif e.code == 401:
                raise GeoLookupError(
                    "Invalid {} credentials".format(self),
                    HTTPStatus.UNAUTHORIZED)
            elif e.code == 404:
                raise GeoLookupError(
                    "{} REST API not found".format(self),
                    HTTPStatus.SERVICE_UNAVAILABLE)
            else:
                raise GeoLookupError(
                    "Received {} from {}".format(e.code, self),
                    HTTPStatus.PAYMENT_REQUIRED)
        except URLError as e:
            if e.reason.errno == 65:
                raise GeoLookupError(
                    "{}: no route to host".format(self),
                    HTTPStatus.REQUEST_TIMEOUT)
            else:
                raise GeoLookupError(
                    "{} REST API not found".format(self),
                    HTTPStatus.SERVICE_UNAVAILABLE)

        try:
            result = json.loads(response.read())
        except:
            raise GeoLookupError(
                "Error parsing JSON response from {}".format(self),
                HTTPStatus.PAYMENT_REQUIRED)          

        try:
            if len(result["Response"]["View"]) == 0:
                raise GeoLookupError(
                    "No result found",
                    HTTPStatus.NOT_FOUND)
            top_result = result["Response"]["View"][0]["Result"][0]
        except KeyError:
            raise GeoLookupError(
                "Unexpected JSON response from {}".format(self),
                HTTPStatus.PAYMENT_REQUIRED)

        return self._build_successful_response(
           lng=top_result["Location"]["DisplayPosition"]['Longitude'],
           lat=top_result["Location"]["DisplayPosition"]['Latitude'])


"""
When adding a new GeoLookup service, add a human-friendly name mapping to the
GEO_NAME_TO_CLASS_MAPPING. This is how the servivce will be referenced from 
the YAML configuration file.
"""
GEO_NAME_TO_CLASS_MAPPING = {
    "Google Maps API": GeoLookupGoogle,
    "HERE": GeoLookupHere
}


class WhereAmI(object):
    """
    Where Am I - performs a proxied geocode query against multiple 
    third-party services
    """
    def __init__(self, config_yml):
        """
        Initialize the Where Am I application using the configuration
        defined in config.yml

        Args:
            config_yml: file system path to 'config.yml'
        Raises:
            RuntimeError: Configuration was invalid

        """
        try:
            with open(config_yml) as f:
                config = yaml.load(f, Loader=yaml.FullLoader)
        except FileNotFoundError:
            raise GeoConfigError("Config file {} not found".format(config_yml))
        except yaml.scanner.ScannerError:
            raise GeoConfigError("Error parsing {}".format(config_yml))

        if 'services' not in config or not isinstance(config['services'], dict):
            raise GeoConfigError("Configuration is missing 'services' list")

        self._services = []

        # Note: The services dict is ordered
        for geo_service_name, geo_service_info in config['services'].items():
            if geo_service_name in GEO_NAME_TO_CLASS_MAPPING.keys():
                if 'credentials' not in geo_service_info:
                    raise GeoConfigError(
                        "credentials not found: {}".format(geo_service_name))
                if 'timeout' not in geo_service_info:
                    raise GeoConfigError(
                        "timeout not specified: {}".format(geo_service_name))

                geo_obj = GEO_NAME_TO_CLASS_MAPPING[geo_service_name](
                    service_name=geo_service_name,
                    credentials=geo_service_info['credentials'],
                    timeout=geo_service_info['timeout'])

                self._services.append(geo_obj)
            else:
                raise GeoConfigError(
                    "{} is an invalid service name".format(geo_service_name))

    def geo_lookup(self, search_term):
        """
        Perform a geocode lookup against multiple services. Once a successful
        result is found, stop progressing through the list and return the
        geocoded result.

        Args:
            search_term: A street, place, or landmark
        Raises:
            GeoConfigError: If no geocode services are configured
        Returns:
            On success, returns a long/lat result, including metadata

        """
        num_services = len(self._services)

        if num_services == 0:
            raise GeoConfigError("There are no configured geocoding services")

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
        help='Location of YAML configuration file')
    parser.add_argument(
        '--rest_url', 
        required=False,
        type=str,
        help='Use the RESTful service to perform the query instead')

    args = parser.parse_args()

    if args.rest_url:
        url = "{}/geo/{}".format(args.rest_url, quote(args.query))

        try:
            response = urlopen(url)
        except HTTPError as e:
            print("Failed. Got HTTP Response: {}".format(e.code))
        else:
            json_response = json.loads(response.read())
            geo_result = json.dumps(json_response)
            print(geo_result)
    else:
        geo_result = WhereAmI(args.config).geo_lookup(args.query)
        print(geo_result)
