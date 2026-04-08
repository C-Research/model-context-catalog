## {{ tool.key }} ({% include 'param_signature.md' %}) -> {% if tool.exec %}str | (int, str, str){% else %}{{ tool.return_type or 'unknown' }}{% endif %}

{% for param in tool.visible_params %}
{% if param.description %}
`{{ param.name }}` — {{ param.description }}
{% endif %}
{% endfor %}
{% if tool.description %}
{{ tool.description }}
{% endif %}
{% if tool.example %}
{{ tool.example }}
{% endif %}
