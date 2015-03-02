.PHONY: default help build install clean devel

DESTDIR := ""
PREFIX := /usr/local

default: devel

help:
	@echo "build          Build the code"
	@echo "install        Install the code"
	@echo "clean          Clean up the source tree"
	@echo "devel          Build and install for this development session"

build:
	mkdir -p build/bin

	scripts/configure-file bin/transom.in build/bin/transom \
		"${PREFIX}/share/transom"

install: build
	scripts/install-python-code python \
		"${DESTDIR}${PREFIX}/share/transom/python"

	install -d "${DESTDIR}${PREFIX}/share/transom/resources"
	install -m 644 resources/* "${DESTDIR}${PREFIX}/share/transom/resources"

	install -d "${DESTDIR}${PREFIX}/bin"
	install -m 755 build/bin/transom "${DESTDIR}${PREFIX}/bin/transom"

clean:
	find python -type f -name \*.pyc -delete
	rm -rf build
	rm -rf install

devel: PREFIX := "${PWD}/install"
devel: clean install
	transom --help >/dev/null
