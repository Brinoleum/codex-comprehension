#!/usr/bin/env python
# this script scrapes OEIS to retrieve numerical sequences and the associated code that generates those sequences

import requests
import re
from itertools import groupby
import json
import sys

index = 0
def key_func(snippet):
    ''' used for grouping, increments every time a new language is encountered '''
    global index
    if re.match(r'^\([a-zA-Z]*\)', snippet):
        index += 1
    return index

def process_snippet(snippet_list):
    ''' strips # comments, replaces tabs with spaces and appends everything into one string '''
    processed = ''
    for snippet in snippet_list:
        no_comment = re.sub(r'#.*$', '', snippet)
        no_tab = re.sub('\t', '    ', no_comment)
        processed += no_tab + '\n'
    return processed


# currently the website lists 348119 sequences in the database
def scrape(filename):
    with open(filename, 'w') as dataset:
        for i in range(1, 348120):
            result = requests.get(f"https://oeis.org/search?fmt=json&q=id:A{i}").json()["results"][0]
            if "program" not in result:
                continue
            name = result["name"]
            data = result["data"]
            snippets = result["program"]
            for k, g in groupby(snippets, key_func):
                g = process_snippet(list(g))
                if g[:8] == '(Python)':
                    json_obj = {"sequence_id": 'A{:0>6}'.format(i), "text": name, "sequence": data, "code": g[8:]}
                    print(json.dumps(json_obj), file=dataset)