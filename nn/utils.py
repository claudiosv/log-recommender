import torch
import warnings

from sklearn.metrics import fbeta_score

from fastai.core import to_np


def f2(preds, targs):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        preds = torch.max(preds, dim=1)[1]
        return fbeta_score(targs.data, preds, 2, average='weighted')


def output_predictions(m, input_field, output_field, starting_text, how_many):
    words = [starting_text.split()]
    t=input_field.numericalize(words, -1)

    res,*_ = m(t)

    #==========================output predictions

    probs, labels = torch.topk(res[-1], how_many)
    print("===================")
    print(beautify_text(starting_text))
    for probability, label in map(to_np, zip(probs, labels)):
        print(f'{output_field.vocab.itos[label[0]]}: {probability}')


def gen_text(m, text_field, starting_words, how_many_to_gen):
    text = ''
    t = text_field.numericalize([starting_words.split()], -1)
    res, *_ = m(t)
    for i in range(how_many_to_gen):
        n = torch.multinomial(res[-1].exp(), 1)
        # n = n[1] if n.data[0] == 0 else n[0]
        text += text_field.vocab.itos[n.data[0]] + ' '
        res, *_ = m(n[0].unsqueeze(0))
    text += '...'
    return text

def beautify_text(text):
    text = text.replace('<eos>', '\n').replace('\\n', '\n').replace('<ect>', '\n\n').replace('<identifiersep>', '_')
    for i in range(1,11):
        text = text.replace('\\t'+str(i), ' ' * 4 * i)
    text = text.replace(' _ ', '_').replace(' . ', '.')
    return text


def to_test_mode(m):
    # Set batch size to 1
    m[0].bs = 1
    # Turn off dropout
    m.eval()
    # Reset hidden state
    m.reset()


def back_to_train_mode(m, bs):
    # Put the batch size back to what it was
    m[0].bs = bs