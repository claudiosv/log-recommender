import logging
import os
import re

from torchtext import data

from logrec.classifier.utils import get_dir_and_file
from logrec.dataprep import TRAIN_DIR, TEST_DIR
from logrec.util import io_utils
from logrec.util.io_utils import file_mapper

__author__ = 'hlib'

logger = logging.getLogger(__name__)

IGNORED_PROJECTS_FILE_NAME = "ignored_projects"

class ContextsDataset(data.Dataset):
    FW_CONTEXTS_FILE_EXT = "context.forward"
    BW_CONTEXTS_FILE_EXT = "context.backward"
    LABEL_FILE_EXT = "label"

    @staticmethod
    def sort_key(ex):
        return len(ex.text)

    @staticmethod
    def _get_pair(file_path):
        c_file_path = re.sub(f'{ContextsDataset.LABEL_FILE_EXT}$',
                             f'{ContextsDataset.FW_CONTEXTS_FILE_EXT}',
                             file_path)
        return c_file_path, file_path


    def __init__(self, path, text_field, label_field, **kwargs):
        """Create an IMDB dataset instance given a path and fields.

        Arguments:
            path: Path to the dataset's highest level directory
            text_field: The field that will be used for text data.
            label_field: The field that will be used for label data.
            Remaining keyword arguments: Passed to the constructor of
                data.Dataset.
        """
        threshold = kwargs.pop("threshold", 0.0)
        path_to_ignored_projects = os.path.join(path, '..', f"{IGNORED_PROJECTS_FILE_NAME}.{threshold}")
        logger.info(f"Loading ignored projects from {path_to_ignored_projects} ...")
        ignored_projects_set = set(io_utils.read_list(path_to_ignored_projects))

        fields = [('text', text_field), ('label', label_field)]
        examples = []

        for c_filename, l_filename in file_mapper(path, ContextsDataset._get_pair, extension='label'):
            proj_name = re.sub(f"\.{ContextsDataset.LABEL_FILE_EXT}$", "", get_dir_and_file(l_filename))
            if proj_name in ignored_projects_set:
                continue

            c_file = None
            l_file = None
            try:
                c_file = open(c_filename, 'r')
                l_file = open(l_filename, 'r')
                for context, level in zip(c_file, l_file):
                    level = level.rstrip('\n')
                    if level:
                        example = data.Example.fromlist([context, level], fields)
                        examples.append(example)
            except FileNotFoundError:
                project_name = c_filename[:-len(ContextsDataset.FW_CONTEXTS_FILE_EXT)]
                logger.error(f"Project context not loaded: {project_name}")
                continue
            finally:
                if c_file is not None:
                    c_file.close()
                if l_file is not None:
                    l_file.close()

        if not examples:
            raise ValueError(f"Examples list is empty")

        logger.debug(f"Number of examples gathered from {path}: {len(examples)} ")
        super(ContextsDataset, self).__init__(examples, fields, **kwargs)

    @classmethod
    def splits(cls, text_field, label_field, path, train=TRAIN_DIR, test=TEST_DIR, **kwargs):
        """Create dataset objects for splits of the IMDB dataset.

        Arguments:
            text_field: The field that will be used for the sentence.
            label_field: The field that will be used for label data.
            root: Root dataset storage directory. Default is '.data'.
            train: The directory that contains the training examples
            test: The directory that contains the test examples
            Remaining keyword arguments: Passed to the splits method of
                Dataset.
        """
        return super(ContextsDataset, cls).splits(
            path=path, text_field=text_field, label_field=label_field,
            train=train, validation=None, test=test, **kwargs)
