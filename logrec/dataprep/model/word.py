from enum import Enum, auto
from typing import List

from logrec.dataprep.model.chars import SpecialChar
from logrec.dataprep.model.placeholders import placeholders
from logrec.dataprep.preprocessors.repr import ReprConfig
from logrec.dataprep.split.ngram import do_ngram_splitting


class Capitalization(Enum):
    UNDEFINED = auto()
    NONE = auto()
    FIRST_LETTER = auto()
    ALL = auto()


class Underscore(SpecialChar):
    def non_preprocessed_repr(self, repr_config):
        return "_"


class Word(object):
    """
    Invariants:
    str === str(Word.of(str))
    """

    def __init__(self, canonic_form, capitalization=Capitalization.UNDEFINED):
        Word._check_canonic_form_is_valid(canonic_form)

        self.canonic_form = canonic_form
        self.capitalization = capitalization

    def get_canonic_form(self):
        return self.canonic_form

    @staticmethod
    def _is_strictly_upper(s):
        return s.isupper() and not s.lower().isupper()

    @staticmethod
    def _check_canonic_form_is_valid(canonic_form):
        if not isinstance(canonic_form, str) or Word._is_strictly_upper(canonic_form) \
                or (canonic_form and Word._is_strictly_upper(canonic_form[0])):
            raise AssertionError(f"Bad canonic form: {canonic_form}")

    def __str__(self):
        return self.non_preprocessed_repr(ReprConfig.empty())

    def __with_capitalization(self, subwords: List[str]) -> List[str]:
        if self.capitalization == Capitalization.UNDEFINED or self.capitalization == Capitalization.NONE:
            res = subwords
        elif self.capitalization == Capitalization.FIRST_LETTER:
            res = [placeholders['capital']] + subwords
        elif self.capitalization == Capitalization.ALL:
            res = [placeholders['capitals']] + subwords
        else:
            raise AssertionError(f"Unknown value: {self.capitalization}")
        return res

    def preprocessed_repr(self, repr_config: ReprConfig) -> List[str]:
        subwords = do_ngram_splitting(self.canonic_form, repr_config.ngram_split_config)

        return self.__with_capitalization(subwords)

    def non_preprocessed_repr(self, repr_config):
        if self.capitalization == Capitalization.UNDEFINED or self.capitalization == Capitalization.NONE:
            return self.canonic_form
        elif self.capitalization == Capitalization.FIRST_LETTER:
            return self.canonic_form.capitalize()
        elif self.capitalization == Capitalization.ALL:
            return self.canonic_form.upper()
        else:
            raise AssertionError(f"Unknown value: {self.capitalization}")

    def __repr__(self):
        return f'{self.__class__.__name__}({self.canonic_form, self.capitalization})'

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.canonic_form == other.canonic_form \
               and self.capitalization == other.capitalization

    @classmethod
    def from_(cls, s: str):
        if not s:
            raise ValueError(f'A subword can be neither None nor of length zero. Value of the subword is {s}')

        if s.islower() or not s:
            return cls(s, Capitalization.NONE)
        elif s.isupper():
            return cls(s.lower(), Capitalization.ALL)
        elif s[0].isupper():
            return cls(s[0].lower() + s[1:], Capitalization.FIRST_LETTER)
        else:
            return cls(s, Capitalization.UNDEFINED)


class ParseableToken(object):
    """
    This class represents parts of input that still needs to be parsed
    """

    def __init__(self, val):
        if not isinstance(val, str):
            raise ValueError(f"val should be str but is {type(val)}")
        self.val = val

    def __str__(self):
        return self.val

    def __repr__(self):
        return f'{self.__class__.__name__}({self.val})'

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.val == other.val
