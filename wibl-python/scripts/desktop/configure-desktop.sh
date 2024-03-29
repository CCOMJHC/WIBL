#!/bin/bash
#
# This configures the parameter file for desktop use of the software (where you
# can't have environment variables for the parameters used in the code).

source configuration-parameters.sh

cat >${CONFIG_FILE_DIR}/configure.json <<-HERE
{
    "provider_id":          "${DCDB_PROVIDER_ID}",
    "staging_bucket":       "${STAGING_BUCKET}",
    "verbose":              true,
    "elapsed_time_width":   32,
    "fault_limit":          10,
    "upload_point":         "${DCDB_UPLOAD_URL}",
    "management_url":       "${MANAGEMENT_URL}",
    "notification": {
        "created":      "${PROVIDER_PREFIX}-wibl-${NOTE_CREATED}",
        "converted":    "${PROVIDER_PREFIX}-wibl-${NOTE_CONVERTED}",
        "validated":    "${PROVIDER_PREFIX}-wibl-${NOTE_VALIDATED}",
        "uploaded":     "${PROVIDER_PREFIX}-wibl-${NOTE_UPLOADED}"
    },
    "local":                true
}
HERE
