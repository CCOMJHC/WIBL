# Management interface for monitoring WIBL processing

## Local development and testing
Build and run:
```shell
$ docker compose --env-file manager.env up
```

Test /heartbeat endpoint:
```shell
$ curl 'http://127.0.0.1:8001/heartbeat'
200
```

Test /wibl endpoint:
```shell
$ curl 'http://127.0.0.1:8001/wibl/all'
{"message": "That WIBL file does not exist."}
```

Run tests against WIBL manager running within Docker container:
```shell
$ ./manager_test.sh
```
