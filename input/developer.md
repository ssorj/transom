# Developer Central

<div id="-developer-forms" class="feature">
  <form id="-jira-goto-form">
    Go to <span class="accesskey">i</span>ssue <input name="jira" accesskey="i" autofocus="autofocus" tabindex="1"/>
  </form>

  <form id="-viewvc-goto-form" action="http://svn.apache.org/viewvc" method="get">
    <input type="hidden" name="view" value="revision"/>
    Go to <span class="accesskey">r</span>evision <input type="text" name="revision" accesskey="r" tabindex="2"/>
  </form>

  <form id="-jira-search-form">
    <span class="accesskey">S</span>earch issues <input name="text" type="text" accesskey="s" tabindex="3"/>
  </form>
</div>

<div class="two-column" markdown="1">
<section markdown="1">

## Upcoming releases

 - [Qpid Dispatch 0.4](https://cwiki.apache.org/confluence/display/qpid/Dispatch+Roadmap)
 - [Qpid Proton 0.9](http://qpid.apache.org/proton/development.html#next-release-proton-09)
 - [Qpid 0.32](https://cwiki.apache.org/confluence/display/qpid/0.32+Release)

</section>
<section markdown="1">

## Current releases

 - [Qpid Dispatch 0.3]({{site_url}}/releases/qpid-dispatch-0.3/index.html), January 2015
 - [Qpid Proton 0.8]({{site_url}}/releases/qpid-proton-0.8/index.html), October 2014
 - [Qpid 0.30]({{site_url}}/releases/qpid-0.30/index.html), September 2014

</section>

;;<section markdown="1">
;;
;;## Trunk snapshots
;;
;; - [Qpid Nightly]({{site_url}}/releases/qpid-trunk/index.html)
;; - [Proton Nightly]({{site_url}}/releases/qpid-proton-trunk/index.html)
;;
;;</section>

</div>

## Source modules

<div id="-source-modules" class="scroll" markdown="1">

 || C++ || [Open issues](https://issues.apache.org/jira/issues/?jql=project%20%3D%20QPID%20AND%20resolution%20%3D%20Unresolved%20AND%20component%20in%20\(%22C%2B%2B%20Broker%22%2C%20%22C%2B%2B%20Client%22%2C%20%22C%2B%2B%20Clustering%22%2C%20%22Dot%20Net%20Client%22%2C%20%22Perl%20Client%22%2C%20%22Python%20Tools%22%2C%20%22Qpid%20Managment%20Framework%22%2C%20%22Ruby%20Client%22\)%20ORDER%20BY%20priority%20DESC) || [Report bug](https://issues.apache.org/jira/secure/CreateIssueDetails!init.jspa?pid=12310520&issuetype=1&components=12311395&components=12311396&summary=[Enter%20a%20brief%20description]&priority=3) || [Request improvement](https://issues.apache.org/jira/secure/CreateIssueDetails!init.jspa?pid=12310520&issuetype=4&components=12311395&components=12311396&summary=[Enter%20a%20brief%20description]&priority=3) || [Build status](https://builds.apache.org/view/M-R/view/Qpid/job/Qpid-cpp-trunk-test/) || [Source location](https://svn.apache.org/repos/asf/qpid/trunk/qpid/cpp) ||
 || Java || [Open issues](https://issues.apache.org/jira/issues/?jql=project%20%3D%20QPID%20AND%20resolution%20%3D%20Unresolved%20AND%20component%20in%20\(%22Java%20Broker%22%2C%20%22Java%20Client%22%2C%20%22Java%20Common%22%2C%20%22Java%20Management%20%3A%20JMX%20Console%22%2C%20%22Java%20Performance%20Tests%22%2C%20%22Java%20Tests%22%2C%20%22Java%20Tools%22%2C%20JCA\)%20ORDER%20BY%20priority%20DESC) || [Report bug](https://issues.apache.org/jira/secure/CreateIssueDetails!init.jspa?pid=12310520&issuetype=1&components=12311388&components=12311389&summary=[Enter%20a%20brief%20description]&priority=3) || [Request improvement](https://issues.apache.org/jira/secure/CreateIssueDetails!init.jspa?pid=12310520&issuetype=4&components=12311388&components=12311389&summary=[Enter%20a%20brief%20description]&priority=3)  || [Build status](https://builds.apache.org/view/M-R/view/Qpid/job/Qpid-Java-Java-Test-JDK1.8/) || [Source location](https://svn.apache.org/repos/asf/qpid/trunk/qpid/java) ||
 || Python || [Open issues](https://issues.apache.org/jira/issues/?jql=project%20%3D%20QPID%20AND%20resolution%20%3D%20Unresolved%20AND%20component%20in%20\(%22Python%20Client%22%2C%20%22Python%20Test%20Suite%22\)%20ORDER%20BY%20priority%20DESC) || [Report bug](https://issues.apache.org/jira/secure/CreateIssueDetails!init.jspa?pid=12310520&issuetype=1&components=12311544&summary=[Enter%20a%20brief%20description]&priority=3) || [Request improvement](https://issues.apache.org/jira/secure/CreateIssueDetails!init.jspa?pid=12310520&issuetype=4&components=12311544&summary=[Enter%20a%20brief%20description]&priority=3) || - || [Source location](https://svn.apache.org/repos/asf/qpid/trunk/qpid/python) ||
 || [Dispatch]({{site_url}}/components/dispatch-router/index.html) || [Open issues](https://issues.apache.org/jira/issues/?jql=project%20%3D%20DISPATCH%20AND%20resolution%20%3D%20Unresolved%20ORDER%20BY%20priority%20DESC) || [Report bug](https://issues.apache.org/jira/secure/CreateIssueDetails!init.jspa?pid=12315321&issuetype=1&summary=[Enter%20a%20brief%20description]&priority=3) || [Request improvement](https://issues.apache.org/jira/secure/CreateIssueDetails!init.jspa?pid=12315321&issuetype=4&summary=[Enter%20a%20brief%20description]&priority=3) || - || [Source location](https://svn.apache.org/repos/asf/qpid/dispatch/trunk) ||
 || [JMS]({{site_url}}/components/qpid-jms/index.html) || [Open issues](https://issues.apache.org/jira/issues/?jql=project%20%3D%20QPIDJMS%20AND%20resolution%20%3D%20Unresolved%20ORDER%20BY%20priority%20DESC) || [Report bug](https://issues.apache.org/jira/secure/CreateIssueDetails!init.jspa?pid=12314524&issuetype=1&summary=[Enter%20a%20brief%20description]&priority=3) || [Request improvement](https://issues.apache.org/jira/secure/CreateIssueDetails!init.jspa?pid=12314524&issuetype=4&summary=[Enter%20a%20brief%20description]&priority=3) || - || [Source location](https://git-wip-us.apache.org/repos/asf/qpid-jms.git) ||
 || [Proton]({{site_url}}/proton/index.html) || [Open issues](https://issues.apache.org/jira/issues/?jql=project%20%3D%20PROTON%20AND%20resolution%20%3D%20Unresolved%20ORDER%20BY%20priority%20DESC) || [Report bug](https://issues.apache.org/jira/secure/CreateIssueDetails!init.jspa?pid=12313720&issuetype=1&summary=[Enter%20a%20brief%20description]&priority=3) || [Request improvement](https://issues.apache.org/jira/secure/CreateIssueDetails!init.jspa?pid=12313720&issuetype=4&summary=[Enter%20a%20brief%20description]&priority=3) || [Build status](https://builds.apache.org/view/M-R/view/Qpid/job/Qpid-proton-c/) || [Source location](https://git-wip-us.apache.org/repos/asf/qpid-proton.git) ||

</div>

<div class="four-column" markdown="1" style="font-size: 0.9em;">
<section markdown="1">

## Issues

 - [Your assigned issues](https://issues.apache.org/jira/issues/?filter=-1)
 - [Your reported issues](https://issues.apache.org/jira/issues/?filter=-2)
 - [Your recently viewed issues](https://issues.apache.org/jira/issues/?filter=-3)
 - [Jiropticon]({{site_url}}/jiropticon.html)

</section>
<section markdown="1">

## List archives

 - [Developers](http://qpid.2158936.n2.nabble.com/Apache-Qpid-developers-f7254403.html)
 - [Users](http://qpid.2158936.n2.nabble.com/Apache-Qpid-users-f2158936.html)
 - [Commits](http://qpid.2158936.n2.nabble.com/Apache-Qpid-commits-f7106555.html)
 - [Notifications](http://mail-archives.apache.org/mod_mbox/qpid-notifications/)

</section>
<section markdown="1">

## Apache services

 - [Qpid at Jenkins](https://builds.apache.org/view/M-R/view/Qpid/)
 - [Qpid at Review Board](https://reviews.apache.org/groups/qpid/)
 - [URI shortener](http://s.apache.org/)
 - [Pastebin](https://paste.apache.org/)

</section>
<section markdown="1">

## Wiki
 - [Index](https://cwiki.apache.org/confluence/display/qpid/index)
 - [Developer pages](https://cwiki.apache.org/confluence/display/qpid/developer+pages)
 - [Documentation](https://cwiki.apache.org/confluence/display/qpid/documentation)
 - [Releases](https://cwiki.apache.org/confluence/display/qpid/Releases)

</section>
</div>
