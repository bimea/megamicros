#! /bin/bash
# This script is used to push the package on the project git repository
# It will update the git with  a "update" commit.
# Usage: ./gitpush.sh

echo 'git push on repository...'
git add . && git commit -m "update" && git push

