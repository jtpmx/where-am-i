from flask import Flask
from flask_restful import Resource, Api
from where_am_i import WhereAmI, GeoLookupError

app = Flask(__name__)
api = Api(app)


class RestfulWhereAmI(Resource):
    """
    A RESTFul interface for the Where Am I application
    
    """
    CONF_PATH = 'config.yml'

    def get(self, address):
        """
        Handler for the /geo GET endpoint

        Args:
            address: search query

        """
        try:
            return WhereAmI(self.CONF_PATH).geo_lookup(address), 200
        except GeoLookupError as geo_error:
            return {
                "status": str(geo_error),
                "result": {}
            }, 200


api.add_resource(RestfulWhereAmI, '/geo/<string:address>')

if __name__ == '__main__':
    app.run(debug=True)
