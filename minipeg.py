# -*- coding: utf-8 -*-
"""
minipeg - using python operators to generate parsers
"""

class Node:
    """a node in a parse tree
    
    Args:
        parseobj -- the object/callable that created the node. If 
                the parse object has a name, the node is given that name.
        children -- the children of the node, which are themselves nodes
        
    Properties:
        span -- a list [start, finish] which includes the spans
                of all children (a span is the range of input which contains
                the node)
    """
    def __init__(self, parseobj, *children):
        """init"""
        if type(parseobj) is str:
            self.name = parseobj
        else:
            self.name = getattr(parseobj, 'name', parseobj)
        self.children = list(children)
        self.span = [children[0].span[0], children[-1].span[1]]
        
    def __getitem__(self, i):
        """node[i] returns the i-th child of the node"""
        return self.children[i]
    
    def __len__(self):
        """len(node) returns the number of children in the node"""
        return len(self.children)
    
    def dump(self, level=0, indent=4):
        """pretty print the node and children with indentation"""
        print(f'{" "*level}{self.name}:')
        for i,c in enumerate(self.children):
            c.dump(level+indent, indent)

class Leaf(Node):
    """a leaf node in a parse tree
    
    Args:
        parseobj -- the object/callable that created the node. If 
                the parse object has a name, the node is given that name.
        leaf -- the leaf node itself, usually a string or token
        span -- a list or tuple [start, finish] which gives the range of 
                input which contains the leaf
    """
    def __init__(self, parseobj, leaf, span):
        if type(parseobj) is str:
            self.name = parseobj
        else:
            self.name = getattr(parseobj, 'name', parseobj)
        self.leaf = leaf
        self.span = span
    
    def __len__(self):
        """returns 0 because a leaf has no children"""
        return 0

    def dump(self, level=0, indent=4):
        """pretty print the node with indentation"""
        print(f'{" "*level}{self.name}: "{self.leaf}"')
       

    
class ParseState:
    """records the current parse state
    
    """
    def __init__(self, input):
        self.input = input
        self.ast = []
        
    def clone(self):
        # clone and restore used for backtracking
        return dict(ast=[*self.ast])
    
    def restore(self, cloned):
        self.ast = cloned['ast']
    
    def group(self, parseobj, oldlen):
        # groups the tail of the ast into a node
        if oldlen<0:
            n = -oldlen
        else:
            n = len(self.ast)-oldlen
        if n>0:
            # node tagged by parseobj or name
            children = []
            for t in self.ast[-n:]:
                if t.name=='seq':
                    # anonymous sequences should be flattened
                    children += t.children
                else:
                    children.append(t)
            self.ast = self.ast[:-n]+[Node(parseobj, *children)]   
    
    def advance(self, n, node=False):
        # partial implementation of advance
        # (optionally) adds a node to the ast
        if node != False:
            self.ast.append(node)
            
# parse state

class TextState(ParseState):
    """state object for text input"""
    def __init__(self, input):
        super().__init__(input)
        self.rest = input # what's left
        
    def clone(self):
        # shallow copy of things
        return dict(rest=self.rest, **super().clone())
        
    def restore(self, cloned):
        # restores from a backup
        super().restore(cloned)
        self.rest = cloned['rest']

    def match(self, patt):
        # matches a string or regex to the start of rest
        # returns the matched string on success
        if type(patt) is str:
            return self.rest.startswith(patt) and patt
        else: # assumed regex
            result = patt.match(self.rest)
            return result and result.group(0)
    
    def advance(self, n, node=False):
        # moves rest forward & (optionally) adds a node to the ast
        super().advance(n, node)
        self.rest = self.rest[n:]
        
    def position(self):
        return len(self.input)-len(self.rest)



class TokenState(ParseState):
    """parsestate object for tokenized input"""
    def __init__(self, input):
        super().__init__(input)
        self.cursor = 0
        
    def clone(self):
        # shallow copy of things
        return dict(cursor=self.cursor, **super().clone())
        
    def restore(self, cloned):
        # restores from a backup
        super().restore(cloned)
        self.cursor = cloned['cursor']

    def match(self, predicate):
        # matches a token to a specification
        return predicate(self.input[self.cursor])
 
    def advance(self, n, node=False):
        # moves cursor forward & (optionally) adds a node to the ast
        super().advance(n, node)
        self.cursor += n
        
    def position(self):
        return self.cursor
            
"""
if A, B, C... are parser objects, then

A & B & C is a parser object that implements a sequence with backtracking
A | B | C is a parser object that implements alternatives
A*n does n or more copies of A
A[err] requires A to be successful, otherwise it raises the error
~A makes A optional; it is equivalent to  A | True

Ref() creates a forward reference for a parser.
"""


class Parser:
    # Parser(state) will change the state and return it if succeeded,
    # or leave state unchanged and return False if failed.
    
    def __and__(self, other):
        # self & other, a sequence
        return Seq(self, asparser(other))
    
    def __rand__(self, other):
        # other & self, a sequence
        return Seq(asparser(other), self)
    
    def __or__(self, other):
        # self | other, alternatives
        return Alt(self, asparser(other))

    def __ror__(self, other):
        # other | self, alternatives
        return Alt(asparser(other), self)
    
    def __invert__(self):
        # ~self, optional
        return Alt(self, BoolParser(True))
    
    def __mul__(self, n):
        # self[n], repeat at least n times
        return Repeat(self, n)
    
    def __getitem__(self, errcode):
        return Require(self, errcode)
    
    def __truediv__(self, name):
        # self/'name' , adds a name to the parser object
        self.name = name
        return self
            
