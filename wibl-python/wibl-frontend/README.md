# Public-facing frontend interface for monitoring WIBL processing

## Local development and testing
Build and run:
```shell
$ docker compose --env-file frontend.env up
$ docker compose --env-file frontend_test.env up
```

Test /heartbeat endpoint:
```shell
$ curl 'http://127.0.0.1:8002/heartbeat'
$ curl 'http://127.0.0.1:8000/heartbeat'
200
```
# Note if adding new file to python flask frontend (CS 792):

If creating a new python file to represent some new page for flask,
ensure that you do these steps to ensure that it renders/interacts properly:

In app_globals, inport your new file and add it to the blueprint

from wibl_frontend.query_main import query_main as query_main_blueprint
...
app.register_blueprint(query_main_blueprint)

In new file , add something like:

query_main = Blueprint('query_main', __name__)

-> Ensure that routes set up on this file follow this name


When changing to an established page to a new one, do something like this:

return redirect(url_for('query_main.home'))

Then, in your new file, insert something similar to below to render the template via the redirection above:

@query_main.route('/home')
def home():
    print("Made it to query_main.home() method")
    return render_template("home.html")


# Setup instructions for AWSCLI/Localstack testing
Run the followingon separate terminal

Run ‘aws –endpoint-url=http://127.0.0.1:4566 s3 ls’. This will establish the endpoint and list buckets (none are in place yet)
Run ‘aws –endpoint-url=http://127.0.0.1:4566b s3 mb s3://geojson-test’
Run ‘aws –endpoint-url=http://127.0.0.1:4566b s3 mb s3://wibl-test’
Run the same initial command to confirm both buckets have been created.

Go to the the wibl-python/wibl-frontend directory

Run ‘./createFile.sh’. This will fill the cloudGeojson/WiblFiles folders with 1000 test files a piece.

Run ‘./cloudFilesTest.sh’ to upload those files into their respective buckets.

(Optional) Run ‘aws --endpoint-url=http://127.0.0.1:4566 s3 ls s3://wibl-test --recursive --human-readable --summarize’ to confirm bucket has the appropriate files. Same for geojson-test.


Cloud setup complete!

# If you need to clear the manager for a clean setup:
Docker volumes contain databases that persist even if the instance is taken down.

Run ‘curl -X DELETE http://127.0.0.1:5000/wibl/all’ To clear any previous data on the WIBL manager endpoint.

Run 'curl -X DELETE http://127.0.0.1:5000/geojson/all' to clear any previous data on the GEOJSON manager endpoint.

These deletes will also clear whatever is present on the local S3 Buckets: client connection and object deletion code can be found in each respective manager endpoint, under the http DELETE routings.

For WIBL: wibl-2023-2024-cs-791-792/wibl-python/wibl-manager/wibl_manager/wibl_data.py

For geojson: wibl-2023-2024-cs-791-792/wibl-python/wibl-manager/wibl_manager/geojson_data.py

# To populate the manager with bucket entries:
Run ‘curl -X GET http://127.0.0.1:8000/setup’. This will hit an endpoint in flask (wibl-frontend/query_main.py, defined in the setupCloudData function) iterates through every object in both buckets, and will post/update them to the manager-side.
