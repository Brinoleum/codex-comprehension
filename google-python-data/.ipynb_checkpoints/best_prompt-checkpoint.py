import sys
import csv
import json
import requests
import itertools
import openai
import re
import random
import time
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction

chencherry = SmoothingFunction()

openai.api_key = "sk-RswSdIxcen3t7lywIj9xchpZ7uJL3x6tTmlaBCTg"

def query(text):
    response = openai.Completion.create(
        engine='davinci-codex',
        prompt=text,
        max_tokens=100,
    )
    return response['choices'][0]['text']

def make_prompt(snippetA, snippetB):
    textA = re.sub("(W|w)rite ", "", snippetA['prompt'])
    textB = re.sub("(W|w)rite ", "", snippetB['prompt'])
    prompt = f"{snippetA['code']}\nThe above code is {textA}\n\n{snippetB['code']}\nThe above code is {textB}\n"
    return prompt


with open('sanitized-mbpp.json', 'r') as dataset:
    snippets = json.loads(dataset.read())
    count = len(snippets)
   
# currently there are 427 snippets and we choose 2, yielding 90,951 prompts
# to reduce number of queries, we also randomly select to get to approximately 5000 prompts
for i in range(10):
    pairs = itertools.combinations(range(count), 2)
    best_prompts = []
    with open(f"best_prompts_length{i}.json", 'w') as outfile:
        sample_index = random.randrange(count)
        try:
            sample_pairs = filter(lambda x: x[0] != sample_index and x[1] != sample_index, pairs) 
            for a, b in random.sample(list(sample_pairs), 500):
                prompt = make_prompt(snippets[a], snippets[b]) + snippets[sample_index]['code'] + "\nThe above code"
                time.sleep(6)
                completion = query(prompt)
                bleu_score = sentence_bleu([snippets[sample_index]['prompt'].split()], completion.split(), smoothing_function=chencherry.method7)
                best_prompts.append((bleu_score, prompt, completion))
        except:
            print("timed out :(")
            print(f'got {len(best_prompts)} many prompts')
            print('waiting...')
            time.sleep(300)
        finally:
            best_prompts.sort(key=lambda x: len(x[1]))
            print(json.dumps({"prompt": snippets[sample_index],
                              "queries": best_prompts}),
                  file=outfile)

