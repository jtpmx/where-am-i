from flask import Flask
from flask_restful import Resource, Api
from where_am_i import WhereAmI, GeoLookupError

app = Flask(__name__)
api = Api(app)


class RestfulWhereAmI(Resource):
    CONF_PATH = 'config.yml'

    def get(self, address):
        try:
            return WhereAmI(self.CONF_PATH).geo_lookup(address)
        except GeoLookupError as geo_error:
            return {
                "status": str(geo_error),
                "result": {}
            }


api.add_resource(RestfulWhereAmI, '/geo/<string:address>')

if __name__ == '__main__':
    app.run(debug=True)
