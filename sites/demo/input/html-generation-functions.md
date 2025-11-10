---
import pprint

thirteen_states = (
    "Delaware",
    "Pennsylvania",
    "New Jersey",
    "Georgia",
    "Connecticut",
    "Massachusetts",
    "Maryland",
    "South Carolina",
    "New Hampshire",
    "Virginia",
    "New York",
    "North Carolina",
    "Rhode Island",
)

employee_data = (
    (101, 'John', 'Doe', 'Sales', 60000),
    (102, 'Jane', 'Smith', 'IT', 75000),
    (103, 'Peter', 'Jones', 'Sales', 62000),
    (104, 'Mary', 'Brown', 'IT', 71000),
    (105, 'David', 'Williams', 'HR', 55000),
)

---

<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-core.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"></script>

# HTML generation functions

<!-- Element `content` is rendered as `str(content)` if scalar and -->
<!-- `"".join(content)` if iterable.  `None` is converted to `""`.  Element -->
<!-- `attrs` are rendered as `<name>="<value>"` after the tag.  The name -->
<!-- `_class` or `class_` is converted to `class`. -->

## Lists

~~~ python
html_list(data, tag="ul", item_fn=None, **attrs) -> "<ul>...</ul>"
html_list_csv(path, tag="ul", item_fn=None, **attrs) -> "<ul>...</ul>"
item_fn(index, value) -> "<li>...</li>"
~~~

Data:

~~~ python
{{pprint.pformat(thirteen_states)}}
~~~

Invocation:

~~~ python
html_list(thirteen_states, style="columns: 3;")
~~~

Result:

{{html_list(thirteen_states, style="columns: 3;")}}

## Tables

~~~ python
html_table(data, headings=None, item_fn=None, heading_fn=None, **attrs)
html_table_csv(path, headings=None, item_fn=None, heading_fn=None, **attrs)
item_fn(row_index, column_index, value) -> "<td>...</td>"
heading_fn(column_index, value) -> "<th>...</th>"
~~~

Data:

~~~ python
{{pprint.pformat(employee_data)}}
~~~

Invocation:

~~~ python
html_table(employee_data, ("Employee ID", "First name", "Last name", "Department", "Salary"))
~~~

Result:

{{html_table(employee_data, ("Employee ID", "First name", "Last name", "Department", "Salary"))}}
