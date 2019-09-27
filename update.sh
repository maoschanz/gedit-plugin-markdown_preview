#!/bin/bash

git stash
git pull
./uninstall.sh
./install.sh

exit 0

