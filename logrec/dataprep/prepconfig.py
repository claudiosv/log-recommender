import logging
from enum import Enum
from typing import Dict, List, Type

from logrec.dataprep.model.chars import NewLine, Tab
from logrec.dataprep.model.containers import SplitContainer, StringLiteral, OneLineComment, MultilineComment
from logrec.dataprep.model.logging import LogStatement, LogContent, LoggableBlock
from logrec.dataprep.model.noneng import NonEng, NonEngContent
from logrec.dataprep.model.numeric import Number
from logrec.dataprep.model.word import Word

logger = logging.getLogger(__name__)


class PrepParam(str, Enum):
    EN_ONLY: str = 'enonly'
    COM_STR: str = 'comstr'
    SPLIT: str = 'split'
    TABS_NEWLINES: str = 'tabsnewlines'
    MARK_LOGS: str = 'marklogs'
    CAPS: str = 'caps'


class PrepConfig(object):
    possible_param_values = {
        PrepParam.EN_ONLY: [0, 1, 2, 3],
        PrepParam.COM_STR: [0, 1, 2, 3],
        PrepParam.SPLIT: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        PrepParam.TABS_NEWLINES: [0, 1],
        PrepParam.MARK_LOGS: [0, 1],
        PrepParam.CAPS: [0, 1]
    }

    human_readable_values = {
        PrepParam.EN_ONLY: {0: 'multilang',
                            1: 'en_only',
                            2: 'en_only+en_only_content',
                            3: 'asci_only'},
        PrepParam.COM_STR: {0: 'strings+comments',
                            1: 'NO_strings+comments',
                            2: 'NO_strings+NO_comments',
                            3: 'strings+NO_comments'},
        PrepParam.SPLIT: {0: 'NO_splitting',
                          1: 'camel+underscore',
                          2: 'camel+underscore+numbers',
                          3: 'camel+underscore+numbers+heuristic',
                          4: 'camel+underscore+bpe_5k',
                          5: 'camel+underscore+bpe_1k',
                          6: 'camel+underscore+bpe_10k',
                          7: 'camel+underscore+bpe_20k',
                          8: 'camel+underscore+bpe_0',
                          9: 'camel+underscore+bpe_custom'},
        PrepParam.TABS_NEWLINES: {0: 'tabs+newlines',
                                  1: 'NO_tabs+NO_newlines'},
        PrepParam.MARK_LOGS: {0: 'NO_log_marks',
                              1: 'log_marks'},
        PrepParam.CAPS: {
            0: 'case_preserved',
            1: 'lowercased'
        }
    }

    base_bpe_mask = {
        PrepParam.EN_ONLY: 0,
        PrepParam.COM_STR: 0,
        PrepParam.SPLIT: 1,
        PrepParam.TABS_NEWLINES: 0,
        PrepParam.MARK_LOGS: 0,
    }

    @staticmethod
    def __check_param_number(n_passed_params: int):
        n_expected_params = len([i for i in PrepParam])
        if n_passed_params != n_expected_params:
            raise ValueError(f'Expected {n_expected_params} params, got {n_passed_params}')

    @classmethod
    def from_encoded_string(cls, s: str):
        PrepConfig.__check_param_number(len(s))

        res = {}
        for ch, pp in zip(s, PrepParam):
            res[pp] = int(ch)
        return cls(res)

    @staticmethod
    def __check_invariants(params: Dict[PrepParam, int]):
        PrepConfig.__check_param_number(len(params))
        for pp in PrepParam:
            if params[pp] not in PrepConfig.possible_param_values[pp]:
                raise ValueError(f'Invalid value {params[pp]} for prep param {pp}, '
                                 f'possible values are: {PrepConfig.possible_param_values[pp]}')

        if params[PrepParam.EN_ONLY] == 1 and params[PrepParam.SPLIT] == 0:
            raise ValueError("Combination NO_SPL=0 and EN_ONLY=1 is not supported: "
                             "basic splitting needs to be dont done to check for non-English words.")

        if params[PrepParam.EN_ONLY] == 2 and params[PrepParam.SPLIT] == 0:
            raise ValueError("Combination NO_SPL=0 and EN_ONLY=2 is not supported: "
                             "basic splitting needs to be dont done to check for non-English words.")

        if params[PrepParam.EN_ONLY] == 3 and params[PrepParam.SPLIT] == 0:
            raise ValueError("Combination NO_SPL=0 and EN_ONLY=3 is not supported: "
                             "basic splitting needs to be dont done to check for non-English words.")

        if params[PrepParam.EN_ONLY] == 2 and params[PrepParam.COM_STR] == 2:
            raise ValueError("Combination EN_ONLY=2 and COM_STR=2 is obsolete: "
                             "Non-eng-content blocks can be present only in comment or string literal blocks, "
                             "which are obfuscated")

        if params[PrepParam.CAPS] == 1 and params[PrepParam.SPLIT] == 0:
            raise ValueError("Combination NO_SPL=0 and CAPS=1 is not supported: "
                             "basic splitting needs to be dont done to lowercase the subword.")

    def __init__(self, params: Dict[PrepParam, int]):
        PrepConfig.__check_invariants(params)

        self.params = params

    def __str__(self) -> str:
        res = ""
        for k in PrepParam:
            res += str(self.params[k])
        return res

    def get_param_value(self, param: PrepParam) -> int:
        return self.params[param]

    @classmethod
    def assert_classification_config(cls, repr):
        if cls.from_encoded_string(repr).get_param_value(PrepParam.MARK_LOGS) == 0:
            raise ValueError(f'PrepConfig {repr} cannot be used for classification')

    def get_base_bpe_prep_config(self):
        res = PrepConfig.base_bpe_mask
        res[PrepParam.CAPS] = self.params[PrepParam.CAPS]
        return str(PrepConfig(res))


com_str_to_types_to_be_repr = {
    0: [],
    1: [StringLiteral],
    2: [StringLiteral, OneLineComment, MultilineComment],
    3: [OneLineComment, MultilineComment]
}

en_only_to_types_to_be_repr = {
    0: [],
    1: [NonEng],
    2: [NonEng, NonEngContent],
    3: [NonEng]
}


def get_types_to_be_repr(prep_config: PrepConfig) -> List[Type]:
    res = []
    if prep_config.get_param_value(PrepParam.SPLIT) in [1, 2, 3, 4, 5, 6, 7, 8, 9]:
        res.extend([SplitContainer, Word])
    if prep_config.get_param_value(PrepParam.SPLIT) in [2, 3, 4, 5, 6, 7, 8, 9]:
        res.append(Number)
    res.extend(com_str_to_types_to_be_repr[prep_config.get_param_value(PrepParam.COM_STR)])
    res.extend(en_only_to_types_to_be_repr[prep_config.get_param_value(PrepParam.EN_ONLY)])
    if prep_config.get_param_value(PrepParam.TABS_NEWLINES):
        res.extend([NewLine, Tab])
    if prep_config.get_param_value(PrepParam.MARK_LOGS):
        res.extend([LogStatement, LogContent, LoggableBlock])
    return res
