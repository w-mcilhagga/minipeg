# -*- coding: utf-8 -*-
"""
markdown parsing: block first, based on a line classification, then span.

Block level elements:
    
* heading
* fenced block ```name ... ```
* section :::name ... ::: (extension)
* blockquote
* list element
* paragraph
* html
* display equation
"""

# Tokenizing:
    
import re

block_prefixes = {
    'fence': lambda x: x.startswith('```'),
    'section': lambda x: x.startswith(':::'),
    'quote': lambda x: x.startswith('>'),
    'header': lambda x: x.startswith('#'),
    'olist_start': lambda x: re.compile(r'[0-9]\. ').match(x),
    'ulist_start': lambda x: re.compile(r'[-*+] ').match(x),
    'blank': lambda x: re.compile(r' *$').match(x),
}

def classify(line):
    for kind in block_prefixes:
        if block_prefixes[kind](line):
            return kind
    return 'normal'

def maketoken(line):
    # returns {kind, value}
    return {'kind':classify(line), 'value':line}

def tokenize_file(fname):
    with open(fname) as f:
        return [maketoken(line) for line in f]

# block grammar

from minipeg import Grammar, MatchToken, TokenState

# make token recognizers

def _is(kind):
    # the predicate for any kind
    return MatchToken(lambda tok: tok['kind']==kind)

def _isnot(kind):
    # the predicate for any not kind
    return MatchToken(lambda tok: tok['kind']!=kind)

# the block level grammar itself:

b = Grammar() 

b.blocks = (b.heading | 
           b.fence | 
           b.section | 
           b.blockquote | 
           b.ulistloose | b.ulisttight | 
           b.olistloose | b.olisttight | 
           b.paragraph | 
           b.blank)*0

# later, add b.displayeq, b.blockhtml

b.heading = _is('header')

# this grammar doesn't allow nested fences, but that should be allowed.

b.fence = _is('fence') & _isnot('fence')*0 & _is('fence') 

# section is an extension
b.section = _is('section') & _isnot('section')*0 & _is('section')

b.blockquote = _is('quote')*1

# lists can be loose or tight; loose lists have blanks between the elements
b.ulisttight = b.ulistelem*1
b.ulistloose = b.ulistelem & (_is('blank') & b.ulistelem)*1
b.ulistelem = _is('ulist_start') & _is('normal')*0

b.olistloose = b.olistelem & (_is('blank') & b.olistelem)*1
b.olisttight = b.olistelem*1
b.olistelem = _is('olist_start') & _is('normal')*0

b.paragraph = _is('normal')*1

b.blank = _is('blank')*1

if __name__ == '__main__':
    s = TokenState(tokenize_file('README.md'))
    s2 = b(s)
    s2.ast[0].dump()
    