import logging
from typing import List, Union, Optional

from torchtext.data import Field

from fastai.core import to_np, to_gpu, F, Variable
from fastai.lm_rnn import SequentialRNN
from fastai.metrics import top_k, MRR

import torch

from fastai.nlp import RNN_Learner
from logrec.dataprep.text_beautifier import beautify_text

logger = logging.getLogger(__name__)


def get_predictions(model: SequentialRNN, input_field: Field, prepared_input: Union[List[str], List[List[str]]],
                    max_n_predictions: int) -> (Variable, Variable):
    t = to_gpu(input_field.numericalize(prepared_input, -1))
    res, *_ = model(t)
    last_res = res[-1]
    n_predictions = min(max_n_predictions, last_res.size()[0])
    outputs, labels = torch.topk(last_res, n_predictions)
    probs = F.softmax(outputs)
    return probs, labels


def format_predictions(probs: Variable, labels: Variable, output_field: Field, actual_label: Optional[str]) -> str:
    text = ""
    for probability, label in map(to_np, zip(probs, labels)):
        uu = f'{output_field.vocab.itos[label[0]]}: {probability}'
        text += (uu + "\n")
    text += f'Actual label: {actual_label}\n'
    return text


def gen_text(learner: RNN_Learner, starting_words_list: List[str], how_many_to_gen: int) -> List[str]:
    text = []
    t = to_gpu(learner.text_field.numericalize([starting_words_list], -1))
    res, *_ = learner.model(t)
    for i in range(how_many_to_gen):
        n = torch.multinomial(res[-1].exp(), 1)
        # n = n[1] if n.data[0] == 0 else n[0]
        text.append(learner.text_field.vocab.itos[n.data[0]])
        res, *_ = learner.model(n[0].unsqueeze(0))
    return text


def to_test_mode(model: SequentialRNN):
    # Set batch size to 1gen_te
    model[0].bs = 1
    # Turn off dropout
    model.eval()
    # Reset hidden state
    model.reset()


def back_to_train_mode(m, bs):
    # Put the batch size back to what it was
    m[0].bs = bs

def display_not_guessed_examples(examples, vocab):
    exs = []
    for input, num, preds, target in examples:
        exs.append((
            beautify_text(" ".join([vocab.itos[inp]
                                    if ind != num + 1 else "[[[" + vocab.itos[inp] + "]]]"
                                    for ind, inp in enumerate(input)])),
            [vocab.itos[p] for p in preds],
            vocab.itos[target]
    ))
    for ex in exs:
        logger.info(f'                    ... {ex[0]}')
        logger.info(f'                    ... {ex[1]}')
        logger.info(f'                    ... {ex[2]}')
        logger.info(f'===============================================')


def calc_and_display_top_k(rnn_learner, metric, vocab):
    spl = metric.split("_")
    cat_index = spl.index("cat")
    if cat_index == -1 or len(spl) <= cat_index + 1:
        raise ValueError(f'Illegal metric format: {metric}')
    ks = list(map(lambda x: int(x), spl[1: cat_index]))
    cat = int(spl[cat_index + 1])

    accuracies, examples = top_k(*rnn_learner.predict_with_targs(True), ks, cat)

    logger.info(f'Current tops are ...')
    logger.info(f'                    ... {accuracies}')
    if spl[-1] == 'show':
        display_not_guessed_examples(examples, vocab)


def calculate_and_display_metrics(rnn_learner, metrics, vocab):
    for metric in metrics:
        if metric.startswith("topk"):
            calc_and_display_top_k(rnn_learner, metric, vocab)
        elif metric == 'mrr':
            mrr = MRR(*rnn_learner.predict_with_targs(True))
            logger.info(f"mrr: {mrr}")


