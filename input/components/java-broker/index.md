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

# Java Broker

A message broker written in Java that stores, routes, and forwards
messages using AMQP.

  || *Platforms* || JVM ||
  || *AMQP versions* || 1.0, 0-10, 0-9-1, 0-9, 0-8 ||
  || *Download* || [qpid-broker-@current-release@-bin.tar.gz](http://www.apache.org/dyn/closer.cgi/qpid/@current-release@/binaries/qpid-broker-@current-release@-bin.tar.gz) \[[ASC](http://www.apache.org/dist/qpid/@current-release@/binaries/qpid-broker-@current-release@-bin.tar.gz.asc), [MD5](http://www.apache.org/dist/qpid/@current-release@/binaries/qpid-broker-@current-release@-bin.tar.gz.md5), [SHA1](http://www.apache.org/dist/qpid/@current-release@/binaries/qpid-broker-@current-release@-bin.tar.gz.sha1)] ||
  || *Source location* ||  <http://svn.apache.org/repos/asf/qpid/trunk/qpid/java/> ||

## Features

<div class="two-column" markdown="1">

 - [JMS 1.1](http://www.oracle.com/technetwork/java/docs-136352.html) compliant
 - Speaks and translates among all versions of AMQP
 - [Management](@current-release-url@/java-broker/book/Java-Broker-Configuring-And-Managing.html) via JMX, REST, QMF, and web console
 - [Access control lists](@current-release-url@/java-broker/book/Java-Broker-Security-ACLs.html)
 - Flexible logging
 - Flow to disk
 - Header-based routing
 - Heartbeats
 - [High availability](@current-release-url@/java-broker/book/Java-Broker-High-Availability.html)
 - Message groups
 - [Pluggable persistence](@current-release-url@/java-broker/book/Java-Broker-Stores.html) supporting Derby, SQL, and BDB stores
 - [Pluggable authentication](@current-release-url@/java-broker/book/Java-Broker-Security.html#Java-Broker-Security-Authentication-Providers) supporting LDAP, Kerberos, and SSL client certificates
 - [Producer flow control](@current-release-url@/java-broker/book/Java-Broker-Runtime-Disk-Space-Management.html#Qpid-Producer-Flow-Control)
 - [Secure connection via SSL](@current-release-url@/java-broker/book/Java-Broker-Security-SSL.html)
 - Server-side selectors
 - [Specialized queuing](@current-release-url@/java-broker/book/Java-Broker-Queues.html) with last value queue, priority queue, and sorted queue
 - Threshold alerts
 - Transactions
 - [Undeliverable message handling](@current-release-url@/java-broker/book/Java-Broker-Runtime-Handling-Undeliverable-Messages.html)
 - [Virtual hosts](@current-release-url@/java-broker/book/Java-Broker-Virtual-Hosts.html)

</div>

## Documentation

This is the documentation for the current released version.  You can
find previous versions with our
[past releases](@site-url@/releases/index.html#past-releases).

<div class="two-column" markdown="1">

 - [Java broker book](@current-release-url@/java-broker/book/index.html)
 - [How to build Qpid Java](https://cwiki.apache.org/confluence/display/qpid/qpid+java+build+how+to)
 - [FAQ](https://cwiki.apache.org/confluence/display/qpid/qpid+java+faq)
 - [Design documents](https://cwiki.apache.org/confluence/display/qpid/java+broker+design)
 - [Qpid extensions to AMQP](https://cwiki.apache.org/confluence/display/qpid/qpid+extensions+to+amqp)
 - [More on the wiki](https://cwiki.apache.org/confluence/display/qpid/qpid+java+documentation)

</div>

## Issues

For more information about finding and reporting bugs, see
[Qpid issues](@site-url@/issues.html).

<div class="indent">
  <form id="jira-search-form">
    <input type="hidden" name="jql" value="project = QPID and component = 'Java Broker' and text ~ '{}' order by updatedDate desc"/>
    <input type="text" name="text"/>
    <button type="submit">Search</button>
  </form>
</div>

<div class="two-column" markdown="1">

 - [Open bugs](http://issues.apache.org/jira/issues/?jql=resolution+%3D+EMPTY+and+issuetype+%3D+%22Bug%22+and+component+%3D+%22Java+Broker%22+and+project+%3D+%22QPID%22)
 - [Fixed bugs](http://issues.apache.org/jira/issues/?jql=resolution+%3D+%22Fixed%22+and+issuetype+%3D+%22Bug%22+and+component+%3D+%22Java+Broker%22+and+project+%3D+%22QPID%22)
 - [Requested enhancements](http://issues.apache.org/jira/issues/?jql=resolution+%3D+EMPTY+and+issuetype+in+%28%22New+Feature%22%2C+%22Improvement%22%29+and+component+%3D+%22Java+Broker%22+and+project+%3D+%22QPID%22)
 - [Completed enhancements](http://issues.apache.org/jira/issues/?jql=resolution+%3D+%22Fixed%22+and+issuetype+in+%28%22New+Feature%22%2C+%22Improvement%22%29+and+component+%3D+%22Java+Broker%22+and+project+%3D+%22QPID%22)
 - [Report a bug](http://issues.apache.org/jira/secure/CreateIssueDetails!init.jspa?pid=12310520&issuetype=1&priority=3&summary=[Enter%20a%20brief%20description]&components=12311388)
 - [Request an enhancement](http://issues.apache.org/jira/secure/CreateIssueDetails!init.jspa?pid=12310520&issuetype=4&priority=3&summary=[Enter%20a%20brief%20description]&components=12311388)
 - [Jira summary page](http://issues.apache.org/jira/browse/QPID/component/12311388)

</div>
