def _link(href, text):
    return "<a href=\"{}\">{}</a>".format(href, text)

class _Release(object):
    def __init__(self, name, number):
        self.name = name
        self.number = number

current_release = "0.30"

current_release_url = "{}/releases/qpid-{}".format(site_url, current_release)
current_release_link = _link("{}/index.html".format(current_release_url), "Qpid {}</a>".format(current_release_url, current_release))

current_release_link = "<a href=\"%(current_release_url)s/index.html\">Qpid %(current_release)s</a>"
current_release_tag = "http://svn.apache.org/repos/asf/qpid/tags/%(current_release)s"

current_proton_release = "0.8"
current_proton_release_url = "%(site_url)s/releases/qpid-proton-%(current_proton_release)s"
current_proton_release_link = "<a href=\"%(current_proton_release_url)s/index.html\">Qpid Proton %(current_proton_release)s</a>"
current_proton_release_tag = "http://svn.apache.org/repos/asf/qpid/proton/tags/%(current_proton_release)s"

current_dispatch_release = "0.3"
current_dispatch_release_url = "%(site_url)s/releases/qpid-dispatch-%(current_dispatch_release)s"
current_dispatch_release_link = "<a href=\"%(current_dispatch_release_url)s/index.html\">Qpid Dispatch %(current_dispatch_release)s</a>"
current_dispatch_release_tag = "http://svn.apache.org/repos/asf/qpid/dispatch/tags/%(current_di"

def user_link(name):
    return "XXX {}".format(name)
