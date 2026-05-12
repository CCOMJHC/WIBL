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
recommended. The site to do so is located [here](https://djecrety.ir/).
- origin_secret: This password phrase adds an optional extra level of security between the CloudFront module and the 
frontend's load balancer. 
- DCDB_provider_id: Replace with your given DCDB provider id.
- DCDB_mode: By default the test mode is active. To switch to using the production URL, set this variable to 1.

### 2. Building The Lambda Package
This step only works if `docker` is currently running on your system. Inside the outer `AWS` folder is a script called 
`build-lambda.sh`, run this script. Even if the script is successful, there may still be a lingering `build` or `package`
folder, pay these no mind and continue to the next step.

### 3. Building The System With Terraform
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

