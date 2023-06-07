master_file = "en-spa_codeswitched_sentences.conllu"
manifest = "checked_sentence_ids.txt"

with open(master_file) as f:
    sentences = [s for s in f.read().split("\n\n") if s.strip("\n")]

with open(manifest) as f:
    checked_ids = set([line.strip("\n") for line in f])

for sent in sentences:
    lines = sent.split("\n")
    id_ = lines[0].split(" = ")[-1]
    labels = lines[5]
    if id_ in checked_ids:
        if "checked" not in labels:
            lines[5] = labels.replace(" =", " = checked ")
    print("\n".join(lines))
    print("")