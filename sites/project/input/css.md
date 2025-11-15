# Transom CSS

<!-- - It is parameterized. -->

<div class="code-label">input/site.css</div>

~~~ css
{{include("../../profiles/website/input/site.css")}}
~~~

<div class="code-label">config/transom/base.css</div>

~~~ css
{{strip(include("config/transom/base.css"))}}
~~~

<div class="code-label">config/transom/components.css</div>

~~~ css
{{strip(include("config/transom/components.css"))}}
~~~

<div class="code-label">config/transom/theme.css</div>

~~~ css
{{strip(include("config/transom/theme.css"))}}
~~~

<div class="code-label">config/transom/layout.css</div>

~~~ css
{{strip(include("config/transom/layout.css"))}}
~~~
