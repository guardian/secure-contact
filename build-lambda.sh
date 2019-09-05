#!/bin/bash

set -ev

APP=secure-contact-lambda
PROJECT_NAME=InfoSec::${APP}

if [[ -z ${BUILD_NUMBER} ]]; then
  BUILD_NUMBER=0
fi

if [[ -z ${BUILD_VCS_NUMBER} ]]; then
  BUILD_VCS_NUMBER=unknown
fi

if [[ -z ${BRANCH_NAME} ]]; then
  BRANCH_NAME=manual
fi

BUILD_START_DATE=$(date +"%Y-%m-%dT%H:%M:%S.000Z")

# Check if the target directory exists and delete it if so
# -d is a operator to test if the given directory exists or not
[ -d target ] && rm -rf target
mkdir -p target/packages
mkdir -p target/lambda

# Download required python packages so we can bundle them
pip install --target target/packages -r requirements.txt

# archive entire directory and subdirectories using maximum compression
cd target/packages
zip -r9 $OLDPWD/target/lambda/${APP}.zip .
cd $OLDPWD

zip -gr target/lambda/${APP}.zip static
zip -gr target/lambda/${APP}.zip templates
zip -g target/lambda/${APP}.zip pgp_listing.py
zip -g target/lambda/${APP}.zip pgp_manager.py

# Create build.json containing RiffRaff metadata
cat >build.json << EOF
{
   "projectName":"${PROJECT_NAME}",
   "buildNumber":"${BUILD_NUMBER}",
   "startTime":"${BUILD_START_DATE}",
   "revision":"${BUILD_VCS_NUMBER}",
   "vcsURL":"git@github.com:guardian/secure-contact.git",
   "branch":"${BRANCH_NAME}"
}
EOF

# upload results of the above to riff-raff artifact bucket
# the resulting structure within the build directory should be:
# |-- riff-raff.yaml
# |-- build.json
# |-- cloudformation
# |   |-- secure-contact-lambda.yaml
# |-- lambda
# |   |-- secure-contact-lambda.zip
function upload() {
	aws s3 cp --acl bucket-owner-full-control --region=eu-west-1 $1 $2
}

upload riff-raff.yaml s3://riffraff-artifact/${PROJECT_NAME}/${BUILD_NUMBER}/riff-raff.yaml
upload cloudformation/${APP}.yaml s3://riffraff-artifact/${PROJECT_NAME}/${BUILD_NUMBER}/cloudformation/${APP}.yaml
upload target/lambda/${APP}.zip s3://riffraff-artifact/${PROJECT_NAME}/${BUILD_NUMBER}/
# upload build.json last to avoid any potential race conditions
upload build.json s3://riffraff-builds/${PROJECT_NAME}/${BUILD_NUMBER}/build.json

rm build.json