import re

############   Multitoken list level    ###############3
from dataprep.preprocessors.model.general import ProcessableToken, ProcessableTokenContainer
from dataprep.preprocessors.model.split import CamelCaseSplit, WithNumbersSplit, UnderscoreSplit, \
    NonDelimiterSplitContainer


def camel_case(token_list):
    return [camel_case_split(identifier) for identifier in token_list]


def underscore(token_list):
    return [underscore_split(identifier) for identifier in token_list]


def with_numbers(token_list):
    return [with_numbers_split(identifier) for identifier in token_list]


#############  Token Level ################

def camel_case_split(token):
    if isinstance(token, ProcessableToken):
        matches = re.finditer('.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)', token.get_val())
        parts = [m.group(0) for m in matches]
        parts_lowercased = [ProcessableToken(p.lower()) for p in parts]
        if len(parts) > 1:
            return CamelCaseSplit(parts_lowercased, parts[0][0].isupper())
        else:
            return token
    elif isinstance(token, ProcessableTokenContainer):
        parts = []
        for subtoken in token.get_subtokens():
            parts.append(camel_case_split(subtoken))
        if isinstance(token, NonDelimiterSplitContainer):
            return type(token)(parts, token.is_capitalized())
        else:
            return type(token)(parts)
    else:
        return token


def with_numbers_split(token):
    if isinstance(token, ProcessableToken):
        parts = [w for w in list(filter(None, re.split('(?<=[a-zA-Z0-9])?([0-9])(?=[a-zA-Z0-9]+|$)', token.get_val())))]
        pt_parts = [ProcessableToken(w) for w in parts]
        if len(parts) > 1:
            return WithNumbersSplit(pt_parts, parts[0][0].isupper())
        else:
            return token
    elif isinstance(token, ProcessableTokenContainer):
        parts = []
        for subtoken in token.get_subtokens():
            parts.append(with_numbers_split(subtoken))
        if isinstance(token, NonDelimiterSplitContainer):
            return type(token)(parts, token.is_capitalized())
        else:
            return type(token)(parts)
    else:
        return token


def underscore_split(token):
    if isinstance(token, ProcessableToken):
        parts = [ProcessableToken(w) for w in token.get_val().split("_")]
        if len(parts) > 1:
            return UnderscoreSplit(parts)
        else:
            return token
    elif isinstance(token, ProcessableTokenContainer):
        parts = []
        for subtoken in token.get_subtokens():
            parts.append(underscore_split(subtoken))
        if isinstance(token, NonDelimiterSplitContainer):
            return type(token)(parts, token.is_capitalized())
        else:
            return type(token)(parts)
    else:
        return token