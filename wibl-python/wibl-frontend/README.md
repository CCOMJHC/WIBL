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
docker-compose build
```

## Create superuser
```shell
docker-compose exec frontend bash
python manage.py createsuperuser
```

> Set the username to `admin`, password to whatever you can remember; e-mail address can be bogus.

## Collect static files
Generate the static files needed by the admin site:
```shell
docker-compose exec frontend bash
python manage.py collectstatic
```

> Note: You will then need to rebuild the frontend container using `docker-compose build`

## Create test user
```shell
docker-compose exec frontend bash
python manage.py shell
from django.contrib.auth.models import User
user=User.objects.create_user('foo', password='bar')
user.is_superuser=False
user.is_staff=False
user.save()
exit()
exit
```
