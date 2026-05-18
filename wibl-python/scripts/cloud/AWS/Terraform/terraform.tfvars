region           = "us-east-2"
incoming_bucket_name  = "default-incoming-bucket"
staging_bucket_name   = "default-staging-bucket"
viz_bucket_name       = "default-viz-bucket"
static_bucket_name = "default-static-files-bucket"

conversion_lambda_name = "default-wibl-conversion-lambda"
conversion_start_lambda_name = "default-wibl-conversion-start-lambda"
viz_lambda_name = "default-wibl-viz-lambda"
validation_lambda_name = "default-wibl-validation-lambda"
submission_lambda_name = "default-wibl-submission-lambda"

conversion_topic_name = "default-wibl-conversion-topic"
validation_topic_name = "default-wibl-validation-topic"
submission_topic_name = "default-wibl-submission-topic"
submitted_topic_name = "default-wibl-submitted-topic"

conversion_lambda_role_name = "default-wibl-conversion-lambda-role"
conversion_start_lambda_role_name = "default-wibl-conversion-start-lambda-role"
validation_lambda_role_name = "default-wibl-validation-lambda-role"
submission_lambda_role_name = "default-wibl-submission-lambda-role"
viz_lambda_role_name = "default-wibl-viz-lambda-role"

map_name = "WIBLOpenLayersMap"

manager_db_name = "managerDB"
manager_db_size = "5"
manager_db_user = "postgres"
manager_db_password = "test_test"

DCDB_provider_id = "UNHJHC"
DCDB_test_url = "https://www.ngdc.noaa.gov/ingest-external/upload/csb/test/geojson/"
DCDB_prod_url = "https://www.ngdc.noaa.gov/ingest-external/upload/csb/geojson/"

# The name of the file in the "auth" folder that contains your DCDB provider auth string
auth_file_name = "default_auth.txt"

frontend_db_name = "frontendDB"
frontend_db_size = "5"
frontend_db_user = "postgres"
frontend_db_password = "test_test"

superuser_username = "foo"
superuser_password = "bar"

// 1 = debug mode is on, 0 = debug mode is off
debug_mode = 0
// Run the generate_secret.sh script to create a unique secret key value
frontend_secret_key = "default__test_dev_key__"

// Origin Secret, replace with a unique value to secure traffic between cloudfront and the frontend alb
// Run the generate_secret.sh again to create a new value
origin_secret = "default"

// 1 = Use the production DCDB URL, 0 = Use the test DCDB URL
DCDB_mode = 0

