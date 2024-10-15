# WIBL Frontend
This directory contains a Django app and project for the WIBL Frontend application

## Running with `docker compose`
Use `docker compose up` to run while developing:
```shell
docker compose up --watch
```

> The `--watch` option will watch source code and rebuild/refresh containers when files are updated.

To re-build container images after major changes (e.g., addition of dependencies), run:
```shell
docker compose build
```

### Load test data into the manager 
Once the frontend is running via `docker compose`, you can load test data into the manager (so that the frontend will 
have some initial data to display/manipulate) by running:
```shell
docker compose exec manager /usr/src/wibl/load-test-data.bash
```

> Note: This script is idempotent so it can be run multiple times without causing problems. If you want to 
> reload test data, first stop `docker compose`, then run `docker compose down`, 
> `docker volume rm wibl-frontend_dbdata_mgr`, `docker compose build`, and then re-run `docker compose up` 
> and then the `load-test-data` script as above.

## Create superuser
```shell
docker compose exec frontend bash
python manage.py createsuperuser
```

> Set the username to `admin`, password to whatever you can remember; e-mail address can be bogus.

## Collect static files
You will need to run the Django `collectstatic` command at minimum the first time you
run `docker compose up` so that the static JS, CSS, and images for the Django admin site
are copied into the frontend container.

Likewise, if you add or edit static JS, CSS, or images for the frontend app, you will
also need to run `collectstatic`.

To run `collecstatic`, first make sure `docker compose up` is running, then run:
```shell
docker compose exec frontend bash
python manage.py collectstatic
```

The first command will open a `bash` shell in the running frontend container. The second
command runs `collectstatic`. Once you've done this, exit the bash shell running in the 
frontend container. Then, from your host, stop `docker compose up` then run:
```shell
docker compose build
docker compose up --watch
```

## Create test user
```shell
docker compose exec frontend bash
python manage.py shell
from django.contrib.auth.models import User
user=User.objects.create_user('foo', password='bar')
user.is_superuser=False
user.is_staff=False
user.save()
exit()
exit
```
