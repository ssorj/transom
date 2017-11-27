DESTDIR := ""
PREFIX := ${HOME}/.local
TRANSOM_HOME = ${PREFIX}/share/transom

export PATH := ${PWD}/install/bin:${PATH}

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
	scripts/configure-file -a transom_home=${TRANSOM_HOME} bin/transom.in build/bin/transom

.PHONY: install
install: build
	scripts/install-files -n \*.py python ${DESTDIR}${TRANSOM_HOME}/python
	scripts/install-files files ${DESTDIR}${TRANSOM_HOME}/files
	scripts/install-files build/bin ${DESTDIR}${PREFIX}/bin

.PHONY: test
test: PREFIX := ${PWD}/install
test: install
	transom --help 1>/dev/null
	transom render --help 1>/dev/null
	transom render input output

.PHONY: devel
devel: PREFIX := ${PWD}/install
devel: clean test
