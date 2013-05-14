#!/usr/bin/sh

# usage: ./make-tar-ball.sh <branch> <version>
# e.g.: ./make-tar-ball.sh master 0.90.0 -> python-nectar-0.90.0.tar.gz

BRANCH=$1
VERSION=$2
GIT=$(which git)

$GIT archive --format=tar.gz --prefix=python-nectar-$VERSION/ $BRANCH >python-nectar-$VERSION.tar.gz
