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

# Qpid Packages

## Debian

Use `apt-get` to install Qpid and its dependencies.

To install the C++ broker and management tools:

    % apt-get install qpidd qpid-tools

To install the C++ and Python Messaging APIs:

    % apt-get install libqpidmessaging2-dev python-qpid

## Fedora

Use `yum` to install Qpid and its dependencies.

To install the C++ broker and management tools:

    % yum install qpid-cpp-server qpid-tools

To install the C++ and Python Messaging APIs:

    % yum install qpid-cpp-client-devel
    % yum install python-qpid

## Windows

A [Windows installer](http://www.riverace.com/qpid/downloads.htm) is
available from Riverace. It is built from the C++ and C# source
distributions.
