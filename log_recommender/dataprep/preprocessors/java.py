import logging
import re

from dataprep.preprocessors.model.chars import MultilineCommentStart, MultilineCommentEnd, OneLineCommentStart, NewLine, \
    Backslash, Quote
from dataprep.preprocessors.model.general import ProcessableToken, ProcessableTokenContainer
from dataprep.preprocessors.model.numeric import Number, D, F, L, DecimalPoint, HexStart, E
from dataprep.preprocessors.model.placeholders import placeholders
from dataprep.preprocessors.model.textcontainers import MultilineComment, StringLiteral, OneLineComment

START_MULTILINE_COMMENT = MultilineCommentStart()
END_MULTILINE_COMMENT = MultilineCommentEnd()

START_ONE_LINE_COMMENT = OneLineCommentStart()
NEW_LINE = NewLine()

QUOTE = Quote()
BACKSLASH = Backslash()

tabs = ["\t" + str(i) for i in range(11)]

two_character_tokens = [
    "/*",
    "*/",
    "==",
    "!=",
    "**",
    "//",
    "++",
    "--",
    "+=",
    "-=",
    "/=",
    "*=",
    "%=",
    "<=",
    ">=",
    "^=",
    "&=",
    "|=",
    ">>",
    "<<",
    "&&",
    "||"
]

one_character_tokens = [
    "+",
    "*",
    "!",
    "/",
    ">",
    "<",
    "="
]

two_char_verbose = [
    "\t", "\n"
]

one_char_verbose = [
    "{", "}", "[", "]", ",", ".", "-", "?", ":", "(", ")", ";", '"', "&",
    "|", "\\", "@", "#", "$", "'", "~", "%", "^", "\\"
]

delimiters_to_drop = "[\[\] ,.\-?:\n\t(){};\"&|_#\\\@$]"
delimiters_to_drop_verbose = " " #TODO according to the new philosophy we shoulnt drop anything

key_words = [
"abstract",
"continue",
"for",
"new",
"switch",
"assert",
"default",
"package",
"synchronized",
"boolean",
"do",
"if",
"private",
"this",
"break",
"double",
"implements",
"protected",
"throw",
"byte",
"else",
"import",
"public",
"throws",
"case",
"enum",
"instanceof",
"return",
"transient",
"catch",
"extends",
"int",
"short",
"try",
"char",
"final",
"interface",
"static",
"void",
"class",
"finally",
"long",
"strictfp",
"volatile",
"float",
"native",
"super",
"while",
"true",
"false",
"null"
]

NUMBER_REGEX = '-?(?:0x[0-9a-fA-F]+[lL]?|[0-9]+[lL]?|(?:[0-9]*\.[0-9]+|[0-9]+(?:\.[0-9]*)?)(?:[eE][-+]?[0-9]+)?[fFdD]?)'


def is_number(s):
    return re.fullmatch(NUMBER_REGEX, s)


def find_all_comment_string_literal_symbols(token_list):
    res = []
    for ind in range(len(token_list)):
        if token_list[ind] == QUOTE:
            i = ind - 1
            while i >= 0 and token_list[i] == BACKSLASH:
                i -= 1
            if (ind - i) % 2 == 1:
                res.append((ind, token_list[ind]))
        elif token_list[ind] in [START_MULTILINE_COMMENT, END_MULTILINE_COMMENT, START_ONE_LINE_COMMENT, NEW_LINE]:
            res.append((ind, token_list[ind]))
    return res


def replace_segments(token_list, segments_to_remove):
    new_token_list = []
    curr_ind = 0
    for begin, end, clazz in segments_to_remove:
        new_token_list.extend(token_list[curr_ind:begin])
        new_token_list.append(clazz(token_list[begin+1:end]))
        curr_ind = end if clazz == OneLineComment else end + 1
    if curr_ind < len(token_list):
        new_token_list.extend(token_list[curr_ind:])
    return new_token_list

