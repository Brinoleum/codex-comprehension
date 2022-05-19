#!/usr/bin/env python

import json
import ast

class RemoveDocstring(ast.NodeTransformer):
    
    def visit_FunctionDef(self, node):
        match node.body[0]:
            case ast.Constant(value=some_val):
                if type(some_val) == str:
                    node.body = node.body[1:]
                return node
            case _:
                return node
    
class ReplaceMapFilter(ast.NodeTransformer):
    '''
    takes the ast node for a function call to map or filter
    and transforms them into list comprehensions

    map(f, xs) -> [f(x) for x in xs]
    filter(f, xs) -> [x for x in xs if f(x)]
    
    because reduce tracks state it needs at least one line to track the current value so far and another to iterate
    to fit it in where a single value is expected is hard to implement and to read even for humans so it's unlikely GPT-3 can understand it
    '''
    def visit_Call(self, node):
        match node.func:
            case ast.Name(id='map'):
                self.generic_visit(node)
                func = node.args[0]
                it = node.args[1]
                return ast.ListComp(elt=ast.Call(func=func,
                                                 args=[ast.Name(id='list_element', ctx=ast.Load())],
                                                 keywords=[]),
                                    generators=[ast.comprehension(
                                                    target=ast.Name(id='list_element', ctx=ast.Store()),
                                                    iter=it,
                                                    ifs=[],
                                                    is_async=0)])
            case ast.Name(id='filter'):
                self.generic_visit(node)
                func = node.args[0]
                it = node.args[1]
                return ast.ListComp(elt=ast.Name(id='list_element', ctx=ast.Load()),
                                    generators=[ast.comprehension(
                                                    target=ast.Name(id='list_element', ctx=ast.Store()),
                                                    iter=it,
                                                    ifs=[ast.Call(func=func,
                                                                  args=[ast.Name(id='list_element', ctx=ast.Load())],
                                                                  keywords=[])],
                                                    is_async=0)])
            case _:
                self.generic_visit(node)
                return node
    
class ReplaceFor(ast.NodeTransformer):
    '''
    takes a for loop and converts it into a while loop
    for x in xs:
        ...x...
    
    gets mapped to

    sequence_iterator = iter(xs)
    while True:
        try:
            x = next(sequence_iterator)
            ...x...
        except StopIteration:
            break
    '''
    def __init__(self):
        self.iterator_index = 0

    def visit_For(self, node):
        self.generic_visit(node)
        self.iterator_index = self.iterator_index + 1
        iter_assign = ast.Assign(targets=[ast.Name(id='sequence_iterator'+str(self.iterator_index), ctx=ast.Store())],
                                 value=ast.Call(func=ast.Name(id='iter', ctx=ast.Load()), 
                                                args=[node.iter], 
                                                keywords=[]))
        while_loop = ast.While(test=ast.Constant(value=True),
                               body=[ast.Try(body=[ast.Assign(targets=[node.target],
                                                              value=ast.Call(func=ast.Name(id='next', ctx=ast.Load()),
                                                                             args=[ast.Name(id='sequence_iterator'+str(self.iterator_index), ctx=ast.Load())],
                                                                             keywords=[]))] + node.body,
                                             handlers=[ast.ExceptHandler(type=ast.Name(id='StopIteration', ctx=ast.Load()),
                                                                         body=[ast.Break()])],
                                             orelse=[], 
                                             finalbody=[])],
                               orelse=[])
        return [iter_assign, while_loop]

class ReplaceReduce(ast.NodeTransformer):
    '''
    y = reduce(f, xs, initial?) ->

    reduce_iter = iter(xs)
    y = next(reduce_iter) OR y = initial IF initial exists
    for iter_element in reduce_iter:
        y = f(y, iter_element)
    '''

    def __init__(self):
        self.iter_index = 0
        
    def visit_Assign(self, node):
        match node.value:
            case ast.Call(func=ast.Name(id='reduce')) as reduce_func:
                self.iter_index = self.iter_index + 1
                target = node.targets[0] # assume single assignment, not like a = b = 1
                func = reduce_func.args[0]
                it = reduce_func.args[1]
                iter_assign = ast.Assign(targets=[ast.Name(id='reduce_iter'+str(self.iter_index), ctx=ast.Store())],
                                         value=ast.Call(func=ast.Name(id='iter', ctx=ast.Load()),
                                                        args=[it], keywords=[]))
                initial_assign = ast.Assign(targets=[target],
                                            value=ast.Call(func=ast.Name(id='next', ctx=ast.Load()),
                                                           args=[ast.Name(id='reduce_iter'+str(self.iter_index), ctx=ast.Load())],
                                                           keywords=[]) if len(reduce_func.args) == 2 else reduce_func.args[2])
                loop = ast.For(target=ast.Name(id='iter_element'+str(self.iter_index), ctx=ast.Store()),
                               iter=ast.Name(id='reduce_iter'+str(self.iter_index), ctx=ast.Load()),
                               body=[ast.Assign(targets=[target],
                                                value=ast.Call(func=func,
                                                               args=[target, ast.Name(id='iter_element'+str(self.iter_index), ctx=ast.Load())],
                                                               keywords=[]))],
                               orelse=[])
                return [iter_assign, initial_assign, loop]
            case _:
                return node

