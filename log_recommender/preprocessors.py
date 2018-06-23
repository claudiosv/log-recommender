import itertools
import re
import sys
from functools import partial

from java_parser import two_character_tokens, one_character_tokens, one_char_verbose, two_char_verbose, \
    delimiters_to_drop, delimiters_to_drop_verbose, IDENTIFIER_SEPARATOR, JavaParser, EOF

VAR_PLACEHOLDER = "<VAR>"
STRING_RESOURCE_PLACEHOLDER = "<STRING_RESOURCE>"

#=====  UTIL ====================

def add_between_elements(list, what_to_add):
    return [w for part in list for w in (part, what_to_add)][:-1]

def create_regex_from_token_list(token_list):
    m = list(map(lambda x:
             x.replace('\\', '\\\\')
                 .replace("+", "\+")
                 .replace("|", "\|")
                 .replace("*", "\*")
                 .replace("[", "\[")
                 .replace("]", "\]")
                 .replace("-", "\-")
                 .replace('"', '\\"')
                 .replace('?', "\?")
                 .replace('(', "\(")
                 .replace(')', "\)")
                 .replace(".", "\.")
                 , token_list))
    return "(" + "|".join(
        m
    ) +")"

#=====  Multitoken level =====================

def remove_placeholders(multitoken):
    multitoken = re.sub(VAR_PLACEHOLDER, r'', multitoken)
    multitoken = re.sub(STRING_RESOURCE_PLACEHOLDER, r'', multitoken)
    return multitoken

def split_log_text_to_keywords_and_identifiers(multitoken):
    return list(filter(None, re.split("[\[\] ,.\-!?:\n\t(){};=+*/\"&|<>_#\\\@$]+", multitoken)))


def strip_line(multitoken):
    return multitoken.strip()


def to_lower(multitoken):
    return multitoken.lower()


def replace_string_resources_names(multitoken):
    changed = re.sub('^([0-9a-zA-Z]+\\.)+[0-9a-zA-Z]+$', STRING_RESOURCE_PLACEHOLDER, multitoken)
    return changed


def replace_variable_place_holders(multitoken):
    changed = re.sub('\\{\\}', VAR_PLACEHOLDER, multitoken)
    changed = re.sub('%[0-9]*[a-z]', VAR_PLACEHOLDER, changed)
    return changed


#=====  Token level  ============

def camel_case_split(identifier, add_separator=False):
    if identifier == '\n': #TODO XXX
        return [identifier]
    matches = re.finditer('.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)', identifier)
    parts = [m.group(0) for m in matches]
    return add_between_elements(parts, IDENTIFIER_SEPARATOR) if add_separator else parts


def underscore_split(identifier, add_separator=False):
    #TODO it creates empty element if the identifier starts or ends with underscore
    parts = identifier.split("_")
    return add_between_elements(parts, IDENTIFIER_SEPARATOR) if add_separator else parts

#======== Token list level   ==========

def add_ect(multitoken):
    multitoken.append("<ect>")
    return multitoken


def filter_out_stop_words(tokens):
    STOP_WORDS = ["a", "an", "and", "are", "as", "at", "be", "for", "has", "in", "is", "it", "its", "of", "on", "that",
                  "the", "to", "was", "were", "with"]
    # the following words are normally stop words but we might want not to consider as stop words:  by, from, he, will

    return list(filter(lambda w: w not in STOP_WORDS, tokens))

def merge_tabs(tokens):
    res = []
    count = 0
    for word in tokens:
        if word == '\t':
            count += 1
        else:
            if count != 0:
                res.append('\t' + str(count))
                count = 0
            res.append(word)
    if count != 0:
        res.append('\t' + str(count))
    return res

#======== Multitoken list level   ==========

def replace_4whitespaces_with_tabs(multitokens):
    return list(map(lambda x: x.replace("    ", "\t"), multitokens))

def spl(multitokens, two_char_delimiters, one_char_delimiter):
    two_char_regex = create_regex_from_token_list(two_char_delimiters)
    one_char_regex = create_regex_from_token_list(one_char_delimiter)
    return [w for spl in (map(lambda str: split_to_key_words_and_identifiers(str, two_char_regex, one_char_regex, delimiters_to_drop_verbose), multitokens))
            for w in spl]


def spl_non_verbose(line):
    return spl(line, two_character_tokens, one_character_tokens)


def spl_verbose(line):
    '''
    doesn't remove such tokens as tabs, newlines, brackets
    '''
    return spl(line,
               two_character_tokens + two_char_verbose,
               one_character_tokens + one_char_verbose)


def split_to_key_words_and_identifiers(line, two_char_regex, one_char_regex, to_drop):
    two_char_tokens_separated = re.split(two_char_regex, line)
    result =[]
    for str in two_char_tokens_separated:
        if str in two_character_tokens:
            result.append(str)
        else:
            one_char_token_separated = re.split(one_char_regex, str)
            result.extend(list(filter(None, itertools.chain.from_iterable(
                [re.split(to_drop, str) for str in one_char_token_separated]
            ))))
    return result


def filter_out_1_and_2_char_tokens(tokens):
    return list(filter(lambda x: x not in one_character_tokens and x not in two_character_tokens, tokens))


def split_line_canel_case(context_line):
    return [item.lower() for identifier in context_line
            for item in camel_case_split(identifier, add_separator=True)]


def split_line_underscore(context_line):
    return [item for identifier in context_line
            for item in underscore_split(identifier, add_separator=True)]


def newline_and_tab_remover(tokens):
    return list(filter(lambda t: t != "\n" and t != "\t", tokens))


#==========================================================

def names_to_functions(pp_names, context):
    pps = []
    java_parser = JavaParser()
    for name in pp_names:
        if name == 'java.strip_off_identifiers':
            pps.append(partial(java_parser.strip_off_identifiers, context['interesting_context_words']))
        elif name.startswith("java."):
            pps.append(partial(getattr(JavaParser, name[5:]), java_parser))
        else:
            pps.append(getattr(sys.modules[__name__], name))
    return pps


def apply_preprocessors(to_be_processed, preprocessors, context={}):
    if not preprocessors:
        return to_be_processed
    if isinstance(next(iter(preprocessors)), str):
        preprocessors = names_to_functions(preprocessors, context)
    for preprocessor in preprocessors:
        to_be_processed = preprocessor(to_be_processed)
    return to_be_processed


def process_full_identifiers(context, preprocessors, interesting_context_words):
    string_list = [w for line in context for w in (line, EOF)]
    preprocessors += [lambda p: repr(" ".join(p))[1:-1] + " <ect>\n"]
    processed = apply_preprocessors(string_list, preprocessors,
                                    {'interesting_context_words': interesting_context_words})
    return processed