SOURCE_DIR=$PWD
BUILD_DIR=$SOURCE_DIR/build
INSTALL_DIR=$SOURCE_DIR/install

export SOURCE_DIR BUILD_DIR INSTALL_DIR

TRANSOM_HOME=$INSTALL_DIR/share/transom
TRANSOM_DEBUG="Hello, bugs"

export TRANSOM_HOME TRANSOM_DEBUG

PATH=$INSTALL_DIR/bin:$PATH

export PATH
