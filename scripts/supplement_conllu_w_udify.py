import glob

def integrate_udify_output(conllu_sent, udify_sent):
    combined = []
    token_idx = 0
    for conllu_line in conllu_sent:
        if conllu_line.startswith("#"):
            combined.append(conllu_line)
        else:
            udify_line = udify_sent[token_idx].split("\t")
            conllu_line = conllu_line.split("\t")

            if conllu_line[0] != udify_line[0]:
                raise Exception("token indices don't match! {} vs {}".format(conllu_line[0], udify_line[0]))
            elif conllu_line[1] != udify_line[1]:
                raise Exception("token forms don't match! {} vs {}".format(conllu_line[1], udify_line[1]))

            conllu_line[2:9] = udify_line[2:9]
            combined.append("\t".join(conllu_line))
            token_idx += 1
            
    return combined


results = {}
all_conllu_files = glob.glob("../data/conllu/*conllu")
for conllu_path in all_conllu_files:
    n = conllu_path.split("/")[-1]
    udify_path = conllu_path.replace("/conllu/", "/udify_outputs/")
    
    with open(udify_path) as f:
        udify_sents = f.read().split("\n\n")
        
    with open(conllu_path) as f:
        conllu_sents = f.read().split("\n\n")

    all_combined = []
    for conllu_sent, udify_sent in zip(conllu_sents, udify_sents):
        if not conllu_sent or not udify_sent:
            continue
        combined = integrate_udify_output(conllu_sent.split("\n"), udify_sent.split("\n"))
        all_combined.append("\n".join(combined))  
    results[n] = all_combined
    print(n)

for fname, result in results.items():
    with open(f"../data/combined/{fname}", "w") as f:
        f.write("\n\n".join(result))
    print(fname)