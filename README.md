# Where Am I?

Where Am I is a geocode resolution service that provides longitude and latitude coordinates corresponding to your search query, which can be in the form of a street address, or a landmark. 

To run a geocode query using the command line utility, you can use the following syntax:

    $ python where_am_i.py "123 Elm Street, Seattle"
    $ python where_am_i.py "Empire State Building"

Where Am I is a proxy service--the actual geocode lookup is performed by a third-party service, and the results are transformed into a simplified result. The simplified result is a single point (as opposed to a polygon or bounding box) which most closely represents the location of the query.

This service can be configured to query multiple third-party geocoding services. If the first service in the list is unreachable, times-out, or returns no results, the query will be attempted against the next service in the list until the list is exhausted.

A reference design for a REST service has also been included--it is implemented using the Flask framework.

## Installation Steps

* Get API keys for Google Maps API, and HERE. Add API credentials to `config.yml`
* Setup a virtualenv environment
* pip install the following packages:
  * `pip install flask flask-restful pyyaml`
* Start the Flask service. This will start a REST service on port 5000:
  * `python flask_service.py`
* Test the service:
  * `curl "http://localhost:5000/geo/empire%20state%20building"`
  * ```{
       "status": "success",
        "result": {
           "service": "Google Maps API",
           "location": {
             "lng": -73.98566,
             "lat": 40.74844
           }
         }
       }
    ```

## Configuration

Configuration is done via a YAML file. `services` contains an entry for each enabled third-party service. This is an ordered list, ranked from most-preferrable to least:

    services:
      SERVICE NAME:
        credentials:
          API_KEY: SECRET_API_KEY
 
The default configuration file `config.yml` has two entries, one for each of the two supported services b default: Google Maps API and HERE. The tilde (~) is a placeholder for the API credentials which you are responsible for acquiring. For instructions on getting an HERE key, see the following document: https://developer.here.com/map/API. For Google Maps, see: https://developers.google.com/maps/documentation/javascript/get-api-key.

    services:
      Google Maps API:
        credentials:
          api_key: ~
      HERE:
        credentials:
          app_code: ~
          app_id: ~
      RandomGeoService
        credentials:
          special_key: ~


## Adding a New Service

Adding a new service is simple, and can be done using a few lines of Python code.

### Build a GeoLookupService Class

Create a class which inherits from `GeoLookupService` and implements `__init__` (the constructor), and the `lookup` method. 

The constructor will typically be responsible for storing the credentials which are passed to `__init__`.

The lookup method is responsible for interacting with the third-party geocoding API. It sends the query to the service, collects the response, and returns the long/lat result. Use the helper method `GeoLookupService._build_successful_response` to wrap the long/lat coordinates in the correct format, and with the correct metadata.

### Human-Friendly Name and YAML Configuration

Add a human-friendly name mapping to the `GEO_NAME_TO_CLASS_MAPPING` global. This is how the service will be referenced from the YAML configuration file. The key is the human-readable name, and the value is the associated `GeoLookupService` class. Finally, add this service to the `service` list in `config.yml`.
