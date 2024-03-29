from flask import Flask
from flask_restful import Resource, Api
from where_am_i import WhereAmI, GeoLookupError, GeoConfigError

app = Flask(__name__)
api = Api(app)


class RestfulWhereAmI(Resource):
    """
    A RESTFul interface for the Where Am I API
    
    """
    CONF_PATH = 'config.yml'

    def get(self, address):
        """
        Handler for the /geo GET endpoint

        Args:
            address: search query

        """
        try:
            where_am_i = WhereAmI(self.CONF_PATH)
        except GeoConfigError as e:
            return {
                "status": str(e),
                "result": {}
            }, 500

        try:
            return where_am_i.geo_lookup(address), 200
        except GeoLookupError as geo_error:
            return {
                "status": str(geo_error),
                "result": {}
            }, geo_error.error_code


api.add_resource(RestfulWhereAmI, '/geo/<string:address>')

if __name__ == '__main__':
    app.run(debug=True)
