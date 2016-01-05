DESTDIR := ""
PREFIX := /usr/local
home = ${PREFIX}/share/transom

.PHONY: default
default: devel

.PHONY: help
help:
	@echo "clean          Clean up the source tree"
	@echo "build          Build the code"
	@echo "install        Install the code"
	@echo "test           Run tests"
	@echo "devel          Build, install, and smoke test in this checkout"

.PHONY: clean
clean:
	find python -type f -name \*.pyc -delete
	rm -rf build
	rm -rf install
	rm -rf output

.PHONY: build
build:
	mkdir -p build/bin
	scripts/configure-file bin/transom.in build/bin/transom transom_home ${home}

.PHONY: install
install: build
	scripts/install-files python ${DESTDIR}${home}/python \*.py
	install -d ${DESTDIR}${home}/resources
	install -m 644 resources/* ${DESTDIR}${home}/resources
	install -d ${DESTDIR}${PREFIX}/bin
	install -m 755 build/bin/transom ${DESTDIR}${PREFIX}/bin/transom

.PHONY: test
test: PREFIX := "${PWD}/install"
test: install
	${PREFIX}/bin/transom input output --verbose

.PHONY: devel
devel: PREFIX := "${PWD}/install"
devel: clean test
