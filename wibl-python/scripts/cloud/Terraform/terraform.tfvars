region           = "us-east-2"
incoming_bucket_name  = "incoming-bucket-gt-test-1"
staging_bucket_name   = "staging-bucket-gt-test-1"
viz_bucket_name       = "viz-bucket-gt-test-1"
static_bucket_name = "gt-static-files-bucket"

conversion_lambda_name = "gt-conversion-lambda"
conversion_start_lambda_name = "gt-conversion-start-lambda"
validation_lambda_name = "gt-validation-lambda"
submission_lambda_name = "gt-submission-lambda"
viz_lambda_name = "gt-viz-lambda"
conversion_lambda_role_name = "gt-conversion-lambda-role"
conversion_start_lambda_role_name = "gt-conversion-start-lambda-role"
validation_lambda_role_name = "gt-validation-lambda-role"
submission_lambda_role_name = "gt-submission-lambda-role"
viz_lambda_role_name = "gt-viz-lambda-role"

manager_db_name = "managerDB"
manager_db_size = "5"
manager_db_user = "postgres"
manager_db_password = "test_test"

frontend_db_name = "frontendDB"
frontend_db_size = "5"
frontend_db_user = "postgres"
frontend_db_password = "test_test"

superuser_username = "foo"
superuser_password = "bar"

// What the frontend domain name will be, so the default site is "ccomwibltest.xyz"
// Uses the domain extension .xyz because it is the cheapest
domain_host_name = "ccomwibltest"


// 1 = debug mode is on, 0 = debug mode is off
debug_mode = 1
// Use this site to generate your own key, https://djecrety.ir/
frontend_secret_key = "default__test_dev_key__"
