.PHONY: default help build install clean devel

BUILD_DIR := build
DESTDIR := ""
PREFIX := /usr/local

default: devel

help:
	@echo "build          Build the code"
	@echo "install        Install the code"
	@echo "clean          Clean up the source tree"
	@echo "devel          Build and install for this development session"

build:
	mkdir -p ${BUILD_DIR}/bin

	scripts/configure-file bin/transom.in "${BUILD_DIR}/bin/transom" \
		"${PREFIX}/share/transom"

install: build
	scripts/install-python-code python \
		"${DESTDIR}${PREFIX}/share/transom/python"

	install -d "${DESTDIR}${PREFIX}/bin"
	install -m 755 "${BUILD_DIR}/bin/transom" "${DESTDIR}${PREFIX}/bin/transom"

clean:
	find python -type f -name \*.pyc -delete
	rm -rf build
	rm -rf install

devel: PREFIX := ${INSTALL_DIR}
devel: clean install
	transom
