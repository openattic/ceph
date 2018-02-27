#!/usr/bin/env bash

# run from ./ or from ../
: ${MGR_DASHBOARD_V2_VIRTUALENV:=/tmp/mgr-dashboard_v2-virtualenv}
test -d dashboard_v2 && cd dashboard_v2

if [ -e tox.ini ]; then
    TOX_PATH=`readlink -f tox.ini`
else
    TOX_PATH=`readlink -f $(dirname $0)/tox.ini`
fi

if [ -z $CEPH_BUILD_DIR ]; then
    export CEPH_BUILD_DIR=$(dirname ${TOX_PATH})
fi

source ${MGR_DASHBOARD_V2_VIRTUALENV}/bin/activate
tox -c ${TOX_PATH}

