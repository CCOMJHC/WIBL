#!/bin/bash
set -eu -o pipefail

data_loaded_flag=/usr/src/wibl/test-data-loaded
manager_url='http://127.0.0.1:5000'

if [[ -f $data_loaded_flag ]]; then
  echo "Test already loaded."
else
  echo "Loading test data..."

  # Some WIBL files
  file_id='0A998589-D21F-4C16-9DC7-7316780E1DD0.wibl'
  curl -f -X 'POST' "${manager_url}/wibl/${file_id}" \
    -H 'Content-Type: application/json' \
  --data @-<<EOF
{
  "size": 1.0
}
EOF
  curl -f -X 'PUT' "${manager_url}/wibl/${file_id}" \
    -H 'Content-Type: application/json' \
  --data @-<<EOF
{
  "logger": "UNHJHC-wibl-2", "platform": "USCGC Healy",
  "observations": 100232, "soundings": 8023,
  "startTime": "2023-01-23T12:34:45.142",
  "endTime": "2023-01-24T01:45:23.012",
  "status": 0
}
EOF

  file_id='047EEFC3-7EEC-4FFD-816F-B6DB15E52297.wibl'
    curl -f -X 'POST' "${manager_url}/wibl/${file_id}" \
    -H 'Content-Type: application/json' \
  --data @-<<EOF
{
  "size": 2.3
}
EOF
  curl -f -X 'PUT' "${manager_url}/wibl/${file_id}" \
    -H 'Content-Type: application/json' \
  --data @-<<EOF
{
  "logger": "UNHJHC-wibl-1", "platform": "USCGC Healy",
  "observations": 200231, "soundings": 3028,
  "startTime": "2023-02-23T12:43:45.142",
  "endTime": "2023-02-24T01:54:23.012",
  "status": 1
}
EOF

  file_id='98C4ED55-190C-40B5-99DF-CC77E1531D1A.wibl'
  curl -f -X 'POST' "${manager_url}/wibl/${file_id}" \
    -H 'Content-Type: application/json' \
  --data @-<<EOF
{
  "size": 1.7
}
EOF
  curl -f -X 'PUT' "${manager_url}/wibl/${file_id}" \
    -H 'Content-Type: application/json' \
  --data @-<<EOF
{
  "logger": "UNHJHC-wibl-2", "platform": "USCGC Coastal",
  "observations": 300230, "soundings": 4027,
  "startTime": "2023-03-23T12:44:45.142",
  "endTime": "2023-03-24T01:53:23.012",
  "status": 1
}
EOF

  file_id='1A82E896-C571-4F60-97D5-A4FEE43E2B9F.wibl'
  curl -f -X 'POST' "${manager_url}/wibl/${file_id}" \
    -H 'Content-Type: application/json' \
  --data @-<<EOF
{
  "size": 0.9
}
EOF
  curl -f -X 'PUT' "${manager_url}/wibl/${file_id}" \
    -H 'Content-Type: application/json' \
  --data @-<<EOF
{
  "logger": "UNHJHC-wibl-1", "platform": "USCGC Coastal",
  "observations": 999999, "soundings": 99999,
  "startTime": "2023-03-23T12:44:45.142",
  "endTime": "2023-03-24T01:53:23.012",
  "status": 2
}
EOF

  # Some GeoJSON files corresponding to WIBL files with status PROCESSING_SUCCESSFUL
  file_id='047EEFC3-7EEC-4FFD-816F-B6DB15E52297.geojson'
  curl -f -X 'POST' "${manager_url}/geojson/${file_id}" \
    -H 'Content-Type: application/json' \
  --data @-<<EOF
{
  "size": 5.4
}
EOF
  curl -f -X 'PUT' "${manager_url}/geojson/${file_id}" \
    -H 'Content-Type: application/json' \
  --data @-<<EOF
{
  "soundings": 1514,
  "status": 1
}
EOF

  file_id='98C4ED55-190C-40B5-99DF-CC77E1531D1A.geojson'
  curl -f -X 'POST' "${manager_url}/geojson/${file_id}" \
    -H 'Content-Type: application/json' \
  --data @-<<EOF
{
  "size": 4.5
}
EOF
  curl -f -X 'PUT' "${manager_url}/geojson/${file_id}" \
    -H 'Content-Type: application/json' \
  --data @-<<EOF
{
  "soundings": 2013,
  "status": 1
}
EOF

  touch $data_loaded_flag
  echo "Finished loading test data."
fi
