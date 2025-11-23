---
def link(index, value):
    return f"<li><a href=\"{value.url}\">{value.config.title}</a></li>"
---

# Sample pages

{{html_list(page._page.children, item_fn=link)}}
