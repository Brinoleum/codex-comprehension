import sys
import csv
import json
import requests
import itertools
import openai
from nltk.translate.bleu_score import sentence_bleu

openai.api_key = "sk-RswSdIxcen3t7lywIj9xchpZ7uJL3x6tTmlaBCTg"

prompt = """
fib(n: int) -> int:

The above code declares a function that generates the n-th Fibonacci number.

def fib1(n: int) -> int:
    a, b = 0, 1
    for i in range(n):
        a, b = b, a+b
    return b

The above function generates the n-th Fibonacci number through an iterative method, described below:

Set initial seed values a and b to 0 and 1 respectively. Then, in a loop for n many iterations, set a to b, and set b to the sum of a and b. Finally, after the loop, return b.

def fib2(n: int) -> int:
    if n == 0 or n == 1:
        return n
    else:
        return fib(n-1) + fib(n-2)

The above function generates the n-th Fibonacci number through a recursive method, described below:

If n is 0 or n is 1, then return n. Otherwise, return the sum of the n-1'st and n-2'nd Fibonacci numbers.
"""

def query(text, presence=0, frequency=0):
    response = openai.Completion.create(
        engine='davinci-codex',
        prompt=text,
        max_tokens=100,
        # look into penalties for presence and frequency
        presence_penalty=presence,
        frequency_penalty=frequency
    )
    return response['choices'][0]['text']

def write_completions(outFile, sequences):
    for sequence in sequences:
        # generate gpt completions
        prompts = list(map(lambda x: f'{prompt}\n{x}\nThe above code generates', sequence['obfuscations']))
        completions = {}
        completions['none'] = list(map(query, prompts))
        completions['p'] = list(map(lambda x: query(x, presence=1), prompts))
        completions['f'] = list(map(lambda x: query(x, frequency=1), prompts))
        completions['pf'] = list(map(lambda x: query(x, presence=1, frequency=1), prompts))
        sequence['completions'] = completions
        
        # generate bleu scores for each setting, compared to sequence text
        bleu_scores = {}
        bleu_scores['none'] = sentence_bleu(list(map(lambda x: x.split(), completions['none'])), sequence['text'])
        bleu_scores['p'] = sentence_bleu(list(map(lambda x: x.split(), completions['p'])), sequence['text'])
        bleu_scores['f'] = sentence_bleu(list(map(lambda x: x.split(), completions['f'])), sequence['text'])
        bleu_scores['pf'] = sentence_bleu(list(map(lambda x: x.split(), completions['pf'])), sequence['text'])
        sequence['bleu_scores'] = bleu_scores
        
        print(json.dumps(sequence), file=outFile)

def read_snippets(inFile, indices=None):
    with open(inFile, mode='r', newline='') as sequences:
        for line in sequences:
            json_obj = json.loads(line)
            if not indices:
                yield json_obj
            elif indices and 'sequence_id' in json_obj and json_obj['sequence_id'] in indices:
                yield json_obj
            else: continue
