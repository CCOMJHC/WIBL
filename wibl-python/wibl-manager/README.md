# Management interface for monitoring WIBL processing

## Local development and testing
Build and run:
```shell
$ docker compose up --watch
```

Test /heartbeat endpoint:
```shell
$ curl 'http://127.0.0.1:6080/heartbeat'
200
```

Test /wibl endpoint:
```shell
$ curl 'http://127.0.0.1:6080/wibl/all'
[]
```

Load test data:
```shell
$ docker compose exec manager /usr/src/wibl/load-test-data.bash
```

Test /wibl and /geojson endpoints:
```shell
$ curl -s 'http://127.0.0.1:6080/wibl/all' | jq .
[
  {
    "fileid": "0A998589-D21F-4C16-9DC7-7316780E1DD0.wibl",
    "processtime": "2024-10-10T18:08:08.429293+00:00",
    "updatetime": "Unknown",
    "notifytime": "Unknown",
    "logger": "Unknown",
    "platform": "Unknown",
    "size": 1.0,
    "observations": -1,
    "soundings": -1,
    "starttime": "Unknown",
    "endtime": "Unknown",
    "status": 0,
    "messages": ""
  },
  {
    "fileid": "047EEFC3-7EEC-4FFD-816F-B6DB15E52297.wibl",
    "processtime": "2024-10-10T18:08:08.444277+00:00",
    "updatetime": "Unknown",
    "notifytime": "Unknown",
    "logger": "Unknown",
    "platform": "Unknown",
    "size": 2.3,
    "observations": -1,
    "soundings": -1,
    "starttime": "Unknown",
    "endtime": "Unknown",
    "status": 0,
    "messages": ""
  },
  {
    "fileid": "98C4ED55-190C-40B5-99DF-CC77E1531D1A.wibl",
    "processtime": "2024-10-10T18:08:08.451439+00:00",
    "updatetime": "Unknown",
    "notifytime": "Unknown",
    "logger": "Unknown",
    "platform": "Unknown",
    "size": 1.7,
    "observations": -1,
    "soundings": -1,
    "starttime": "Unknown",
    "endtime": "Unknown",
    "status": 0,
    "messages": ""
  },
  {
    "fileid": "1A82E896-C571-4F60-97D5-A4FEE43E2B9F.wibl",
    "processtime": "2024-10-10T18:08:08.457781+00:00",
    "updatetime": "Unknown",
    "notifytime": "Unknown",
    "logger": "Unknown",
    "platform": "Unknown",
    "size": 0.9,
    "observations": -1,
    "soundings": -1,
    "starttime": "Unknown",
    "endtime": "Unknown",
    "status": 0,
    "messages": ""
  }
]
$ curl -s 'http://127.0.0.1:6080/geojson/all' | jq .
[
  {
    "fileid": "047EEFC3-7EEC-4FFD-816F-B6DB15E52297.geojson",
    "uploadtime": "2024-10-10T17:59:05.625058+00:00",
    "updatetime": "2024-10-10T18:11:20.682855+00:00",
    "notifytime": "Unknown",
    "logger": "Unknown",
    "size": 5.4,
    "soundings": 1514,
    "status": 1,
    "messages": null
  },
  {
    "fileid": "98C4ED55-190C-40B5-99DF-CC77E1531D1A.geojson",
    "uploadtime": "2024-10-10T17:59:05.633163+00:00",
    "updatetime": "2024-10-10T18:11:20.690761+00:00",
    "notifytime": "Unknown",
    "logger": "Unknown",
    "size": 4.5,
    "soundings": 2013,
    "status": 1,
    "messages": null
  }
]
```

## Testing
Run tests against WIBL manager running within Docker container:
```shell
$ ./manager_test.sh
```