def asparser(x):
    # changes primitives into parsers for binary operators
    if isinstance(x, Parser):
        return x
    if type(x) is str:
        return Match(x)
    if type(x) is bool:
        return BoolParser(x)
    if type(x) is re.Pattern:
        return MatchRe(x)
    if callable(x):
        # fingers crossed it's a parser
        return x
    raise ValueError('Not convertible to a parser')
    
    
class MatchToken(Parser):
    def __init__(self, predicate, save=True):
        self.pred = predicate
        self.name = 'token'
        self.save = save
    
    def __call__(self, state, backtrack=False):
        if state.match(self.predicate):
            p = state.position()
            state.advance(1,
                self.save and Leaf(self, self.token, [p, p+1]))
            # need to save the matched token
            return state
        else:
            return False            

class Match(Parser):
    # match a string to the start of the state
    def __init__(self, pattern, ws=True, save=True):
        self.pattern = pattern
        self.name = 'literal'
        self.ws = ws
        self.save = save
        
    def __call__(self, state, backtrack=False):
        if self.ws:
            Whitespace(state)
        if state.match(self.pattern):
            p = state.position()
            state.advance(len(self.pattern),
                self.save and Leaf(self, self.pattern, [p, p+len(self.pattern)]))
            return state
        else:
            return False
        
import re

class MatchRe(Parser):
    # match a regex to start of state.rest
    def __init__(self, pattern, ws=True, save=True):
        if type(pattern) is str:
            pattern = re.compile(pattern)
        self.re = pattern
        self.name = 're('+pattern.pattern+')'
        self.ws = ws
        self.save = save
        
    def __call__(self, state, backtrack=False):
        if self.ws:
            # note that this way does not backtrack over the ws
            # and requires whitespace to always succeed
            Whitespace(state)
        result = state.match(self.re)
        if result:
            p = state.position()
            state.advance(len(result),
                self.save and Leaf(self, result, [p,p+len(result)]))
            return state
        else:
            return False            

Whitespace = MatchRe(' *', ws=False, save=False)
    
class BoolParser(Parser):
    # a parser that's always true/false but does nothing
    def __init__(self, value):
        self.value = value
        
    def __call__(self, state, backtrack=False):
        return self.value and state
        
class Seq(Parser):
    # sequence of parsers with backtracking
    def __init__(self, L, R):
        self.L = L
        self.R = R
        self.name = 'seq'
        
    def __call__(self, state, backtrack=False):
        # backtrack says whether we are in a backtracking context
        if not backtrack:
            oldstate = state.clone()
        astlen = len(state.ast)
        if not (self.L(state, True) and self.R(state, True)):
            if not backtrack:
                state.restore(oldstate)
            return False
        state.group(self, astlen)
        return state
    
class Alt(Parser):
    # alternative parsers
    def __init__(self, L, R):
        self.L = L
        self.R = R
        self.name = 'alt'
        
    def __call__(self, state, backtrack=False):
        # ignore the backtrack
        astlen = len(state.ast)
        if self.L(state) or self.R(state):
            if self.name!='alt':
                state.group(self, astlen)
            return state
        return False
    
class Repeat(Parser):
    def __init__(self, p, n):
        self.parser = p
        self.n = n
        
    def __call__(self, state, backtrack=False):
        # do the minimum number of parses with backtracking
        if not backtrack:
            oldstate = state.clone()
        for i in range(self.n):
            if not self.parser(state, True):
                if not backtrack:
                    state.restore(oldstate)
                return False
        # do zero or more parses, each of which looks after its
        # own backtrack
        while self.parser(state):
            pass
        return state
    
class Ref(Parser):
    # forward reference
    def __init__(self):
        self.parser = None
        self.name = None
        
    def set(self, parser):
        self.parser = parser
        
    def __call__(self, state, backtrack=False):
        return self.parser(state, backtrack)
    
    def __truediv__(self, name):
        self.name = name
        self.parser/name
        return self
    
class Require(Parser):
    def __init__(self, required, errcode):
        self.parser = required
        self.errcode = errcode
        
    def __call__(self, state, backtrack=False):
        if self.parser(state, backtrack):
            return state
        else:
            raise RuntimeError(dict(position=state.position(), errorcode=self.errcode))

class Grammar(Parser):
    # something to make forward references & naming easy
    def __init__(self, p=None):
        self.__dict__['parsername'] = p
    
    def __getattr__(self, attr):
        # create a forward reference to the rule
        object.__setattr__(self, attr, Ref())
        return getattr(self, attr)
    
    def __setattr__(self, attr, value):
        # create or fill in an attribute
        if attr in self.__dict__:
            g = getattr(self, attr)
            if type(g) is Ref:
                g.set(value)
                g/attr
                return
        self.__dict__[attr] = value
        value/attr
        
    def __call__(self, state, backtrack=False):
        return getattr(self, self.parsername)(state, backtrack)
