---
violet = "Petunia"
---

# Test cases 1

## Print object repr()s

~~~
site == {{site}}
site.page_template == {{site.page_template}}
site.body_template == {{site.body_template}}

page == {{page}}
page.page_template == {{page.page_template}}
page.body_template == {{page.body_template}}
~~~

## Resolve a variable defined in site.py

~~~
albert == "{{albert}}"
~~~

## Resolve a variable defined in the page header

~~~
violet == "{{violet}}"
~~~

## Convert triple curly braces to literal double curly braces

~~~
\{\{\{literal\}\}\} == {{{literal}}}
~~~

## Generate path navigation with leading and trailing elements stripped

~~~
page.path_nav(1, -1) == "{{page.path_nav(1, -1)}}"
~~~
