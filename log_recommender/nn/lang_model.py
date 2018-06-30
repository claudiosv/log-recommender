import json
from collections import defaultdict
from time import time

import deepdiff
import matplotlib
matplotlib.use('Agg')

from nn.params import nn_params, Mode
from nn.utils import to_test_mode, back_to_train_mode, beautify_text, gen_text


import logging
import os

import pandas

import torch
from functools import partial

from fastai.core import USE_GPU
from fastai.metrics import top_k, MRR
from fastai.nlp import LanguageModelData, seq2seq_reg
import dill as pickle
from fastai import metrics
from torchtext import data

logging.basicConfig(level=logging.DEBUG)

nn_arch = nn_params['arch']
nn_testing = nn_params['testing']

def display_not_guessed_examples(examples, vocab):
    exs = []
    for input, num, preds, target in examples:
        exs.append((
            beautify_text(" ".join([vocab.itos[inp]
                                    if ind != num + 1 else "[[[" + vocab.itos[inp] + "]]]"
                                    for ind, inp in enumerate(input)])),
            num,
            [vocab.itos[p] for p in preds],
            vocab.itos[target]
    ))
    for ex in exs:
        logging.info(f'                    ... {ex[0]}')
        logging.info(f'                    ... {ex[1]}')
        logging.info(f'                    ... {ex[2]}')
        logging.info(f'                    ... {ex[3]}')
        logging.info(f'===============================================')


def calc_and_display_top_k(rnn_learner, metric, vocab):
    spl = metric.split("_")
    cat_index = spl.index("cat")
    if cat_index == -1 or len(spl) <= cat_index + 1:
        raise ValueError(f'Illegal metric format: {metric}')
    ks = list(map(lambda x: int(x), spl[1: cat_index]))
    cat = int(spl[cat_index + 1])

    accuracies, examples = top_k(*rnn_learner.predict_with_targs(True), ks, cat)

    logging.info(f'Current tops are ...')
    logging.info(f'                    ... {accuracies}')
    if spl[-1] == 'show':
        display_not_guessed_examples(examples, vocab)


def calculate_and_display_metrics(rnn_learner, metrics, vocab):
    for metric in metrics:
        if metric.startswith("topk"):
            calc_and_display_top_k(rnn_learner, metric, vocab)
        elif metric == 'mrr':
            mrr = MRR(*rnn_learner.predict_with_targs(True))
            logging.info(f"mrr: {mrr}")


def create_df(dir):
    lines = []
    for root, dirs, files in os.walk(dir):
        for file in files:
            with open(os.path.join(root, file), 'r') as f:
                lines.extend([line for line in f])
    if not lines:
        raise ValueError(f"No data available: {dir}")
    return pandas.DataFrame(lines)


def get_model(model_name):
    dataset_name = nn_params["dataset_name"]
    path_to_dataset = f'{nn_params["path_to_data"]}/{dataset_name}'
    path_to_model = f'{path_to_dataset}/{model_name}'

    train_df = create_df(f'{path_to_dataset}/train/')
    test_df = create_df(f'{path_to_dataset}/test/')

    text_field = data.Field()
    languageModelData = LanguageModelData.from_dataframes(path_to_model,
                                                          text_field, 0, train_df, test_df, test_df,
                                                          bs=nn_arch["bs"],
                                                          bptt=nn_arch["bptt"],
                                                          min_freq=nn_arch["min_freq"]
                                                          # not important since we remove rare tokens during preprocessing
                                                          )
    pickle.dump(text_field, open(f'{path_to_dataset}/TEXT.pkl', 'wb'))

    logging.info(f'Dictionary size is: {len(text_field.vocab.itos)}')

    opt_fn = partial(torch.optim.Adam, betas=nn_arch['betas'])

    rnn_learner = languageModelData.get_model(opt_fn, nn_arch['em_sz'], nn_arch['nh'], nn_arch['nl'],
                                              dropouti=nn_arch['drop']['outi'],
                                              dropout=nn_arch['drop']['out'],
                                              wdrop=nn_arch['drop']['w'],
                                              dropoute=nn_arch['drop']['oute'],
                                              dropouth=nn_arch['drop']['outh'])
    rnn_learner.reg_fn = partial(seq2seq_reg, alpha=nn_arch['reg_fn']['alpha'], beta=nn_arch['reg_fn']['beta'])
    rnn_learner.clip = nn_arch['clip']

    logging.info(rnn_learner)

    try:
        rnn_learner.load(dataset_name)
        model_trained = True
        # calculate_and_display_metrics(rnn_learner, nn_params['metrics'], text_field.vocab)
    except FileNotFoundError:
        logging.warning(f"Model {dataset_name}/{model_name} not found")
        model_trained = False

    return rnn_learner, text_field, model_trained

def run_and_display_tests(m, text_field, path_to_save):
    to_test_mode(m)
    print("==============        TESTS       ====================")

    text = gen_text(m, text_field, nn_testing["starting_words"], nn_testing["how_many_words"])

    beautified_text = beautify_text(text)
    print(beautified_text)
    with open(path_to_save, 'w') as f:
        f.write(beautified_text)

    back_to_train_mode(m, nn_arch['bs'])

PARAM_FILE_NAME = 'params.json'
DEEPDIFF_ADDED = 'dictionary_item_added'
DEEPDIFF_REMOVED = 'dictionary_item_removed'
DEEPDIFF_CHANGED = 'values_changed'

