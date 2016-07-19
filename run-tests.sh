set -e

# Find and eradicate all .pyc files, so they don't ruin everything
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
find $PROJECT_DIR -name "*.pyc" -delete

PACKAGES="nectar"

# Test Directories
TESTS="test/unit"

python3-flake8 --config flake8.cfg .

nosetests-3.5 --with-coverage --cover-html --cover-erase --cover-package $PACKAGES $TESTS
