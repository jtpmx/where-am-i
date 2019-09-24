from flask import Flask
from flask_restful import Resource, Api
from where_am_i import WhereAmI, GeoLookupError

app = Flask(__name__)
api = Api(app)

class RestfulWhereAmI(Resource):
    def get(self, address):
        try:
            return WhereAmI('config.yml').geo_lookup(address)
        except GeoLookupError as geo_error:
            return {"status": str(geo_error)}

api.add_resource(RestfulWhereAmI, '/geo/<string:address>')

if __name__ == '__main__':
    app.run(debug=True)