def process_comments_and_str_literals(token_list, context):
    comment_string_literal_symbols_locations = find_all_comment_string_literal_symbols(token_list)
    active_symbol, active_symbol_index = None, -1
    segments_to_remove = []

    for index, symbol in comment_string_literal_symbols_locations:
        logging.debug(f"Processing {index} out of {len(token_list)}")
        if active_symbol is None:
            if symbol == END_MULTILINE_COMMENT:
                logging.warning(f"{token_list[index-100:index+1]}, index: {index}")
                return token_list
            elif symbol == NEW_LINE:
                pass
            else:
                active_symbol, active_symbol_index = symbol, index
        elif active_symbol == QUOTE:
            if symbol == NEW_LINE:
                logging.warning(f"{token_list[index-100:index+1]}, index: {index}")
                return token_list
            elif symbol == QUOTE:
                segments_to_remove.append((active_symbol_index, index, StringLiteral))
                active_symbol, active_symbol_index = None, -1
        elif active_symbol == START_ONE_LINE_COMMENT:
            if symbol == NEW_LINE:
                segments_to_remove.append((active_symbol_index, index, OneLineComment))
                active_symbol, active_symbol_index = None, -1
        elif active_symbol == START_MULTILINE_COMMENT:
            if symbol == END_MULTILINE_COMMENT:
                segments_to_remove.append((active_symbol_index, index, MultilineComment))
                active_symbol, active_symbol_index = None, -1
        else:
            raise AssertionError(f"Unknown symbol: {active_symbol}")
    token_list = replace_segments(token_list, segments_to_remove)
    return token_list

def replace(token_list, start, end, new_symbol):
    len_before_replacement = len(token_list)
    string_literal_content = token_list[start+1:end]
    del (token_list[start: end if new_symbol == OneLineComment else end+1])
    token_list.insert(start, new_symbol(string_literal_content))
    return len_before_replacement - len(token_list)

def strip_off_identifiers(token_list, context):
    identifiers_to_ignore = context['identifiers_to_ignore']
    non_identifiers = set(
        key_words + two_character_tokens + one_character_tokens + one_char_verbose + two_char_verbose + \
        list(placeholders.values()) + tabs + identifiers_to_ignore)

    result = []
    for token in token_list:
        if not is_number(token) and token not in non_identifiers:
            result.append(placeholders['identifier'])
        else:
            result.append(token)
    return result


def process_number_literal(possible_number):
    if is_number(possible_number) and possible_number not in tabs:
        parts_of_number = []
        if possible_number.startswith('-'):
            parts_of_number.append('-')
            possible_number = possible_number[1:]
        if possible_number.startswith("0x"):
            parts_of_number.append(HexStart())
            possible_number = possible_number[2:]
            hex = True
        else:
            hex = False
        for ch in possible_number:
            if ch == '.':
                parts_of_number.append(DecimalPoint())
            elif ch == 'l' or ch == 'L':
                parts_of_number.append(L())
            elif (ch == 'f' or ch == 'F') and not hex:
                parts_of_number.append(F())
            elif (ch == 'd' or ch == 'D') and not hex:
                parts_of_number.append(D())
            elif (ch == 'e' or ch == 'E') and not hex:
                parts_of_number.append(E())
            else:
                parts_of_number.append(ch)
        return Number(parts_of_number)
    else:
        return ProcessableToken(possible_number)


def process_numeric_literals(token_list, context):
    res = []
    for token in token_list:
        if isinstance(token, ProcessableToken):
            numbers_separated = list(filter(None, re.split(f'(?:^|(?<=[^a-zA-Z0-9]))({NUMBER_REGEX})(?=[^a-zA-Z0-9.]|$)', token.get_val())))
            for possible_number in numbers_separated:
               res.append(process_number_literal(possible_number))
        elif isinstance(token, ProcessableTokenContainer):
            for subtoken in token.get_subtokens():
                res.extend(process_numeric_literals(subtoken))
        else:
            res.append(token)
    return res
