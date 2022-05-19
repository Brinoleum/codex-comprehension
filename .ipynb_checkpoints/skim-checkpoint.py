#!/usr/bin/env python

# haha lmao this file is skimpy
# but for realsies it prints each oeis sequence description and prompts whether to keep it or not
# dear lord there's 6777 entries to get through why did i do this to myself

import csv

with open('oeis_data_obfuscated.tsv', mode='r', newline='') as sequences, open('oeis_data_obf_readable.tsv', mode='w', newline='') as indexed:
    reader = csv.reader(sequences, delimiter='\t')
    writer = csv.writer(indexed, delimiter='\t')
    writer.writerow(['readable'] + next(reader))
    count = 0
    for row in reader:
        if count == 100:
            break
        readable = input(row[1])
        if readable:
            writer.writerow(row)
            count += 1
