# Please keep the following in alphabetical order so it's easier to determine
# if something is in the list

# Find and eradicate all .pyc files, so they don't ruin everything
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
find $PROJECT_DIR -name "*.pyc" -delete

PACKAGES="nectar"

# Test Directories
TESTS="test/unit"

nosetests --with-coverage --cover-html --cover-erase --cover-package $PACKAGES $TESTS
