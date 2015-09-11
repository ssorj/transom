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

# Source Code

Qpid employs
[revision control](http://en.wikipedia.org/wiki/Revision_control) to
track and manage changes to its source code.  Qpid uses the
[Subversion](http://subversion.apache.org/) revision control system.

## Browse the code

 - [Browse via ViewVC](http://svn.apache.org/viewvc/qpid)
 - [Browse the source tree directly](https://svn.apache.org/repos/asf/qpid)
 - <form id="-viewvc-goto-form" action="http://svn.apache.org/viewvc" method="get"><input type="hidden" name="view" value="revision"/>Go to revision <input type="text" name="revision"/></form>

## Check out the code

To access the repository anonymously, use the `svn checkout` command
with one of the Subversion URLs below.

    Qpid
    % svn checkout http://svn.apache.org/repos/asf/qpid/trunk/qpid qpid

    Qpid Dispatch
    % svn checkout http://svn.apache.org/repos/asf/qpid/dispatch/trunk dispatch

When adding files to Subversion, it's important that the appropriate
Subversion properties are set. The client can do it automatically by
modifying the `auto-props` section of the Subversion config file.  Use
the contents of [qpid/etc/svn-auto-props](http://svn.apache.org/repos/asf/qpid/trunk/qpid/etc/svn-auto-props).

<div class="two-column" markdown="1">
<section markdown="1">

### Qpid

 - [Anonymous Subversion URL](http://svn.apache.org/repos/asf/qpid/trunk/qpid/)
 - [Committer Subversion URL](https://svn.apache.org/repos/asf/qpid/trunk/qpid/)
 - [Browse via ViewVC](http://svn.apache.org/viewvc/qpid/trunk/qpid/)

</section>
<section markdown="1">

### Qpid Dispatch

 - [Anonymous Subversion URL](http://svn.apache.org/repos/asf/qpid/dispatch/trunk/)
 - [Committer Subversion URL](https://svn.apache.org/repos/asf/qpid/dispatch/trunk/)
 - [Browse via ViewVC](http://svn.apache.org/viewvc/qpid/dispatch/trunk/)

</section>
</div>

## Install the code

Consult the install documentation below.

 - [How to build Qpid Java](https://cwiki.apache.org/confluence/display/qpid/qpid+java+build+how+to)
 - [Installing Qpid C++](http://svn.apache.org/repos/asf/qpid/trunk/qpid/cpp/INSTALL)
 - [Installing Qpid Dispatch](http://svn.apache.org/repos/asf/qpid/dispatch/trunk/README)
 - [Installing Qpid Python](http://svn.apache.org/repos/asf/qpid/trunk/qpid/python/README.txt)
 - [Installing Qpid WCF](http://svn.apache.org/repos/asf/qpid/trunk/qpid/wcf/ReadMe.txt)

## Git

Read-only [Git](http://git-scm.com/) mirrors are available.  Use one
of the following commands.

    Qpid
    % git clone git://git.apache.org/qpid.git

    Qpid Dispatch
    % git clone git://git.apache.org/qpid-dispatch.git

If you have commit access, it's also possible to commit back with `git
svn dcommit` by following the instructions on the
[Git at Apache](http://www.apache.org/dev/git.html) page.

[Qpid Proton]({{site_url}}/proton/index.html) uses Git as its primary
source control.  See the links for
[Qpid Proton source code]({{site_url}}/proton/index.html#source-code).

## Continuous integration

Qpid uses [Jenkins](http://jenkins-ci.org/) to perform
[continuous integration](http://en.wikipedia.org/wiki/Continuous_integration)
of the latest changes.

 - [Automated tests in Jenkins](https://builds.apache.org//view/M-R/view/Qpid/)
 - [Overview of Qpid CI](https://cwiki.apache.org/confluence/display/qpid/continuous+integration)

## Notifications

The traffic on these lists is automatically generated.  Please do not
post any messages to them.

To subscribe, send an email with subject "subscribe" to the subscribe
address.  To unsubscribe, send "unsubscribe" to the unsubscribe
address.

### Commits list

Alerts for changes committed to the Qpid source.  

 - Send "subscribe" to <commits-subscribe@qpid.apache.org>
 - Send "unsubscribe" to <commits-unsubscribe@qpid.apache.org>
 - [List information](http://mail-archives.apache.org/mod_mbox/qpid-commits/)
 - [Archive](http://qpid.2158936.n2.nabble.com/Apache-Qpid-commits-f7106555.html)
 - [News feed](http://mail-archives.apache.org/mod_mbox/qpid-commits/?format=atom)

### Notifications list

Alerts for build and test failures from our continuous integration
servers.

 - Send "subscribe" to <notifications-subscribe@qpid.apache.org>
 - Send "unsubscribe" to <notifications-unsubscribe@qpid.apache.org>
 - [List information](http://mail-archives.apache.org/mod_mbox/qpid-notifications/)
 - [News feed](http://mail-archives.apache.org/mod_mbox/qpid-notifications/?format=atom)

## More information

 - [Subversion project](http://subversion.apache.org/)
 - [Subversion manual](http://svnbook.red-bean.com/)
 - [Subversion at Apache](http://www.apache.org/dev/version-control.html)
 - [Git project](http://git-scm.com)
 - [Git documentation](http://git-scm.com/documentation)
 - [Git at Apache](http://www.apache.org/dev/git.html)
 - [Jenkins project](http://jenkins-ci.org/)
 - [Jenkins documentation](https://wiki.jenkins-ci.org/display/JENKINS/Meet+Jenkins)
 - [Continuous integration at Apache](http://ci.apache.org/)
