pp_params = {
    'preprocessors': [
        "lines_to_one_lines_with_newlines",
        "replace_4whitespaces_with_tabs",
        "split_numeric_literals",
        "java.process_number_literals",
        "spl_verbose",
        "split_line_camel_case",
        "split_line_underscore",
        # "merge_tabs",
        "java.strip_off_string_literals",
        "java.strip_off_multiline_comments",
        "java.strip_off_one_line_comments",

        # "java.strip_off_identifiers"
        "newline_and_tab_remover",
        "split_line_with_numbers",
        "split_line_lowercase",
        "to_string_repr"
    ],
    'more_lines_ignore': 5000
}