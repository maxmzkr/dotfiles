; extends

(identifier) @variable.member

[(raw_string_literal) (interpreted_string_literal)] @string

(raw_value) @variable

(full_text_search) @string

(binary_expression
  operator: (_) @keyword.operator)

[
  "="
  ":"
  "=~"
  "<"
  "<="
  ">"
  ">="
] @operator

[
  "("
  ")"
  "{"
  "}"
] @punctuation.bracket
