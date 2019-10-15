# Where Am I?

Where Am I is a geocode resolution service that provides longitude and latitude coordinates corresponding to a search query, which can be in the form of a street address, or a landmark. 

Where Am I is a proxy--the actual geocode lookup is performed by a third-party service, and the results are transformed into a simplified result. The simplified result is a single point (as opposed to a polygon or bounding box) which most closely represents the location of the street or entity specified by the query.

This service can be configured to query multiple third-party geocoding services. If the first service in the list is unreachable, times-out, returns an error, or produces no results, the query will be attempted against the next service in the list until the list is exhausted.

A reference design for a REST service has also been included--it is implemented using the Flask framework.

## Installation

* Setup a Python 3 virtualenv environment
* pip install the following packages:
  * `pip install flask flask-restful pyyaml`
* Get API keys for Google Maps API, and HERE
* Copy `config.yml.dist` to `config.yml` and add API credentials to `config.yml`
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

Where Am I is configured using a YAML file. `services` contains an entry for each enabled third-party service. `services` is an ordered list, ranked from the most-preferrable service configuration to the least-preferrable. It is possible to add multiple copies of a service (Google Maps API for example) with different credentials. 

    services:
      SERVICE NAME:
        credentials:
          API_KEY: SECRET_API_KEY
 
The default configuration file `config.yml` has two entries, one for each of the two supported services by default: Google Maps API and HERE. The tilde (~) is a placeholder for the API credentials which you are responsible for obtaining. For instructions on getting an HERE key, see the following document: https://developer.here.com/map/API. For Google Maps, see: https://developers.google.com/maps/documentation/javascript/get-api-key.

    services:
      Google Maps API:
        timeout: 1.0
        credentials:
          api_key: ~
      HERE:
        timeout: 1.0
        credentials:
          app_code: ~
          app_id: ~
      RandomGeoService:
        timeout: 1.0
        credentials:
          special_key: ~

# REST API

Where Am I includes a Flask service which features a simple GET interface for making requests. Here is an example usage using the included Flask service running locally on port 5000 (default). 

Get the location of the *Massachusetts Institute of Technology* campus:

    http://localhost:5000/geo/MIT

Successful response example:

```
{
  "status": "success",
  "result": {
    "service": "Google Maps API",
    "location": {
      "lng": -71.09416,
      "lat": 42.360091
    }
  }
}
```

Here is an example of a query which has no result:

    http://localhost:5000/geo/this%20is%20an%20invalid%20query

HTTP response code:

    404 (Not found)

JSON body:

```
{
  "status": "No result found",
  "result": {}
}
```

## HTTP Response Codes

Where Am I uses conventional HTTP response codes to indicate the success or failure of an API request. In general, codes in the 2xx range indicate success. Codes in the 4xx range indicate an error that failed given the information provided (bad credentials, bad query, connectivity issue with third-party service, etc). Codes in the 5xx range (except for 503) indicate an internal error.

| Code | Description |
| ---- | ----------- |
| 200 | Geocoding resolution succeeded |
| 400 | The query was invalid |
| 401 | Authentication failed. Check your credential settings |
| 402 | The query was valid, but an unexpected response was received from the third-party API |
| 404 | The location could not be resolved for the query provided |
| 408 | Timed out waiting for response. Try increasing the configured timeout |
| 503 | Third-party service was unreachable. |
| 5xx | Internal server error |

# Command-Line Utility
 
A CLI utility is included which allows you to execute queries:

    $ python where_am_i.py "400 Broad St, Seattle"
    
It can also be used to run queries against a REST service:

    $ python flask_service.py &  # start the REST service first
    $ python where_am_i.py --rest_url http://localhost:5000 "Empire State Building"

# Adding Support For a New Third-Party Service

Adding a new service is simple, and can be done using a few lines of Python code.

### Build a GeoLookupService Class

Create a class which inherits from `GeoLookupService` and implements `__init__` (the constructor), and the `lookup` method. 

The constructor will typically be responsible for storing the credentials which are passed to `__init__`.

The lookup method is responsible for interacting with the third-party geocoding API. It sends the query to the service, collects the response, and returns the long/lat result. Use the helper method `GeoLookupService._build_successful_response` to wrap the long/lat coordinates in the correct format, and with the correct metadata.

Make sure that all lookup errors map to the uniform set of HTTP responses specified above.

### Human-Friendly Name and YAML Configuration

Add a human-friendly name mapping to the `GEO_NAME_TO_CLASS_MAPPING` global. This is how the service will be referenced from the YAML configuration file. The key is the human-readable name, and the value is the associated `GeoLookupService` class. Finally, add this service to the `services` list in `config.yml`.
