# Terraform AWS Build Instructions

## Setup
The following software items must be installed and configured before continuing

- Docker
- AWS CLI
- Terraform

### 1. Change default configurations
Edit the `terraform.tfvars` file as needed. Due to the nature of the cloud, all AWS components must have name unique to
its region and type. Thus, the default names provided will most likely already be taken. 

#### Important Variables To Consider:
- region: Must be a valid AWS region code. Consider this list for available regions. [AWS_Region_List](https://docs.aws.amazon.com/global-infrastructure/latest/regions/aws-regions.html)
- auth_file_name: Like it describes in the configuration file, it must be set to a valid file name that exists in the 
`auth` folder. The easiest solution is to copy and paste your string into the `default_auth.txt` file.
- frontend_secret_key: Following the directions is the configuration file to generate a Django secret is highly 
recommended. The script is located [here](./generate_secret.sh)
- origin_secret: This password phrase adds an extra level of security between the CloudFront module and the 
frontend's load balancer. Run the generate_secret script again to create a new value.
- DCDB_provider_id: Replace with your given DCDB provider id.
- DCDB_mode: By default the test mode is active. To switch to using the production URL, set this variable to 1.

### 2. Building The Lambda Package
This step only works if `docker` is currently running on your system. Inside the outer `AWS` folder is a script called 
`build-lambda.sh`, run this script. Even if the script is successful, there may still be a lingering `build` or `package`
folder, pay these no mind and continue to the next step.

### 3. Bootstrapping Terraform
Terraform is able to modify and delete computing resources that were created using Terraform. To do this, Terraform must 
store state information about what resources have been created. This state information can be stored locally on a single 
compute. However, if the locally stored state information is lost, then you lose the ability to automatically update or 
delete the computing resources originally created by Terraform. To avoid this problem, Terraform state can be stored 
remotely in S3. In addition to providing a disaster recovery solution, storing state in S3 allows multiple 
people/computers to manage a WIBL upload-server created with Terraform, and to do so asynchronously, without having to
worry about each person's updates overwriting each other.

You can use the script terraform-bootstrap.bash to create an S3 bucket in which to store Terraform state. Before doing 
so, change the name of the bucket and state object key by editing terraform_state_bucket and terraform_state_key in 
terraform.tfvars.

Running terraform-bootstrap.bash will look something like this:

```
$ ./scripts/cloud/Terraform/aws/terraform-bootstrap.bash
CONTENT_ROOT: /Users/JANE_USER/repos/WIBL/UploadServer
Using AWS_TF_ROOT: /Users/JANE_USER/repos/WIBL/UploadServer/scripts/cloud/Terraform/aws
Using ARCHITECTURE: arm64
Using AWS_BUILD: aws-build
Using BUILD_DEST: /Users/JANE_USER/repos/WIBL/UploadServer/aws-build
Using CERTS_DEST: /Users/JANE_USER/repos/WIBL/UploadServer/aws-build/certs
Using WIBL_UPLOAD_BINARY: upload-server
Using WIBL_UPLOAD_BINARY_PATH: /Users/JANE_USER/repos/WIBL/UploadServer/aws-build/upload-server
Using ADD_LOGGER_BINARY: add-logger
Using ADD_LOGGER_BINARY_PATH: /Users/JANE_USER/repos/WIBL/UploadServer/aws-build/add-logger
Using WIBL_UPLOAD_CONFIG_PROTO: /Users/JANE_USER/repos/WIBL/UploadServer/scripts/cloud/Terraform/aws/config-aws.json.proto
Using WIBL_UPLOAD_CONFIG_PATH: /Users/JANE_USER/repos/WIBL/UploadServer/aws-build/config.json
Using AWS_PROFILE: wibl-upload-server
Using TF_VARS: /Users/JANE_USER/repos/WIBL/UploadServer/scripts/cloud/Terraform/aws/terraform.tfvars
Using WIBL_UPLOAD_SERVER_PORT: 443
Using AWS_REGION: us-east-2
Using TF_STATE_BUCKET: unhjhc-wibl-tf-state
Using TF_STATE_KEY: terraform/state/wibl-upload-server-deploy.tfstate
Using WIBL_UPLOAD_BUCKET_NAME: unhjhc-wibl-upload-server-incoming
Using WIBL_UPLOAD_SNS_TOPIC_NAME: unhjhc-wibl-upload-server-conversion
Using AWS_CLI: aws --profile wibl-upload-server --region us-east-2
Using AWS_ACCOUNT_NUMBER: XXXXXXXXXXXX
Using WIBL_UPLOAD_SNS_TOPIC_ARN: arn:aws:sns:us-east-2:XXXXXXXXXXXX:unhjhc-wibl-upload-server-conversion
Creating terraform state bucket unhjhc-wibl-tf-state in AWS region us-east-2...
{
    "Location": "http://unhjhc-wibl-tf-state.s3.amazonaws.com/"
}
Enabling bucket versioning in terraform state bucket unhjhc-wibl-tf-state...
Done.
```
### 4. Building The System With Terraform
This step also requires `docker` to work, so ensure it is running. First, run the `plan.sh` script inside the Terraform 
folder. This is where any you will be alerted of any misconfigured or missing variables. If script says "Plan: 125 to 
add, 0 to change, 0 to destroy." without returning any errors, run the next script `build.sh`. If you do experience any 
errors, you need to then run the `destroy.sh` script before you can attempt another build. 

#### IMPORTANT: The system can take upwards of 15 to 25 minutes to fully build or destroy.

### How To Tear Down The System
#### WARNING: This script destroys ALL resources, meaning all data put into the system will be unrecoverable.
To destroy the resources in the cloud, including all AWS and docker resources, run the `destroy.sh` script. 
The following resources tend to take longer to destroy than their counter-parts. 
- module.configure-manager-ecs.aws_internet_gateway.ig_public
- module.configure-manager-ecs.aws_cloudfront_distribution.frontend

This is mostly due to a bug with AWS's resource state management system. AWS believes select lambda functions are still 
running, which can often leave multiple components hanging on each other waiting for the other to be destroyed. If it 
seems like this might be the case, using ^c to cancel the script and rerunning it may solve the issue.

