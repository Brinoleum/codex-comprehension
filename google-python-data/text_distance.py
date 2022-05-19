from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

def jaccard(a, b):
    a = set(a.split())
    b = set(b.split())
    return len(a.intersection(b)) / len(a.union(b))

def cosine(a, b):
    data = [a, b]
    Tfidf_vect = TfidfVectorizer()
    vector_matrix = Tfidf_vect.fit_transform(data)

    tokens = Tfidf_vect.get_feature_names()
    cosine_similarity_matrix = cosine_similarity(vector_matrix)
    return cosine_similarity_matrix[0, 1]


import json

for i in range(10):
    with open(f'best_prompts_length{i}.json', 'r') as infile, open(f'best_prompts_similarity{i}.json', 'w') as outfile:
        data = json.loads(infile.read())
        prompt = data['prompt']['prompt']
        queries = data['queries']
        data['queries'] = list(map(lambda x: x[:1] + [jaccard(prompt, x[2]), cosine(prompt, x[2])] + x[1:], queries))
        print(json.dumps(data), file=outfile)