class ReplaceCompAssign(ast.NodeTransformer):
    '''
    assignments where the value is a comprehension are turned into loops
    y = {x for x in xs} ->
    y = set()
    for x in xs:
        y.push(x)

    *assumes that there is only one thing being assigned to at a time*
    '''
    def visit_Assign(self, node):
        match node.value:
            case ast.ListComp() as assign_list:
                assignment = ast.Assign(targets=node.targets,
                                        value=ast.Set(elts=[], ctx=ast.Load()))
                loop = self.generate_body(assign_list, ast.Call(func=ast.Attribute(value=node.targets[0],
                                                                                   attr='append',
                                                                                   ctx=ast.Load()),
                                                                args=[assign_list.elt],
                                                                keywords=[]))
                return [assignment, loop]
            case ast.SetComp() as assign_set:
                assignment = ast.Assign(targets=node.targets,
                                        value=ast.List(elts=[], ctx=ast.Load()))
                loop = self.generate_body(assign_set, ast.Call(func=ast.Attribute(value=node.targets[0],
                                                                                  attr='push',
                                                                                  ctx=ast.Load()),
                                                               args=[assign_set.elt],
                                                               keywords=[]))
                return [assignment, loop]
            case _:
                return node

    def generate_body(self, comprehension, body):
        '''
        [line for file in files for line in file if f(line) if g(file)] ->
        for file in lines:
            for line in file:
                if f(line) and g(file):
                    y.push(line)
        '''
        curr = None
        for generator in comprehension.generators[::-1]:
            inner_body = body if not curr else curr
            curr = ast.For(target=generator.target,
                           iter=generator.iter,
                           body=inner_body if len(generator.ifs) == 0 else ast.If(test=ast.BoolOp(op=ast.And(),
                                                                                                  values=generator.ifs),
                                                                                  body=inner_body,
                                                                                  orelse=[]),
                           orelse=[])
        return curr


class ReplaceCollections(ast.NodeTransformer):
    '''
    calls to the constructor (e.g. list() or set()) will be replaced with list comprehensions/empty collection
    list(x for x in range(10)) -> [x for x in range(10)]

    list comprehensions/empty collections will be converted back into calls to the constructor
    '''
    def visit_Call(self, node):
        match node.func:
            case ast.Name(id='list'):
                self.generic_visit(node)
                # should only have one arg, the iterator
                if len(node.args) == 0:
                    return ast.List(elts=[], ctx=ast.Load())
                else:
                    # ignore conversions between different collections
                    it = node.args[0]
                    if not isinstance(it, ast.GeneratorExp):
                        return node
                    return ast.ListComp(elt=it.elt,
                                        generators=it.generators)
            case ast.Name(id='set'):
                self.generic_visit(node)
                if len(node.args) == 0:
                    return node # no empty set literal
                else:
                    if len(node.args) == 1:
                        it = node.args[0]
                        if not isinstance(it, ast.GeneratorExp):
                            return node
                        return ast.SetComp(elt=it.elt,
                                           generators=it.generators)
                    else:
                        return ast.Set(
                            elts=node.args()
                        )
            case ast.Name(id='dict'):
            # dictionary comprehensions can be complex since they need an iterator yielding keys and values
            # which can be given in many ways so if it's not empty just leave it be
                self.generic_visit(node)
                if len(node.args) == 0:
                    return ast.Dict(keys=[], values=[])
                else:
                    return node
            case _:
                return node

    def visit_ListComp(self, node):
        list_gen = ast.GeneratorExp(elt=node.elt,
                                    generators=node.generators)
        return ast.Call(func=ast.Name(id='list', ctx=ast.Load()),
                        args=[list_gen],
                        keywords=[])

    def visit_SetComp(self, node):
        set_gen = ast.GeneratorExp(elt=node.elt,
                                   generators=node.generators)
        return ast.Call(func=ast.Name(id='set', ctx=ast.Load()),
                        args=[set_gen],
                        keywords=[])

def obfuscate(inFile, outFile):
    with open(inFile, mode='r') as dataset, open(outFile, mode='w') as obf_dataset:
        for line in dataset:
            try:
                json_obj = json.loads(line)
                snippet_AST = ast.parse(json_obj['code'])
                snippet_AST = RemoveDocstring().visit(snippet_AST)
                processors = [ReplaceMapFilter(), ReplaceFor(), ReplaceReduce(), ReplaceCompAssign(), ReplaceCollections()]
                obfuscations = []
                for index, processor in enumerate(processors):
                    obf_AST = ast.fix_missing_locations(processor.visit(snippet_AST))
                    obfuscations.append(ast.unparse(obf_AST))
                json_obj['obfuscations'] = obfuscations
                print(json.dumps(json_obj), file=obf_dataset)
            except SyntaxError:
                continue
