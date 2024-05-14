aws --endpoint-url="http://localhost:4566" s3 sync "cloudWiblFiles" s3://wibl-test
aws --endpoint-url="http://localhost:4566" s3 sync "cloudGeoJsonFiles" s3://geojson-test

echo "File Upload Complete!"
