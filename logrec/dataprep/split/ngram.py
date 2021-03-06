from enum import Enum, auto

from logrec.dataprep.split.bpe_encode import encode_word



class NgramSplittingType(Enum):
    NUMBERS_AND_CUSTOM = auto()
    BPE = auto()
    ONLY_NUMBERS = auto()


class NgramSplitConfig(object):
    def __init__(self, splitting_type=None, merges_cache=None, merges=None, sc_splittings=None):
        self._splitting_type = splitting_type
        self._merges_cache = merges_cache
        self._merges = merges
        self._sc_splittings = sc_splittings

    @property
    def merges_cache(self):
        return self._merges_cache

    @property
    def merges(self):
        return self._merges

    @property
    def sc_splittings(self):
        return self._sc_splittings

    @merges.setter
    def merges(self, m):
        self._merges = m

    @merges_cache.setter
    def merges_cache(self, m):
        self._merges_cache = m

    def set_splitting_type(self, type):
        self._splitting_type = type

    @sc_splittings.setter
    def sc_splittings(self, s):
        self._sc_splittings = s

    @property
    def splitting_type(self):
        return self._splitting_type


def get_bpe_subwords(word, config):
    merges = config.merges
    cache = config.merges_cache
    if word in cache:
        return cache[word]
    else:
        return encode_word(word, merges)


def get_sc_subwords(word, config):
    splittings = config.sc_splittings
    if word in splittings:
        return splittings[word]
    else:
        return [word]


def get_number_subwords(word, config):
    return [str(w) for w in word]


splitting_type_to_func_map = {
    NgramSplittingType.ONLY_NUMBERS: get_number_subwords,
    NgramSplittingType.NUMBERS_AND_CUSTOM: get_sc_subwords,
    NgramSplittingType.BPE: get_bpe_subwords
}


def do_ngram_splitting(token, ngram_split_config):
    if ngram_split_config.splitting_type and ngram_split_config.splitting_type != NgramSplittingType.ONLY_NUMBERS:
        subwords = splitting_type_to_func_map[ngram_split_config.splitting_type](token, ngram_split_config)
    else:
        subwords = [token]

    return subwords
