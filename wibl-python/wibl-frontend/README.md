# Public-facing frontend interface for monitoring WIBL processing

## Local development and testing
Build and run:
```shell
$ docker compose --env-file frontend.env up
```

Test /heartbeat endpoint:
```shell
$ curl 'http://127.0.0.1:8002/heartbeat'
200
```
