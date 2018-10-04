import logging
import re
############   Multitoken list level    ###############3
import time
from functools import partial

from dataprep.preprocessors.model.general import ProcessableToken, ProcessableTokenContainer
from dataprep.preprocessors.model.split import CamelCaseSplit, WithNumbersSplit, UnderscoreSplit, \
    NonDelimiterSplitContainer, SameCaseSplit


def camel_case(token_list, context):
    return [apply_splitting_to_token(identifier, split_string_camel_case) for identifier in token_list]


def underscore(token_list, context):
    return [apply_splitting_to_token(identifier, split_string_underscore) for identifier in token_list]


def with_numbers(token_list, context):
    return [apply_splitting_to_token(identifier, split_string_with_numbers) for identifier in token_list]

def same_case(token_list, context):
    splitting_file_location = context['splitting_file_location']
    start = time.time()
    splitting_dict = {}
    with open(splitting_file_location, 'r') as f:
        for ln in f:
            word, splitting = ln.split("|")
            splitting_dict[word] = splitting.split()
    logging.info(f"Splitting dictionary is build in {time.time()-start} s")

    return [apply_splitting_to_token(identifier, partial(split_string_same_case, splitting_dict)) for identifier in token_list]


#############  String Level ################

def split_string_camel_case(str):
    matches = re.finditer('.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)', str)
    return [m.group(0) for m in matches], CamelCaseSplit

def split_string_with_numbers(str):
    return [w for w in list(filter(None, re.split('(?<=[a-zA-Z0-9])?([0-9])(?=[a-zA-Z0-9]+|$)', str)))], WithNumbersSplit

def split_string_underscore(str):
    return [w for w in str.split("_")], UnderscoreSplit

def split_string_same_case(splitting_dict, str):
    return splitting_dict[str] if str in splitting_dict else [str], SameCaseSplit

#############  Token Level ################

def apply_splitting_to_token(token, str_splitting_func):
    if isinstance(token, ProcessableToken):
        parts, cls = str_splitting_func(token.get_val())
        parts_lowercased = [ProcessableToken(p.lower()) for p in parts]
        if len(parts) > 1:
            if issubclass(cls, NonDelimiterSplitContainer):
                return cls(parts_lowercased, parts[0][0].isupper())
            else:
                return cls(parts_lowercased)
        else:
            return token
    elif isinstance(token, ProcessableTokenContainer):
        parts = []
        for subtoken in token.get_subtokens():
            parts.append(apply_splitting_to_token(subtoken, str_splitting_func))
        if isinstance(token, NonDelimiterSplitContainer):
            return type(token)(parts, token.is_capitalized())
        else:
            return type(token)(parts)
    else:
        return token
