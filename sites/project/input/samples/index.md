---
def link(index, value):
    return f"<li><a href=\"{value.url}\">{value.title}</a></li>"
---

# Sample pages

{{html_list(_page.children, item_fn=link)}}
