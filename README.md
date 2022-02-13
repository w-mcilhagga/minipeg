# minipeg
A minimal tool for creating [peg parsers](https://en.wikipedia.org/wiki/Parsing_expression_grammar) in python from expressions that look a lot like [EBNF](https://en.wikipedia.org/wiki/Extended_Backus%E2%80%93Naur_form) .

## Example

A simple EBNF grammar for arithmetic expressions could be

```EBNF
expr = term { add_op term} ;
add_op = '+' | '-' ;
term = factor { mult_op factor } ;
mult_op = '*' | '/' ;
factor = number ['^' factor] | bracket ;
bracket = '(' expression ')' ;
number = ['+'|'-'] digit {digit} ;
```

In `minipeg`, this would be written as:

```python
from minipeg import Grammar, Match, MatchRe

g = Grammar()

g.expr = g.term & (g.add_op & g.term)*0
g.add_op = Match('+') | '-'
g.term = g.factor & (g.mult_op & g.factor)*0
g.mult_op = Match('*') | '/'
g.factor = g.number & ~('^' & g.factor) | g.bracket
g.bracket = '(' & g.expr & ')'
g.number = MatchRe(r'(\+|-)?[0-9]+')
```

`minipeg` works by overloading operators and playing games with `__setattr__` and `__getattr__`.

## Equivalents between EBNF and `minipeg`.

The equivalents between EBNF and `minipeg` are:

* concatenation:
  - EBNF:   `A B C`
  - minipeg:  `A & B & C`
* alternation:
  - EBNF: `A|B|C`
  - minipeg: `A|B|C`
* optional:
  - EBNF: `[A]`
  - minipeg: `~A`
* repetition:
  - EBNF: `{A}` to repeat zero or more times
  - minipeg: `A*0` to repeat at least zero times, `A*n` to repeat at least n times
* terminal string:
  - EBNF: `"..."` or `'...'`
  - minipeg: `Match('...')` or `MatchRe('...')` if the string is a regular expression pattern

Note that in the example, strings are sometimes inside `Match` calls and sometimes not. When a builtin type is combined with a Parser object, the Parser operator overrides will convert the builtin type to a Parser of (usually) the appropriate kind. However, this won't work with strings. Thus `'+'|'-'` will yield an error, but `Match('+')|'-'` creates a parser object `Match('+')` which applies a conversion to the `'-'` string when its `__or__` method is called.

`minipeg` expressions of course follow python's operator precendence rules.

## Running the Parser.
Once the grammar `g` has been defined, it can be run on a string input as follows:

```python
from minipeg import TextState

state = g(TextState('  (1+345^2) / 3*7-4'))
```

A `TextState` object takes a string input, keeps track of the state of the parse, and stores the ast. 
The grammar object `g` will use the first defined rule `g.expr` by default when parsing, but you can 
explicitly call any other rule on a state object. 

If the parse succeeds, the resultant state object has an `ast` attribute which is a list containing 
the parse tree as its first element. If the parse fails, the return value is either `False`, or 
an exception is thrown ( when error parsers have been defined).

The ast can be inspected by calling `state.ast[0].dump()`. In this case, the dump looks like this:

```
expr:
    term:
        factor:
            bracket:
                literal: "("
                expr:
                    term:
                        factor:
                            number: "1"
                    add_op:
                        literal: "+"
                    term:
                        factor:
                            number: "345"
                            literal: "^"
                            factor:
                                number: "2"
                literal: ")"
        mul_op:
            literal: "/"
        factor:
            number: "3"
        mul_op:
            literal: "*"
        factor:
            number: "7"
    add_op:
        literal: "-"
    term:
        factor:
            number: "4"
```

Each named parser expression creates a node in the tree. 