class _Release(object):
    def __init__(self, component_name, component_key, number):
        self.component_name = component_name
        self.component_key = component_key
        self.number = number

    @property
    def name(self):
        return "{} {}".format(self.component_name, self.number)

    @property
    def url(self):
        return "{}/releases/{}-{}".format(site_url, self.component_key, self.number)

    @property
    def link(self):
        return "<a href=\"{}\">{}</a>".format(self.url, self.name)

_qpid_release = _Release("Qpid", "qpid", "0.30")
_proton_release = _Release("Qpid Proton", "qpid-proton", "0.8")
_dispatch_release = _Release("Qpid Dispatch", "qpid-dispatch", "0.3")

_svn_base = "http://svn.apache.org/repos/asf/qpid"

current_release = _qpid_release.number
current_release_url = _qpid_release.url
current_release_link = _qpid_release.link
current_release_tag = "{}/tags/{}".format(_svn_base, _qpid_release.number)

current_proton_release = _proton_release.number
current_proton_release_url = _proton_release.url
current_proton_release_link = _proton_release.link
current_proton_release_tag = "{}/proton/tags/{}".format \
                             (_svn_base, _proton_release.number)

current_dispatch_release = _dispatch_release.number
current_dispatch_release_url = _dispatch_release.url
current_dispatch_release_link = _dispatch_release.link
current_dispatch_release_tag = "{}/dispatch/tags/{}".format \
                               (_svn_base, _dispatch_release.number)
