from enum import Enum, auto

from torchtext import data


class Mode(Enum):
    TRAINING = auto()
    LEARNING_RATE_FINDING = auto()
    # ONLY_TESTING = auto()


nn_params = {
    'path_to_data': '../nn-data/',
    'dataset_name': 'guess_possition_566_2_context_lines',
    # 'model_name': 'baseline',
    'arch': {
        'bs': 16,
        'bptt': 10,
        'em_sz': 300,  # size of each embedding vector
        'nh': 300,     # number of hidden activations per layer
        'nl': 3,       # number of layers
        'min_freq': 0,
        'betas': [0.7, 0.99],
        'clip': 0.3,
        'reg_fn': {'alpha': 2, 'beta': 1},
        'drop': {'outi': 0.05, 'out': 0.05, 'w':0.1, 'oute': 0.02, 'outh': 0.05},
        'wds': 1e-6,
        'cycle': {'n': 1, 'len': 1, 'mult': 2},
        'training_metrics': ['accuracy', 'mrr']
    },
    'lr': 1e-3,
    'metrics': ['topk_1_10_100_cat_2', 'mrr'],
    'testing': {
        'how_many_words': 2000,
        'starting_words': "loading"
    },
    'mode': Mode.LEARNING_RATE_FINDING
}

LEVEL_LABEL = data.Field(sequential=False)