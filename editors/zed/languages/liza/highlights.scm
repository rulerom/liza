(type_identifier) @type
(builtin_type) @type.builtin
["View" "Option" "Result"] @type.builtin
(builtin_variant) @constructor
(number) @number
(boolean) @boolean
(string) @string
(escape_sequence) @string.escape
(comment) @comment
["import" "pub" "fn" "struct" "enum" "var" "return" "if" "else" "while"
 "match" "copy" "move" "view" "pure" "io" "alloc"] @keyword
["+" "-" "*" "/" "%" "+%" "-%" "*%" "+|" "-|" "*|"
 "==" "!=" "<" "<=" ">" ">=" "&&" "||" "!" "~" "&" "|" "^" "<<" ">>" "=" "->" "=>" ".."] @operator
["(" ")" "[" "]" "{" "}"] @punctuation.bracket
["," ";" ":" "."] @punctuation.delimiter
(function_definition name: (identifier) @function)
(parameter name: (identifier) @variable.parameter)
(field_definition name: (identifier) @property)
(field_expression field: (identifier) @property)
(variant_definition name: (identifier) @constructor)
(pattern variant: (_) @constructor)
(pattern binding: (identifier) @variable)
(call_expression function: (identifier) @function)
(call_expression function: (field_expression field: (identifier) @function))
; Constructors follow the type naming convention; no semantic type resolution.
((call_expression function: (identifier) @constructor) (#match? @constructor "^[A-Z]"))

[(break_statement) (continue_statement)] @keyword

((field_expression value: (identifier) @type field: (identifier) @constructor)
 (#match? @type "^[A-Z]"))

(module_path) @variable

(generic_parameter (identifier) @type)
["copyable" "implicit_copy"] @keyword
