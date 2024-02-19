# Public-facing frontend interface for monitoring WIBL processing

## Local development and testing
Build and run:
```shell
$ docker compose --env-file frontend_test.env up
```

Test /heartbeat endpoint:
```shell
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



