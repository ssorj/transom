# Transom CSS

<!-- - It is parameterized. -->

<div class="code-label">input/site.css</div>

~~~ css
{{include("../../profiles/website/input/site.css")}}
~~~

<div class="code-label">config/transom.css</div>

~~~ css
{{strip(strip_license_header(include("config/transom.css")))}}
~~~
