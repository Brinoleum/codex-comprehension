import json
import csv


with open('oeis_data.tsv', newline='') as data, open('oeis_data.jsonl', 'w') as json_data:
    reader = csv.reader(data, delimiter='\t')
    for line in reader:
        json_obj = {}
        json_obj['sequence_id'] = line[0]
        json_obj['text'] = line[1]
        json_obj['sequence'] = line[2]
        json_obj['code'] = line[3]
        print(json.dumps(json_obj), file=json_data)

