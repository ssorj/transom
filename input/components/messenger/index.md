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

# AMQP Messenger

AMQP Messenger offers a simple but powerful programming model.
Connection management happens under the covers, leaving you to focus
on your application.

The AMQP Messenger API is part of the
[Qpid Proton](@site-url@/proton/index.html) toolkit for making any
application speak AMQP.

  || *Languages* || C, Java, Perl, PHP, Python, Ruby ||
  || *Platforms* || Linux, OS X, JVM ||
  || *AMQP versions* || 1.0 ||
  || *Download* || [qpid-proton-@current-proton-release@.tar.gz](http://www.apache.org/dyn/closer.cgi/qpid/proton/@current-proton-release@/qpid-proton-@current-proton-release@.tar.gz) \[[ASC](http://www.apache.org/dist/qpid/proton/@current-proton-release@/qpid-proton-@current-proton-release@.tar.gz.asc), [SHA1](http://www.apache.org/dist/qpid/proton/@current-proton-release@/SHA1SUM)] ||
  || *Source location* ||  <http://svn.apache.org/repos/asf/qpid/proton/trunk/> ||

## Features

<div class="two-column" markdown="1">

 - Point-to-point and brokered messaging
 - C-based and pure-Java implementations
 - Secure connection via SSL
 - Seamless disconnected operation
 - Converts AMQP data types to language-native types

</div>

## Documentation

This is the documentation for the current released version.  You can
find previous versions with our
[past releases](@site-url@/releases/index.html#past-releases).

<div class="two-column" markdown="1">

 - [C API reference](@current-proton-release-url@/protocol-engine/c/api/messenger_8h.html)
 - [C examples](@current-proton-release-url@/messenger/c/examples/index.html)
 - [Java API reference](@current-proton-release-url@/protocol-engine/java/api/org/apache/qpid/proton/messenger/Messenger.html)
 - [Perl examples](@current-proton-release-url@/messenger/perl/examples/index.html)
 - [PHP examples](@current-proton-release-url@/messenger/php/examples/index.html)
 - [Python API reference](@current-proton-release-url@/protocol-engine/python/api/proton.Messenger-class.html)
 - [Python examples](@current-proton-release-url@/messenger/python/examples/index.html)
 - [Ruby examples](@current-proton-release-url@/messenger/ruby/examples/index.html)
 - [Ruby example applications](https://github.com/mcpierce/qpid-ruby-examples)
 - [Installing Qpid Proton](http://svn.apache.org/repos/asf/qpid/proton/tags/@current-proton-release@/README)

</div>

## Issues

For more information about finding and reporting bugs, see
[Qpid issues](@site-url@/issues.html).

<div class="indent">
  <form id="jira-search-form">
    <input type="hidden" name="jql" value="project = PROTON and text ~ '{}' order by updatedDate desc"/>
    <input type="text" name="text"/>
    <button type="submit">Search</button>
  </form>
</div>

<div class="two-column" markdown="1">

 - [Open bugs](http://issues.apache.org/jira/issues/?jql=resolution+%3D+EMPTY+and+issuetype+%3D+%22Bug%22+and+project+%3D+%22PROTON%22)
 - [Fixed bugs](http://issues.apache.org/jira/issues/?jql=resolution+%3D+%22Fixed%22+and+issuetype+%3D+%22Bug%22+and+project+%3D+%22PROTON%22)
 - [Requested enhancements](http://issues.apache.org/jira/issues/?jql=resolution+%3D+EMPTY+and+issuetype+in+%28%22New+Feature%22%2C+%22Improvement%22%29+and+project+%3D+%22PROTON%22)
 - [Completed enhancements](http://issues.apache.org/jira/issues/?jql=resolution+%3D+%22Fixed%22+and+issuetype+in+%28%22New+Feature%22%2C+%22Improvement%22%29+and+project+%3D+%22PROTON%22)
 - [Report a bug](http://issues.apache.org/jira/secure/CreateIssueDetails!init.jspa?pid=12313720&issuetype=1&priority=3&summary=[Enter%20a%20brief%20description])
 - [Request an enhancement](http://issues.apache.org/jira/secure/CreateIssueDetails!init.jspa?pid=12313720&issuetype=4&priority=3&summary=[Enter%20a%20brief%20description])
 - [Jira summary page](http://issues.apache.org/jira/browse/PROTON)

</div>
