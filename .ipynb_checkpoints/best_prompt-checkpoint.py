import openai
import json
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
import time
openai.api_key = "sk-RswSdIxcen3t7lywIj9xchpZ7uJL3x6tTmlaBCTg"
def getJsonData(filename):
    with open(filename) as data:
        return json.loads(data.read())

def query(text):
    response = openai.Completion.create(
            engine='davinci-codex',
            prompt=text,
            max_tokens=100)
    return response['choices'][0]['text']


if __name__ == '__main__':
    bleuObjs = []
    smoothing = SmoothingFunction()

    for i, obj in enumerate(getJsonData('google-python-data/mbpp.json')):
        time.sleep(10)
        text = obj['text']
        code = obj['code']
        prompt = f"""Listed below is a snippet of code and a description of what it does.

{text}

The code above is"""
        print("generating completion")
        completion = query(prompt)
        print("generating bleu score")
        score = sentence_bleu([text.split()], completion.split(), smoothing_function=smoothing.method4)
        bleuObjs.append((score, obj))

    with open('best_prompts.txt', 'w') as outFile:
        bleuObjs.sort(key=lambda x: x[0], reverse=True)
        outJson = json.dumps(bleuObjs)
        print(outJson, file=outFile)
