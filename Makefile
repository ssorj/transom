.PHONY: default help clean build install devel dist

DESTDIR := ""
PREFIX := /usr/local

default: devel

help:
	@echo "clean          Clean up the source tree"
	@echo "build          Build the code"
	@echo "install        Install the code"
	@echo "test           Run tests"
	@echo "devel          Clean, build, install, test"
	@echo "dist           Generate a release tarball"

clean:
	find python -type f -name \*.pyc -delete
	rm -rf build
	rm -rf install
	rm -rf output
	rm -rf dist

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

dist: VERSION := $(shell cat VERSION)
dist:
	mkdir -p dist
	git archive --prefix "transom-${VERSION}/" --output "dist/transom-${VERSION}.tar.gz" HEAD
