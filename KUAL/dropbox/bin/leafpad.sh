#!/bin/sh
EXTENSION=/mnt/us/extensions/leafpad
export HOME=${EXTENSION}/settings
export PATH=$PATH:${EXTENSION}/bin
cd ${EXTENSION}/notes
${EXTENSION}/bin/leafpad /mnt/us/extensions/dropbox/dropbox.cfg &