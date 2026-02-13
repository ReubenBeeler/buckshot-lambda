#!/bin/bash

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
DIR=$(mktemp -d)
NAME='layer'

uv pip freeze > $DIR/requirements.txt

echo installing dependencies...
mkdir $DIR/$NAME
uv pip install -r $DIR/requirements.txt --target $DIR/$NAME

echo "unzipped size: $(du -sh --apparent-size $DIR/$NAME | awk {'print $1'})"

echo "zipping $NAME... (may take a while)"
cd $DIR
zip $SCRIPT_DIR/$NAME.zip -r $NAME >/dev/null

cd $SCRIPT_DIR
echo "zipped size: $(du -sh --apparent-size $NAME.zip | awk {'print $1'})"

rm -rf $DIR