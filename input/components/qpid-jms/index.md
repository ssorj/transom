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

# Qpid JMS

A [Java Message
Service](http://en.wikipedia.org/wiki/Java_Message_Service) 1.1
implementation that speaks all versions of AMQP.

  || *Languages* || Java ||
  || *Platforms* || JVM ||
  || *AMQP versions* || 1.0\*, 0-10, 0-9-1, 0-9, 0-8 ||
  || *Downloads* || AMQP 0-10, 0-9-1, 0-9, 0-8: [qpid-client-@current-release@-bin.tar.gz](http://www.apache.org/dyn/closer.cgi/qpid/@current-release@/binaries/qpid-client-@current-release@-bin.tar.gz) \[[ASC](http://www.apache.org/dist/qpid/@current-release@/binaries/qpid-client-@current-release@-bin.tar.gz.asc), [MD5](http://www.apache.org/dist/qpid/@current-release@/binaries/qpid-client-@current-release@-bin.tar.gz.md5), [SHA1](http://www.apache.org/dist/qpid/@current-release@/binaries/qpid-client-@current-release@-bin.tar.gz.sha1)],<br/>AMQP 1.0: [qpid-amqp-1-0-client-jms-@current-release@-bin.tar.gz](http://www.apache.org/dyn/closer.cgi/qpid/@current-release@/binaries/qpid-amqp-1-0-client-jms-@current-release@-bin.tar.gz) \[[ASC](http://www.apache.org/dist/qpid/@current-release@/binaries/qpid-amqp-1-0-client-jms-@current-release@-bin.tar.gz.asc), [MD5](http://www.apache.org/dist/qpid/@current-release@/binaries/qpid-amqp-1-0-client-jms-@current-release@-bin.tar.gz.md5), [SHA1](http://www.apache.org/dist/qpid/@current-release@/binaries/qpid-amqp-1-0-client-jms-@current-release@-bin.tar.gz.sha1)] ||
  || *Source location* ||  <http://svn.apache.org/repos/asf/qpid/trunk/qpid/java/> ||

\*1.0 support is offered in an implementation distinct from that of
older protocol versions.

## Features

<div class="two-column" markdown="1">

 - [JMS 1.1](http://www.oracle.com/technetwork/java/docs-136352.html) compliant
 - Speaks and translates among many versions of AMQP
 - Pure-Java implementation
 - Flow control
 - Pluggable authentication supporting LDAP, Kerberos, and SSL certificates
 - Secure connection via SSL
 - Transactions
 - [Flexible logging](@current-release-url@/programming/book/section-JMS-Logging.html)
 - Failover
 - Heartbeats

</div>

## Documentation

This is the documentation for the current released versions.  You can
find previous versions with our
[past releases](@site-url@/releases/index.html#past-releases).

<div class="two-column" markdown="1">

 - [API reference](http://docs.oracle.com/javaee/1.4/api/javax/jms/package-summary.html)
 - [How to build Qpid Java](https://cwiki.apache.org/confluence/display/qpid/qpid+java+build+how+to)
 - [Using the Qpid JMS client (AMQP 0-10)](@current-release-url@/programming/book/QpidJMS.html)
 - [Using the Qpid JMS client (AMQP 0-9-1, 0-9, 0-8)](@current-release-url@/jms-client-0-8/book/index.html)
 - [Examples (AMQP 1.0)](http://svn.apache.org/repos/asf/qpid/branches/@current-release@/qpid/java/amqp-1-0-client-jms/example)
 - [Examples (AMQP 0-10)](@current-release-url@/qpid-jms/examples/index.html)
 - [Examples (AMQP 0-9-1, 0-9, 0-8)](@current-release-url@/jms-client-0-8/book/JMS-Client-0-8-Examples.html)

</div>

## Issues

For more information about finding and reporting bugs, see
[Qpid issues](@site-url@/issues.html).

<div class="indent">
  <form id="jira-search-form">
    <input type="hidden" name="jql" value="project = QPID and component = 'Java Client' and text ~ '{}' order by updatedDate desc"/>
    <input type="text" name="text"/>
    <button type="submit">Search</button>
  </form>
</div>

<div class="two-column" markdown="1">

 - [Open bugs](http://issues.apache.org/jira/issues/?jql=resolution+%3D+EMPTY+and+issuetype+%3D+%22Bug%22+and+component+%3D+%22Java+Client%22+and+project+%3D+%22QPID%22)
 - [Fixed bugs](http://issues.apache.org/jira/issues/?jql=resolution+%3D+%22Fixed%22+and+issuetype+%3D+%22Bug%22+and+component+%3D+%22Java+Client%22+and+project+%3D+%22QPID%22)
 - [Requested enhancements](http://issues.apache.org/jira/issues/?jql=resolution+%3D+EMPTY+and+issuetype+in+%28%22New+Feature%22%2C+%22Improvement%22%29+and+component+%3D+%22Java+Client%22+and+project+%3D+%22QPID%22)
 - [Completed enhancements](http://issues.apache.org/jira/issues/?jql=resolution+%3D+%22Fixed%22+and+issuetype+in+%28%22New+Feature%22%2C+%22Improvement%22%29+and+component+%3D+%22Java+Client%22+and+project+%3D+%22QPID%22)
 - [Report a bug](http://issues.apache.org/jira/secure/CreateIssueDetails!init.jspa?pid=12310520&issuetype=1&priority=3&summary=[Enter%20a%20brief%20description]&components=12311389)
 - [Request an enhancement](http://issues.apache.org/jira/secure/CreateIssueDetails!init.jspa?pid=12310520&issuetype=4&priority=3&summary=[Enter%20a%20brief%20description]&components=12311389)
 - [Jira summary page](http://issues.apache.org/jira/browse/QPID/component/12311389)

</div>
