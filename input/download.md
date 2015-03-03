;;
;; Licensed to the Apache Software Foundation (ASF) under one
;; or more contributor license agreements.  See the NOTICE file
;; distributed with this work for additional information
;; regarding copyright ownership.  The ASF licenses this file
;; to you under the Apache License, Version 2.0 (the
;; "License"); you may not use this file except in compliance
;; with the License.  You may obtain a copy of the License at
;; 
;;   http://www.apache.org/licenses/LICENSE-2.0
;; 
;; Unless required by applicable law or agreed to in writing,
;; software distributed under the License is distributed on an
;; "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
;; KIND, either express or implied.  See the License for the
;; specific language governing permissions and limitations
;; under the License.
;;

# Download

*In addition to the source artefacts below, we offer
[Qpid packages](packages.html) and [Qpid via Maven](maven.html).*

Qpid's source artefacts are produced as part of our community release
process.  The downloads on this page are from our current releases,
@current-release-link@, @current-proton-release-link@, and
@current-dispatch-release-link@.  You can also see our
[past releases](@site-url@/releases/index.html#past-releases).

It's important to [verify the integrity](#verify-what-you-download) of
the files you download.

## Messaging APIs

| Content | Download | Verify |
| ------- | -------- | ------ |
| [AMQP Messenger](@site-url@/components/messenger/index.html) | [qpid-proton-@current-proton-release@.tar.gz](http://www.apache.org/dyn/closer.cgi/qpid/proton/@current-proton-release@/qpid-proton-@current-proton-release@.tar.gz) | [ASC](http://www.apache.org/dist/qpid/proton/@current-proton-release@/qpid-proton-@current-proton-release@.tar.gz.asc), [SHA1](http://www.apache.org/dist/qpid/proton/@current-proton-release@/SHA1SUM) |
| [AMQP Protocol Engine](@site-url@/components/messenger/index.html) | [qpid-proton-@current-proton-release@.tar.gz](http://www.apache.org/dyn/closer.cgi/qpid/proton/@current-proton-release@/qpid-proton-@current-proton-release@.tar.gz) | [ASC](http://www.apache.org/dist/qpid/proton/@current-proton-release@/qpid-proton-@current-proton-release@.tar.gz.asc), [SHA1](http://www.apache.org/dist/qpid/proton/@current-proton-release@/SHA1SUM) |
| [Qpid JCA](@site-url@/components/qpid-jca/index.html) | [qpid-java-@current-release@.tar.gz](http://www.apache.org/dyn/closer.cgi/qpid/@current-release@/qpid-java-@current-release@.tar.gz) | [ASC](http://www.apache.org/dist/qpid/@current-release@/qpid-java-@current-release@.tar.gz.asc), [MD5](http://www.apache.org/dist/qpid/@current-release@/qpid-java-@current-release@.tar.gz.md5), [SHA1](http://www.apache.org/dist/qpid/@current-release@/qpid-java-@current-release@.tar.gz.sha1) |
| [Qpid JMS](@site-url@/components/qpid-jms/index.html) (AMQP 0-10, 0-9-1, 0-9, 0-8) | [qpid-client-@current-release@-bin.tar.gz](http://www.apache.org/dyn/closer.cgi/qpid/@current-release@/binaries/qpid-client-@current-release@-bin.tar.gz)\* | [ASC](http://www.apache.org/dist/qpid/@current-release@/binaries/qpid-client-@current-release@-bin.tar.gz.asc), [MD5](http://www.apache.org/dist/qpid/@current-release@/binaries/qpid-client-@current-release@-bin.tar.gz.md5), [SHA1](http://www.apache.org/dist/qpid/@current-release@/binaries/qpid-client-@current-release@-bin.tar.gz.sha1) |
| [Qpid JMS](@site-url@/components/qpid-jms/index.html) (AMQP 1.0) | [qpid-amqp-1-0-client-jms-@current-release@-bin.tar.gz](http://www.apache.org/dyn/closer.cgi/qpid/@current-release@/binaries/qpid-amqp-1-0-client-jms-@current-release@-bin.tar.gz)\* | [ASC](http://www.apache.org/dist/qpid/@current-release@/binaries/qpid-amqp-1-0-client-jms-@current-release@-bin.tar.gz.asc), [MD5](http://www.apache.org/dist/qpid/@current-release@/binaries/qpid-amqp-1-0-client-jms-@current-release@-bin.tar.gz.md5), [SHA1](http://www.apache.org/dist/qpid/@current-release@/binaries/qpid-amqp-1-0-client-jms-@current-release@-bin.tar.gz.sha1) |
| [Qpid Messaging API](@site-url@/components/messaging-api/index.html) (C++, bindings) | [qpid-cpp-@current-release@.tar.gz](http://www.apache.org/dyn/closer.cgi/qpid/@current-release@/qpid-cpp-@current-release@.tar.gz) | [ASC](http://www.apache.org/dist/qpid/@current-release@/qpid-cpp-@current-release@.tar.gz.asc), [MD5](http://www.apache.org/dist/qpid/@current-release@/qpid-cpp-@current-release@.tar.gz.md5), [SHA1](http://www.apache.org/dist/qpid/@current-release@/qpid-cpp-@current-release@.tar.gz.sha1) |
| [Qpid Messaging API](@site-url@/components/messaging-api/index.html) (Python) | [qpid-python-@current-release@.tar.gz](http://www.apache.org/dyn/closer.cgi/qpid/@current-release@/qpid-python-@current-release@.tar.gz) | [ASC](http://www.apache.org/dist/qpid/@current-release@/qpid-python-@current-release@.tar.gz.asc), [MD5](http://www.apache.org/dist/qpid/@current-release@/qpid-python-@current-release@.tar.gz.md5), [SHA1](http://www.apache.org/dist/qpid/@current-release@/qpid-python-@current-release@.tar.gz.sha1) |

## Servers and tools

| Content | Download | Verify |
| ------- | -------- | ------ |
| [C++ broker](@site-url@/components/cpp-broker/index.html) | [qpid-cpp-@current-release@.tar.gz](http://www.apache.org/dyn/closer.cgi/qpid/@current-release@/qpid-cpp-@current-release@.tar.gz) | [ASC](http://www.apache.org/dist/qpid/@current-release@/qpid-cpp-@current-release@.tar.gz.asc), [MD5](http://www.apache.org/dist/qpid/@current-release@/qpid-cpp-@current-release@.tar.gz.md5), [SHA1](http://www.apache.org/dist/qpid/@current-release@/qpid-cpp-@current-release@.tar.gz.sha1) |
| [C++ broker](@site-url@/components/cpp-broker/index.html) (command-line tools) | [qpid-tools-@current-release@.tar.gz](http://www.apache.org/dyn/closer.cgi/qpid/@current-release@/qpid-tools-@current-release@.tar.gz) | [ASC](http://www.apache.org/dist/qpid/@current-release@/qpid-tools-@current-release@.tar.gz.asc), [MD5](http://www.apache.org/dist/qpid/@current-release@/qpid-tools-@current-release@.tar.gz.md5), [SHA1](http://www.apache.org/dist/qpid/@current-release@/qpid-tools-@current-release@.tar.gz.sha1) |
| [Java broker](@site-url@/components/java-broker/index.html) | [qpid-broker-@current-release@-bin.tar.gz](http://www.apache.org/dyn/closer.cgi/qpid/@current-release@/binaries/qpid-broker-@current-release@-bin.tar.gz)\* | [ASC](http://www.apache.org/dist/qpid/@current-release@/binaries/qpid-broker-@current-release@-bin.tar.gz.asc), [MD5](http://www.apache.org/dist/qpid/@current-release@/binaries/qpid-broker-@current-release@-bin.tar.gz.md5), [SHA1](http://www.apache.org/dist/qpid/@current-release@/binaries/qpid-broker-@current-release@-bin.tar.gz.sha1) |
| [QMF](@site-url@/components/qmf/index.html) | [qpid-qmf-@current-release@.tar.gz](http://www.apache.org/dyn/closer.cgi/qpid/@current-release@/qpid-qmf-@current-release@.tar.gz) | [ASC](http://www.apache.org/dist/qpid/@current-release@/qpid-qmf-@current-release@.tar.gz.asc), [MD5](http://www.apache.org/dist/qpid/@current-release@/qpid-qmf-@current-release@.tar.gz.md5), [SHA1](http://www.apache.org/dist/qpid/@current-release@/qpid-qmf-@current-release@.tar.gz.sha1) |
| [Dispatch router](@site-url@/components/dispatch-router/index.html) | [qpid-dispatch-@current-dispatch-release@.tar.gz](http://www.apache.org/dyn/closer.cgi/qpid/dispatch/@current-dispatch-release@/qpid-dispatch-@current-dispatch-release@.tar.gz) | [ASC](http://www.apache.org/dist/qpid/dispatch/@current-dispatch-release@/qpid-dispatch-@current-dispatch-release@.tar.gz.asc), [SHA1](http://www.apache.org/dist/qpid/dispatch/@current-dispatch-release@/SHA1SUM) |

\*These Java artefacts are released as compiled bytecode.  We also
offer the source as part of our
[Java source release](http://www.apache.org/dyn/closer.cgi/qpid/@current-release@/qpid-java-@current-release@.tar.gz)
\[[ASC](http://www.apache.org/dist/qpid/@current-release@/qpid-java-@current-release@.tar.gz.asc), [MD5](http://www.apache.org/dist/qpid/@current-release@/qpid-java-@current-release@.tar.gz.md5), [SHA1](http://www.apache.org/dist/qpid/@current-release@/qpid-java-@current-release@.tar.gz.sha1)].

## Verify what you download

It is essential that you verify the integrity of the downloaded files
using the ASC signatures, MD5 checksums, or SHA1 checksums.

The signatures can be verified using PGP or GPG. First download
the [`KEYS`](http://www.apache.org/dist/qpid/KEYS) file as well as the
`.asc` signature file for the relevant artefact. Make sure you get
these files from the relevant subdirectory of the
[main distribution directory](http://www.apache.org/dist/qpid/),
rather than from a mirror. Then verify the signatures using one of the
following sets of commands.

    % pgpk -a KEYS
    % pgpv qpid-@current-release@.tar.gz.asc

    % pgp -ka KEYS
    % pgp qpid-@current-release@.tar.gz.asc

    % gpg --import KEYS
    % gpg --verify qpid-@current-release@.tar.gz.asc

Alternatively, you can verify the MD5 or SHA1 checksums of the
files. Unix programs called `md5sum` and `sha1sum` (or `md5` and
`sha1`) are included in many unix distributions.  They are also
available as part of
[GNU Coreutils](http://www.gnu.org/software/coreutils/). For
Windows users, [FSUM](http://www.slavasoft.com/fsum/) supports MD5 and
SHA1. Ensure your generated checksum string matches the string
published in the `.md5` or `.sha1` file included with each release
artefact. Again, make sure you get this file from the relevant
subdirectory of the
[main distribution directory](http://www.apache.org/dist/qpid/),
rather than from a mirror.

## More information

 - [Qpid releases](@site-url@/releases/index.html)
 - [Qpid components](@site-url@/components/index.html)
