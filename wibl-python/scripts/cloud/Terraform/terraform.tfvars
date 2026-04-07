region           = "us-east-2"
incoming_bucket_name  = "incoming-bucket-gt-test-1"
staging_bucket_name   = "staging-bucket-gt-test-1"
viz_bucket_name       = "viz-bucket-gt-test-1"
static_bucket_name = "gt-static-files-bucket"

conversion_lambda_name = "gt-conversion-lambda"
conversion_start_lambda_name = "gt-conversion-start-lambda"
conversion_topic_name = "gt-conversion-topic"
validation_lambda_name = "gt-validation-lambda"
validation_topic_name = "gt-validation-topic"
submission_lambda_name = "gt-submission-lambda"
submission_topic_name = "gt-submission-topic"
submitted_topic_name = "gt-submitted-topic"
viz_lambda_name = "gt-viz-lambda"
conversion_lambda_role_name = "gt-conversion-lambda-role"
conversion_start_lambda_role_name = "gt-conversion-start-lambda-role"
validation_lambda_role_name = "gt-validation-lambda-role"
submission_lambda_role_name = "gt-submission-lambda-role"
viz_lambda_role_name = "gt-viz-lambda-role"
map_name = "WIBLOpenLayersMap"
manager_db_name = "managerDB"
manager_db_size = "5"
manager_db_user = "postgres"
manager_db_password = "test_test"

DCDB_PROVIDER_ID = "UNHJHC"
DCDB_TEST_URL = "https://www.ngdc.noaa.gov/ingest-external/upload/csb/test/geojson/"
DCDB_PROD_URL = "https://www.ngdc.noaa.gov/ingest-external/upload/csb/geojson/"
# The name of the file in the "auth" folder that contains your DCDB provider auth string
auth_file_name = "test_auth.txt"

frontend_db_name = "frontendDB"
frontend_db_size = "5"
frontend_db_user = "postgres"
frontend_db_password = "test_test"

superuser_username = "foo"
superuser_password = "bar"

// 1 = debug mode is on, 0 = debug mode is off
debug_mode = 1
// Use this site to generate your own Django secret key, https://djecrety.ir/
frontend_secret_key = "default__test_dev_key__"

// Origin Secret, replace with a unique value to secure traffic between cloudfront and the frontend alb
origin_secret = "default"

// 1 = Use the production DCDB URL, 0 = Use the test DCDB URL
DCDB_mode = 0

