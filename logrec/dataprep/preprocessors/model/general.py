from dataprep.preprocessors.model.placeholders import placeholders


class ProcessableToken(object):
    def __init__(self, s):
        if isinstance(s, str):
            self.val = s
        else:
            raise AssertionError(f"Bad type of obj: {str}")

    def get_val(self):
        return self.val

    def to_repr(self):
        return self.val.lower()

    def get_flat_list(self):
        return self.__get_flat_list(self.val)

    def __str__(self):
        return self.val

    def __repr__(self):
        return f'{self.__class__.__name__}({self.val})'

    def __get_flat_list(self, val):
        if isinstance(val, list):
            return [r for v in val for r in self.__get_flat_list(v)]
        elif isinstance(val, str):
            return val
        elif isinstance(val, ProcessableToken):
            return val.get_flat_list()
        else:
            raise AssertionError(f"Bad type of obj: {str}")

    def get_processable_subtokens(self):
        if self.simple():
            return [self]
        else:
            return [pst for st in self.val if isinstance(st, ProcessableToken) for pst in st.get_processable_subtokens()]

    def simple(self):
        return len(self.val) == 1 and isinstance(self.val[0], str)

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.val == other.val


class ProcessableTokenContainer(object):
    def __init__(self, subtokens):
        if isinstance(subtokens, list):
            self.subtokens = subtokens
        else:
            raise AssertionError(f"Should be list byt is: {subtokens}")

    def get_subtokens(self):
        return self.subtokens

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.subtokens == other.subtokens

    def __repr__(self):
        return f'{self.__class__.__name__}{self.subtokens}'


class NonEng(object):
    def __init__(self, str):
        self.str = str

    def non_preprocessed_repr(self):
        return self.str
        # raise NotImplementedError("We don't support non preprocessed representation of NonEng, i.e. non-english tokens")

    def preprocessed_repr(self):
        return placeholders['non_ascii']

    def __repr__(self):
        return f'{self.__class__.__name__}({self.str})'

    def __str__(self):
        return self.non_preprocessed_repr()

    def to_repr(self):
        return self.preprocessed_repr()

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.str == other.str
