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

# C++ Broker

A message broker written in C++ that stores, routes, and forwards
messages using AMQP.

  || *Platforms* || Linux, Windows ||
  || *AMQP versions* || 1.0, 0-10 ||
  || *Download* || [qpid-cpp-@current-release@.tar.gz](http://www.apache.org/dyn/closer.cgi/qpid/@current-release@/qpid-cpp-@current-release@.tar.gz) \[[ASC](http://www.apache.org/dist/qpid/@current-release@/qpid-cpp-@current-release@.tar.gz.asc), [MD5](http://www.apache.org/dist/qpid/@current-release@/qpid-cpp-@current-release@.tar.gz.md5), [SHA1](http://www.apache.org/dist/qpid/@current-release@/qpid-cpp-@current-release@.tar.gz.sha1)\], [qpid-tools-@current-release@.tar.gz](http://www.apache.org/dyn/closer.cgi/qpid/@current-release@/qpid-tools-@current-release@.tar.gz) \[[ASC](http://www.apache.org/dist/qpid/@current-release@/qpid-tools-@current-release@.tar.gz.asc), [MD5](http://www.apache.org/dist/qpid/@current-release@/qpid-tools-@current-release@.tar.gz.md5), [SHA1](http://www.apache.org/dist/qpid/@current-release@/qpid-tools-@current-release@.tar.gz.sha1)\] ||
  || *Source location* ||  <http://svn.apache.org/repos/asf/qpid/trunk/qpid/cpp/>, <http://svn.apache.org/repos/asf/qpid/trunk/qpid/tools/> ||

## Features

<div class="two-column" markdown="1">

 - Speaks and translates between AMQP 1.0 and 0-10
 - [Management](@current-release-url@/cpp-broker/book/chapter-Managing-CPP-Broker.html#section-Managing-CPP-Broker) via [QMF](@site-url@/components/qmf/index.html)
 - Access control lists
 - [Federation](@current-release-url@/cpp-broker/book/chap-Messaging_User_Guide-Broker_Federation.html)
 - Flexible logging
 - Header-based routing
 - Heartbeats
 - [High availability](@current-release-url@/cpp-broker/book/chapter-ha.html)
 - [Message groups](@current-release-url@/cpp-broker/book/Using-message-groups.html)
 - Message TTLs and arrival timestamps
 - Pluggable persistence
 - [Pluggable authentication via SASL](@current-release-url@/cpp-broker/book/chap-Messaging_User_Guide-Security.html)
 - [Producer flow control](@current-release-url@/cpp-broker/book/producer-flow-control.html)
 - [Queue replication](@current-release-url@/cpp-broker/book/ha-queue-replication.html)
 - Resource limits
 - Secure connection via SSL
 - [Server-side selectors](https://issues.apache.org/jira/browse/QPID-4558?focusedCommentId=13592659&page=com.atlassian.jira.plugin.system.issuetabpanels:comment-tabpanel#comment-13592659)
 - Specialized queueing with [last value queue](@current-release-url@/cpp-broker/book/ch01s06.html), priority queue, and ring queue
 - [Threshold alerts](https://issues.apache.org/jira/browse/QPID-3002)
 - Transactions
 - Undeliverable message handling

</div>

## Documentation

This is the documentation for the current released version.  You can
find previous versions with our
[past releases](@site-url@/releases/index.html#past-releases).

<div class="two-column" markdown="1">

 - [C++ broker book](@current-release-url@/cpp-broker/book/index.html)
 - [Managing the C++ broker](@current-release-url@/cpp-broker/book/chapter-Managing-CPP-Broker.html#section-Managing-CPP-Broker)
 - [Installing Qpid C++](http://svn.apache.org/repos/asf/qpid/tags/@current-release@/qpid/cpp/INSTALL)
 - [Qpid extensions to AMQP](https://cwiki.apache.org/confluence/display/qpid/qpid+extensions+to+amqp)

</div>

## Issues

For more information about finding and reporting bugs, see
[Qpid issues](@site-url@/issues.html).

<div class="indent">
  <form id="jira-search-form">
    <input type="hidden" name="jql" value="project = QPID and component in ('C++ Broker', 'Python Tools') and text ~ '{}' order by updatedDate desc"/>
    <input type="text" name="text"/>
    <button type="submit">Search</button>
  </form>
</div>

<div class="two-column" markdown="1">

 - [Open bugs](https://issues.apache.org/jira/issues/?jql=resolution%20%3D%20EMPTY%20and%20issuetype%20%3D%20%22Bug%22%20and%20component%20in%20\(%22C%2B%2B%20Broker%22%2C%20%22Python%20Tools%22\)%20and%20project%20%3D%20%22QPID%22)
 - [Fixed bugs](https://issues.apache.org/jira/issues/?jql=resolution%20%3D%20Fixed%20and%20issuetype%20%3D%20%22Bug%22%20and%20component%20in%20\(%22C%2B%2B%20Broker%22%2C%20%22Python%20Tools%22\)%20and%20project%20%3D%20%22QPID%22)
 - [Requested enhancements](https://issues.apache.org/jira/issues/?jql=resolution%20%3D%20EMPTY%20and%20issuetype%20in%20\(%22New%20Feature%22%2C%20%22Improvement%22\)%20and%20component%20in%20\(%22C%2B%2B%20Broker%22%2C%20%22Python%20Tools%22\)%20and%20project%20%3D%20%22QPID%22)
 - [Completed enhancements](https://issues.apache.org/jira/issues/?jql=resolution%20%3D%20Fixed%20and%20issuetype%20in%20\(%22New%20Feature%22%2C%20%22Improvement%22\)%20and%20component%20in%20\(%22C%2B%2B%20Broker%22%2C%20%22Python%20Tools%22\)%20and%20project%20%3D%20%22QPID%22)
 - [Report a bug](http://issues.apache.org/jira/secure/CreateIssueDetails!init.jspa?pid=12310520&issuetype=1&priority=3&summary=[Enter%20a%20brief%20description]&components=12311395)
 - [Request an enhancement](http://issues.apache.org/jira/secure/CreateIssueDetails!init.jspa?pid=12310520&issuetype=4&priority=3&summary=[Enter%20a%20brief%20description]&components=12311395)
 - [Jira summary page](http://issues.apache.org/jira/browse/QPID/component/12311395)

</div>
