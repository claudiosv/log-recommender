import argparse
import logging
import os
from collections import defaultdict

from Levenshtein.StringMatcher import StringMatcher
from tqdm import tqdm

from logrec.dataprep import base_project_dir
from logrec.dataprep.split.samecase.splitter import load_english_dict

logger = logging.getLogger(__name__)


def get_words_of_almost_same_length(word, len_to_words_in_dict):
    ln = len(word)
    return len_to_words_in_dict[ln - 1] + len_to_words_in_dict[ln] + len_to_words_in_dict[ln + 1]


def fl(word, word_from_dict):
    if len(word) != len(word_from_dict):
        return False
    for i in range(len(word) - 1):
        if (word[:i] + word[i + 1] + word[i] + word[i + 2:]) == word_from_dict:
            return True
    return False


def is_typo(word, word_from_dict):
    sm = StringMatcher()
    sm.set_seq1(word)
    sm.set_seq2(word_from_dict)
    dist = sm.distance()
    return dist == 1 or (dist == 2 and fl(word, word_from_dict))


def run(path_to_typo_candidates, file_with_fixes):
    logger.info(f"Reading typo candidates from {path_to_typo_candidates}...")

    words_with_typos = []
    with open(path_to_typo_candidates, 'r') as f:
        for line in f:
            words_with_typos.append(line[:-1])

    general_dict = load_english_dict(os.path.join(base_project_dir, 'dicts', 'eng'))
    len_to_words_in_dict = defaultdict(list)
    for w in general_dict:
        len_to_words_in_dict[len(w)].append(w)
    len_to_words_in_dict.default_factory = None

    with open(file_with_fixes, 'w') as f:
        for word in tqdm(words_with_typos):
            possible_fixes = []
            for word_from_dict in get_words_of_almost_same_length(word, len_to_words_in_dict):
                if is_typo(word, word_from_dict):
                    possible_fixes.append(word_from_dict)
            stringified_possible_fixes = " ".join(possible_fixes)
            f.write(f"{word}|{stringified_possible_fixes}\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--path-to-typo-candidates', action='store', default="100_percent/splits/typo-candidates.txt")
    args = parser.parse_args()

    base_dir = base_from = os.path.join(base_project_dir, 'nn-data', 'new-framework')
    path_to_typo_candidates = os.path.join(base_dir, args.path_to_typo_candidates)
    file_with_fixes = os.path.join(os.path.split(path_to_typo_candidates)[0], 'typo-fixes.txt')

    run(path_to_typo_candidates, file_with_fixes)
