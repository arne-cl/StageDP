#!/usr/bin/env python3.5
# -*- coding: utf-8 -*-

import os
import gzip
import pickle
import argparse
import sys

from pycorenlp import StanfordCoreNLP

from models.parser import RstParser
from utils.token import Token
from utils.document import Doc
from nltk import Tree


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file')
    parser.add_argument('output_file', nargs='?', default=sys.stdout)
    return parser.parse_args()


def create_doc_from_plaintext_file(text_file, annotate_func):
    with open(text_file, 'r') as fin:
        input_text = fin.read()
        doc_tokens = []
        
        sentences = annotate_func(input_text)['sentences']
        for sidx, sent in enumerate(sentences):
            sent_tokens = []
            for t in sent['tokens']:
                token = Token()
                token.tidx, token.word, token.lemma, token.pos = t['index'], t['word'], t['lemma'], t['pos']

                # Our input is not annotated with paragraph/sentence/EDU boundaries,
                # so the paragraph index (pidx) is always 1 and the
                # EDU index (edudix) always equals the sentence number (sidx + 1).
                #
                # Don't ask me why sidx starts counting at 0, but pidx and eduidx start at 1.
                token.pidx = 1
                token.sidx = sidx
                token.eduidx = sidx + 1
                sent_tokens.append(token)
            for dep in sent['basicDependencies']:
                dependent_token = sent_tokens[dep['dependent']-1]
                dependent_token.hidx = dep['governor']
                dependent_token.dep_label = dep['dep']
            doc_tokens += sent_tokens

    doc = Doc()
    doc.init_from_tokens(doc_tokens)
    return doc



def main():
    args = parse_args()
    parser = RstParser()
    parser.load('../data/model')
    with gzip.open('../data/resources/bc3200.pickle.gz') as fin:
        print('Load Brown clusters for creating features ...')
        brown_clusters = pickle.load(fin)
    core_nlp = StanfordCoreNLP('http://localhost:9000')

    annotate_plaintext = lambda x: core_nlp.annotate(x, properties={
        'annotators': 'tokenize,ssplit,pos,lemma,parse,depparse',
        'outputFormat': 'json'
    })

    doc = create_doc_from_plaintext_file(args.input_file, annotate_func=annotate_plaintext)
    
    pred_rst = parser.sr_parse(doc, brown_clusters)
    tree_str = pred_rst.get_parse()
    pprint_tree_str = Tree.fromstring(tree_str).pformat(margin=150) + '\n'
    
    if isinstance(args.output_file, str):
        with open(args.output_file, 'w') as fout:
            fout.write(pprint_tree_str)
    else:
        sys.stdout.write(pprint_tree_str)


if __name__ == '__main__':
    main()
