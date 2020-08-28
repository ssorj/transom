#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

.NOTPARALLEL:

DESTDIR := ""
PREFIX := ${HOME}/.local
INSTALLED_TRANSOM_HOME = ${PREFIX}/share/transom

export TRANSOM_HOME = ${CURDIR}/build/transom
export PATH := ${CURDIR}/build/bin:${PATH}
export PYTHONPATH := ${CURDIR}/python:${PYTHONPATH}

VERSION := $(shell cat VERSION.txt)

BIN_SOURCES := $(shell find bin -type f -name \*.in)
BIN_TARGETS := ${BIN_SOURCES:%.in=build/%}

FILE_SOURCES := $(shell find files -type f)
FILE_TARGETS := ${FILE_SOURCES:%=build/transom/%}

PYTHON_SOURCES := $(shell find python -type f -name \*.py)
PYTHON_TARGETS := ${PYTHON_SOURCES:%=build/transom/%}

.PHONY: default
default: build

.PHONY: help
help:
	@echo "build          Build the code"
	@echo "install        Install the code"
	@echo "clean          Clean up the source tree"
	@echo "test           Run the tests"

.PHONY: build
build: ${BIN_TARGETS} ${FILE_TARGETS} ${PYTHON_TARGETS} build/prefix.txt
	scripts/smoke-test

.PHONY: install
install: build
	scripts/install-files build/bin ${DESTDIR}$$(cat build/prefix.txt)/bin
	scripts/install-files build/transom ${DESTDIR}$$(cat build/prefix.txt)/share/transom

.PHONY: clean
clean:
	rm -rf build
	rm -rf qpid-site/output
	rm -rf python/__pycache__

.PHONY: test
test: build
	transom-test

.PHONY: render
render: build
	cd qpid-site && transom render --force config input output

# https://stackoverflow.com/questions/22475849/node-js-what-is-enospc-error-and-how-to-solve
# $ echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf && sudo sysctl -p
.PHONY: serve
serve: build
	cd qpid-site && transom render --force --serve 8080 config input output

# pip3 install --user py-spy
.PHONY: profile
profile: build
	cd qpid-site && py-spy record -o /tmp/profile.svg -- transom render --force config input output

.PHONY: check-links
check-links: build
	cd qpid-site && transom check-links config input output

.PHONY: check-files
check-files: build
	cd qpid-site && transom check-files config input output

build/prefix.txt:
	echo ${PREFIX} > build/prefix.txt

build/bin/%: bin/%.in
	scripts/configure-file -a transom_home=${INSTALLED_TRANSOM_HOME} $< $@

build/transom/python/transom/%: python/transom/% python/transom/common.py python/commandant.py python/plano.py
	@mkdir -p ${@D}
	cp $< $@

build/transom/python/%: python/%
	@mkdir -p ${@D}
	cp $< $@

build/transom/files/%: files/%
	@mkdir -p ${@D}
	cp $< $@

.PHONY: update-markdown2
update-markdown2:
	curl -sfo python/markdown2.py "https://raw.githubusercontent.com/trentm/python-markdown2/master/lib/markdown2.py"

.PHONY: update-%
update-%:
	curl -sfo python/$*.py "https://raw.githubusercontent.com/ssorj/$*/master/python/$*.py"
