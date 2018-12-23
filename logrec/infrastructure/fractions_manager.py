import logging
import os
import pandas

from logrec.util.io_utils import file_mapper

logger = logging.getLogger(__name__)

N_CHUNKS = 1000

def check_max_precision(fl, prec):
    n = int(fl * 10 ** prec) / float(10 ** prec)
    return n == fl


def check_value_ranges(percent, start_from):
    if percent <= 0.0 or percent > 100.0:
        raise ValueError(f"Wrong value for percent: {percent}")
    if start_from < 0.0:
        raise ValueError(f"Start from cannot be negative: {start_from}")
    if percent + start_from > 100.0:
        raise ValueError(f"Wrong values for percent ({percent}) "
                         f"and ({start_from})")


def normalize_string(val):
    if int(val * 10) % 10 == 0:
        return f'{int(val)}'
    else:
        return f'{val:.1f}'


def normalize_percent_data(percent, start_from):
    check_max_precision(percent, 1)
    check_max_precision(start_from, 1)
    check_value_ranges(percent, start_from)
    return normalize_string(percent), normalize_string(start_from)


def get_chunk_prefix(filename):
    underscore_index = filename.index("_")
    if underscore_index == -1:
        raise ValueError(f"Filename is not in format <chunk>_<model name>: {filename}")
    return filename[:underscore_index]


def include_to_df(filename, percent, start_from):
    basename = os.path.basename(filename)
    if basename.startswith("_"):
        return False
    chunk = float(get_chunk_prefix(basename))
    return start_from <= chunk < percent * N_CHUNKS * 0.01


def include_to_df_tester(percent, start_from):
    def tmp(filename):
        return 1 if include_to_df(filename, percent, start_from) else 0

    return tmp


def create_df(dir, percent, start_from):
    lines = []
    files_total = sum(f for f in file_mapper(dir, include_to_df_tester(percent, start_from),
                                             extension=None, ignore_prefix="_"))

    cur_file = 0
    for root, dirs, files in os.walk(dir):
        for file in files:
            with open(os.path.join(root, file), 'r') as f:
                if include_to_df(file, percent, start_from):
                    cur_file += 1
                    logger.info(f'Adding {os.path.join(root, file)} to dataframe [{cur_file} out of {files_total}]')
                    lines.extend([line for line in f])
    if not lines:
        raise ValueError(f"No data available: {os.path.abspath(dir)}")
    return pandas.DataFrame(lines)