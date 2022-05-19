import json
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction

chencherry = SmoothingFunction()

with open("best_prompts0.json", 'r') as infile, open('recalcuated.json', 'w') as outfile:
    data = json.loads(infile.read())
    prompt = data['prompt']['prompt']
    for query in data['queries']:
        query[0] = sentence_bleu([prompt.split()], query[2], smoothing_function = chencherry.method7)
    print(json.dumps(data), file=outfile)
