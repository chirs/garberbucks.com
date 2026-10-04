#!/bin/bash
# Full rebuild-and-ship: data repos -> mongo -> postgres -> bert.
# Runs build/build.sh, then this repo's build.sh, then upload.sh, in order,
# stopping at the first failure.
set -e
cd "$(dirname "$0")"

../build/build.sh
./build.sh
./upload.sh
