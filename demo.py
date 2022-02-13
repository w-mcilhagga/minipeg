# -*- coding: utf-8 -*-
  
from minipeg import Grammar, Match, MatchRe, TextState

def printstate(s, backtrack=False):
    s.ast[-1].print()
    return s
    
def rename(name):
    def rename_parser(state, backtrack=False):
        state.ast[-1].name = name
        return state
    return rename_parser
    
def makepower(state, backtrack=False):
    if state.ast[-1].name == 'seq' and len(state.ast[-1])==3:
        state.group('power', -1)
    return state

g = Grammar('expr')
g.expr = g.term & (g.add_op & g.term)*0
g.add_op = Match('+') | '-'
g.term = g.factor & (g.mul_op & g.factor)*0
g.mul_op = Match('*') | '/'
g.factor = g.number & ~('^' & g.factor) & makepower | g.bracket
g.number = MatchRe('[0-9]+')
g.bracket = '(' & g.expr & Match(')')[1]


s=g(TextState('  (1+345^2) / 3*7-4'))
s.ast[0].dump()