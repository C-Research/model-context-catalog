## {{ tool.key }}
{% if tool.groups %}
groups: {{ tool.sorted_groups | join(',') }}
{% endif %}
{% if tool.visible_params %}
params:
{% for param in tool.visible_params %}
  - `{{ param.name }}` type: {{ param.type }} {% if param.required %}required{% else %}default: {{ param.default }}{% endif %}{% if param.description %}: {{ param.description }}{% endif %}{% if param.example %} (example: {{ param.example }}){% endif %}

{% endfor %}
{% endif %}

{% if tool.exec %}
return: str  # stdout on success

return: list (code: int, stdout: str, stderr: str) # on error
{% else %}
return: {{ tool.return_type or 'unknown' }}
{% endif %}
{% if tool.description or tool.example %}```{% endif %}
{% if tool.description %}

{{ tool.description }}
{% endif %}
{% if tool.example %}

example: {{ tool.example }}
{% endif %}
{% if tool.description or tool.example %}```{% endif %}