def find_most_similar_config(path_to_dataset, current_config):
    config_dict = defaultdict(list)
    for (dirpath, dirnames, filenames) in os.walk(path_to_dataset):
        for dirname in dirnames:
            file_path = os.path.join(dirpath, dirname, PARAM_FILE_NAME)
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    config = json.load(f)
                dd = deepdiff.DeepDiff(config, current_config)
                if dd == {}:
                    return dirname, {}
                else:
                    n_changed_params=(len(dd[DEEPDIFF_ADDED]) if DEEPDIFF_ADDED in dd else 0) \
                                     + (len(dd[DEEPDIFF_CHANGED]) if DEEPDIFF_CHANGED in dd else 0) \
                                     + (len(dd[DEEPDIFF_REMOVED]) if DEEPDIFF_REMOVED in dd else 0)
                    config_dict[n_changed_params].append((dirname, dd))
    if not config_dict:
        return None, deepdiff.DeepDiff({}, current_config)
    else:
        return config_dict[min(config_dict)][-1]

def extract_last_key(keys):
    last_apostrophe = keys.rindex('\'')
    return keys[keys[:last_apostrophe].rindex('\'') + 1:last_apostrophe]


def find_name_for_new_config(config_diff):
    name = ""
    if DEEPDIFF_CHANGED in config_diff:
        for key, val in config_diff[DEEPDIFF_CHANGED].items():
            name += extract_last_key(key)
            name += "_"
            name += str(val['new_value'])
            name += "_"
    if DEEPDIFF_ADDED in config_diff:
        for key in config_diff[DEEPDIFF_ADDED]:
            name += extract_last_key(key)
            name += "_"
    if DEEPDIFF_REMOVED in config_diff:
        for key in config_diff[DEEPDIFF_REMOVED]:
            name += extract_last_key(key)
            name += "_"
    if name:
        name = name[:-1]
    return name


def printGPUInfo():
    logging.info("Using GPU: " + str(USE_GPU))
    if USE_GPU:
        logging.info("Number of GPUs available: " + str(torch.cuda.device_count()))


def get_model_name_by_params():
    folder, config_diff = find_most_similar_config(path_to_dataset, nn_arch)
    if config_diff == {}:
        return folder
    else: #nn wasn't run with this config yet
        name = find_name_for_new_config(config_diff) if folder is not None else "baseline"
        path_to_model = f'{path_to_dataset}/{name}'
        while os.path.exists(path_to_model):
            name = name + "_"
            path_to_model = f'{path_to_dataset}/{name}'
        return name

def find_and_plot_lr(rnn_learner, path_to_model):
    logging.info("Looking for the best learning rate...")
    rnn_learner.lr_find()

    dir = os.path.dirname(os.path.realpath(__file__))
    path = os.path.join(dir, path_to_model, 'lr_finder_plot.png')
    rnn_learner.sched.plot(path)
    logging.info(f"Plot is saved to {path}")


def train_model(rnn_learner, path_to_dataset, model_name):
    dataset_name = nn_params["dataset_name"]
    training_start_time = time()
    vals, ep_vals = rnn_learner.fit(nn_params['lr'], n_cycle=nn_arch['cycle']['n'], wds=nn_arch['wds'],
                                    cycle_len=nn_arch['cycle']['len'], cycle_mult=nn_arch['cycle']['mult'],
                                    metrics=list(map(lambda x: getattr(metrics, x), nn_arch['training_metrics'])),
                                    cycle_save_name=dataset_name, get_ep_vals=True, best_model_save=f'{dataset_name}_best')
    training_time_mins = int(time() - training_start_time) // 60
    with open(f'{path_to_dataset}/{model_name}/results.out', 'w') as f:
        f.write(str(training_time_mins) + "\n")
        for _, vals in ep_vals.items():
            f.write(" ".join(map(lambda x: str(x), vals)) + "\n")

    logging.info(f'Saving model: {dataset_name}/{model_name}')
    rnn_learner.save(dataset_name)
    rnn_learner.save_encoder(dataset_name + "_encoder")


if __name__ =='__main__':
    printGPUInfo()
    logging.info("Using the following parameters:")
    logging.info(nn_arch)
    path_to_dataset = f'{nn_params["path_to_data"]}/{nn_params["dataset_name"]}'
    force_rerun = True
    # if "model_name" in nn_params:
    #     logging.info(f'')
    #     model_name = nn_params["model_name"]
    # else:
    model_name = get_model_name_by_params()
    path_to_model = f'{path_to_dataset}/{model_name}'

    if not os.path.exists(path_to_model):
        os.mkdir(path_to_model)

    learner, text_field, model_trained = get_model(model_name)
    vocab_file = f'{path_to_dataset}/TEXT.pkl'
    if not os.path.exists(vocab_file):
        with open(vocab_file, 'w') as f:
            f.dump(text_field)
    if not model_trained or force_rerun:
        with open(f'{path_to_model}/{PARAM_FILE_NAME}', 'w') as f:
            json.dump(nn_arch, f)
        # with open(f'{path_to_dataset}/{name}/config_diff.json', 'w') as f:
        #     json.dump(config_diff, f)

        if nn_params['mode'] is Mode.LEARNING_RATE_FINDING:
            if model_trained:
                logging.info(f"Forcing lr-finder rerun")
            find_and_plot_lr(learner, f'{path_to_dataset}/{model_name}')
        elif nn_params['mode'] is Mode.TRAINING:
            if model_trained:
                logging.info(f"Forcing training rerun")
            train_model(learner, path_to_dataset, model_name)
            m = learner.model
            run_and_display_tests(m, text_field, f'{path_to_model}/gen_text.out')
        else:
            raise AssertionError("Unknown mode")
    else:
        logging.info(f'Model {nn_params["dataset_name"]}/{model_name} already trained. Not rerunning training.')
