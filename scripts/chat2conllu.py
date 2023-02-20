import glob
import re
from string import punctuation

p = re.compile("Untagged words are (English|Spanish) except where part of an utterance headed \[\- (spa|eng)\], in which untagged words are (Spanish|English)")
timestamp_pattern = re.compile("[0-9]+_[0-9]+")
lang_block_pattern = re.compile("\[- (eng|spa)]")

pos_map = {'PRON': 'PRON', 'ADV': 'ADV', 'V': 'VERB', 'SV': 'VERB', 
           'REL+GB': "SCONJ", 'ADJ+PV': "ADJ", 'IM+PV': "INTJ", 
           'ADJ+ADV': "ADJ", 'ADV+PV': "ADV", 'PRON+BE': "PRON", 
           'IM': "INTJ", 'ADJ+V': "ADJ", 'AV': "VERB", 'CONJ': "CCONJ",
           'IM+V': "INTJ", 'N': "NOUN", 'ADV+V': "ADV", 'PRON+GB': "PRON", 
           'CONJ+BE': "CCONJ", 'PREP': "ADP", 'DET': "DET", 'ADJ': "ADJ", 
           'NUM': "NUM", "name":"PROPN"}

class ChatDoc(object):
    def __init__(self, path_to_file):
        self.file_name = path_to_file.split("/")[-1]
        with open(path_to_file) as f:
            self.data = f.read()
        self.default_lang_code = self.read_default_lang()
        self.num_utterances = 0
        self.failed_glosses = 0
        self.n_tokens = 0

    
    def read_default_lang(self):
        lang_match = re.search(p, self.data)
        if lang_match is not None:
            return lang_match.groups()[0][:3].lower()
        else:
            return ""
    
    def process_tokens(self, tokens):
        procd_tokens = []
        token_langs = []
        
        add_lang = None

        for token in tokens:
            if token == "[-eng]":
                add_lang = "eng"
                continue
            elif token == "[-spa]":
                add_lang = "spa"
                continue
            if token == "(.)":
                continue
            
            token = token.strip("><()")
            if not token:
                continue
            if token[0] in punctuation and token not in ".?!":
                continue
            elif token == "xxx":
                continue
            else:
                if "@s" in token:
                    token, lang = token.split("@s:")   
                else:
                    lang = (
                        add_lang if add_lang is not None 
                        else self.default_lang_code
                    )
                
                # if "_" in token:
                    # cmpnnts = token.split("_")
                    # if all(len(c) == 1 for c in cmpnnts) or len(cmpnnts[0]):
                    #     token = token.replace("_", "")
                    # elif len(cmpnnts[0]) == 1:
                    #     token = token.replace("_", "-")
                    # elif token.lower() == "t_vs":
                    #     token = token.replace("_", "")
                    # else:
                    #     multi_token = cmpnnts
                    #     langs = [lang] * len(cmpnnts)
                    #     procd_tokens.extend(multi_token)
                    #     token_langs.extend(langs)
                    #     continue                        
                    
                    

                procd_tokens.append(token)
                token_langs.append(lang)

        return procd_tokens, token_langs

    def process_single_utterance(self, line, autogloss):
        speaker, line = line.split("\t")
        speaker = speaker.strip("*:")
        autogloss = autogloss.split("\t")[1]
        d = {"orig": line}
        
        line = re.sub(lang_block_pattern, r"[-\1]", line)
        line = line.replace("[=! ", "[=!")
        tokens, token_langs = self.process_tokens(line.split())
        self.n_tokens += len(tokens)

        autogloss = autogloss.replace("+V 3S PRES", "+V.3S.PRES")
        autogloss_tokens = autogloss.split()
        
        pause_timestamps = tokens[-1].replace("\x15", "")
        if re.match(timestamp_pattern, pause_timestamps):
            tokens = tokens[:-1]
            token_langs = token_langs[:-1]
            d["wait_time_interval"] = [float(n) for n in pause_timestamps.split("_")]

        self.num_utterances += 1
        if len(autogloss_tokens) != len([t for t in tokens if t not in ".?!"]):
            d["sent_id"] = "{}:{}".format(self.file_name, self.num_utterances)
            d["text"] = " ".join(tokens)
            d["speaker"] = speaker
            d["tokenized"] = tokens
            d["token_langs"] = token_langs
            d["gloss[orig]"] = " ".join(autogloss_tokens)
            d["glosses"] = []  
            self.failed_glosses += 1
        else:
            d["sent_id"] = "{}:{}".format(self.file_name, self.num_utterances)
            d["text"] = " ".join(tokens)
            d["speaker"] = speaker
            d["tokenized"] = tokens
            d["token_langs"] = token_langs
            d["gloss[orig]"] = " ".join(autogloss_tokens)
            d["glosses"] = autogloss_tokens        
        
        return d

    def join_mwt(self, t):
        sides = t.split("_")
        if all(len(s) == 1 for s in sides) or t.lower() == "t_vs":
            return t.replace("_", "")
        elif len(sides[0]) == 1:
            return t.replace("_", "-")
        
    def print_conllu_sent(self, d):
        out_str = ""
        out_str += (f"# sent_id = {d['sent_id']}\n")

        procd_tokens = []
        for tok in d['tokenized']:
            joined = self.join_mwt(tok)
            if joined is not None:
                procd_tokens.append(joined)
            else:
                if "_" in tok:
                    tok = tok.replace("_", " ")
                procd_tokens.append(tok)
        text = ' '.join(procd_tokens)
        out_str += (f"# text = {text}\n")

        out_str += (f"# text[orig] = {d['orig']}\n")
        out_str += (f"# gloss[orig] = {' '.join(d['glosses'])}\n")
        out_str += (f"# speaker = {d['speaker']}\n")
        out_str += ("# labels =\n")
        j = 0
        i = 0
        while j < len(d["tokenized"]):
            gloss = d["glosses"][i] if i < len(d["glosses"]) else None
            token = d["tokenized"][j]
            if token in ".!?":
                out_str += (f"{j + 1}\t{token}\t_\tPUNCT\t_\t_\t_\t_\t_\t_\n")
                j += 1
            else:
                if gloss is None:
                    if "_" in token:
                        joined_mwt = self.join_mwt(token)
                        if joined_mwt is not None:
                            lang = d["token_langs"][j]
                            out_str += (f"{j + 1}\t{joined_mwt}\t_\t_\t_\t_\t_\t_\t_\tLang={lang}\n")
                            j += 1
                            continue
                        else:
                            mwts = token.split("_")
                            lang = d["token_langs"][j]
                            start_token_idx = j + 1
                            end_token_idx = j + len(mwts)
                            if start_token_idx == end_token_idx:
                                import pdb;pdb.set_trace()
                            out_str += (f"{start_token_idx}-{end_token_idx}\t{mwts[0]}\t_\t_\t_\t_\t_\t_\t_\tLang={lang}\n")
                            tidx = 0
                            for t in mwts:
                                tidx += 1
                                out_str += (f"{j + tidx}\t{t}\t_\t_\t_\t_\t_\t_\t_\tLang={lang}\n")
                            j += tidx 
                            continue                                                        
                    lang = d["token_langs"][j]
                    out_str += (f"{j + 1}\t{token}\t_\t_\t_\t_\t_\t_\t_\tLang={lang}\n")
                    j += 1
                else:
                    if "_" in token:
                        joined_mwt = self.join_mwt(token)
                        if joined_mwt is not None:
                            pos_o = gloss.split(".")[1] if "." in gloss else ""
                            upos = pos_map.get(pos_o, "_")
                            lang = d["token_langs"][j]
                            out_str += (f"{j + 1}\t{joined_mwt}\t_\t{upos}\t_\t_\t_\t_\t_\tLang={lang}\n")
                            i += 1
                            j += 1
                            continue
                        else:
                            mwts = token.split("_")
                            pos_o = gloss.split(".")[1] if "." in gloss else "PROPN" if gloss == "name" else ""
                            upos = pos_map.get(pos_o, "_")
                            lang = d["token_langs"][j]
                            out_str += (f"{j + 1}\t{mwts[0]}\t_\t_\t_\t_\t_\t_\t_\tLang={lang}\n")
                            tidx = 1
                            for t in mwts[1:]:
                                tidx += 1
                                out_str += (f"{j + tidx}\t{t}\t_\t_\t_\t_\t_\t_\t_\tLang={lang}\n")
                            i += 1
                            j += tidx 
                            continue 
        
                    pos_o = gloss.split(".")[1] if "." in gloss else ""
                    upos = pos_map.get(pos_o, "_")
                    lang = d["token_langs"][j]
                    out_str += (f"{j + 1}\t{token}\t_\t{upos}\t_\t_\t_\t_\t_\tLang={lang}\n")
                    i += 1
                    j += 1
        return out_str

    def print_conllu(self, out_file=None):
        utterances = self.process_utterances()
        utt_for_print = [self.print_conllu_sent(d) for d in utterances]
        if out_file is not None:
            with open(out_file, "w") as fout:
                print("\n".join(utt_for_print), file=fout)
        else:
            print("\n".join(utt_for_print))

    def process_utterances(self):
        utterances = []
        lines = self.data.split("\n")
        for i in range(len(lines)):
            line = lines[i]
            next_line = lines[i+1] if (len(lines) - 1) > i else None
            if line.startswith("@"):
                continue
            if line.startswith("*"):
                if next_line is not None:
                    if next_line.startswith("%aut"):
                        utterance_dict = self.process_single_utterance(line, next_line)
                        utterances.append(utterance_dict)
            else:
                continue
        return utterances

if __name__ == "__main__":
    filenames = glob.glob("../data/original/*")
    all_pos = set([])
    total_tokens = 0
    for fname in filenames:
        print(fname)
        processor = ChatDoc(fname)
        outfile = "../data/conllu/{}.conllu".format(processor.file_name)

        processor.print_conllu(
            out_file=outfile
        )
        total_tokens += processor.n_tokens

    print("Tokens: {}".format(total_tokens))