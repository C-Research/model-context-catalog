{%- for param in tool.visible_params -%}
  {%- if not loop.first %}, {% endif -%}
  {{- param.name }}:{{ param.type -}}
  {%- if not param.required %}={{ '"' ~ (param.default or '') ~ '"' if param.type == 'str' else param.default }}{% endif -%}
{%- endfor -%}
