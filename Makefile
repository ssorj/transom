.PHONY: default help build install clean devel

DESTDIR := ""
PREFIX := /usr/local

default: devel

help:
	@echo "clean          Clean up the source tree"
	@echo "build          Build the code"
	@echo "install        Install the code"
	@echo "test           Run tests"
	@echo "devel          Clean, build, install, test"

clean:
	find python -type f -name \*.pyc -delete
	rm -rf build
	rm -rf install
	rm -rf output

build:
	mkdir -p build/bin

	scripts/configure-file bin/transom.in build/bin/transom \
		transom_home "${PREFIX}/share/transom"

install: build
	scripts/install-files python "${DESTDIR}${PREFIX}/share/transom/python" \*.py

	install -d "${DESTDIR}${PREFIX}/share/transom/resources"
	install -m 644 resources/* "${DESTDIR}${PREFIX}/share/transom/resources"

	install -d "${DESTDIR}${PREFIX}/bin"
	install -m 755 build/bin/transom "${DESTDIR}${PREFIX}/bin/transom"

test: install
	transom input output

devel: PREFIX := "${PWD}/install"
devel: clean test
