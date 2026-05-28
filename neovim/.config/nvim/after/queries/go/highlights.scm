; extends

(function_declaration
  name: (identifier) @spell)

(method_declaration
  name: (field_identifier) @spell)

(type_spec
  name: (type_identifier) @spell)

(var_declaration (var_spec name: (identifier) @spell))

(const_declaration (const_spec name: (identifier) @spell))

(short_var_declaration
  left: (expression_list) @spell)

(field_declaration
  name: (field_identifier) @spell)

(parameter_declaration
  name: (identifier) @spell)

(variadic_parameter_declaration
  name: (identifier) @spell)

(field_identifier) @spell
