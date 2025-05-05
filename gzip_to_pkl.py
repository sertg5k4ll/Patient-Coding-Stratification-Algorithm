import os
import gzip
import argparse
import json
import pickle as pkl
import itertools
from tqdm import tqdm
from random import randint,shuffle


def data_generator(data):
    with gzip.open(args.input,"rb") as f:
        jb = f.read()
    js = jb.decode("utf-8")
    data_j = json.loads(js)
    data = data_j["data"]
    for x in tqdm(data,desc="data",total=len(data)):
        yield x

def get_split_id():
    with gzip.open(args.input,"rb") as f:
        jb = f.read()
    js = jb.decode("utf-8")
    data_j = json.loads(js)
    split = data_j["splits"]
    return split

def get_rows():
    with gzip.open(args.input,"rb") as f:
        jb = f.read()
    js = jb.decode("utf-8")
    data_j = json.loads(js)
    rows = data_j["rows"]
    return rows

def sentence_segment(docs):
    docs = list(docs)
    for doc in docs:
        yield [[[t for t in sent.split()] for sent in d['Sentences']] for d in doc]

def sentence_segment_2(docs):
    """
    with reports type
    """
    docs = list(docs)
    for doc in docs:
        yield [[[[t for t in sent.split()] for sent in d['Sentences']],d["Reports_Type"]] for d in doc]

def build_dataset2(args):
    print("Building dataset from : {}".format(args.input))

    gen_a,gen_b = itertools.tee(data_generator(args.input),2)

    if args.model_type == "han":
        data = [(z[0], tok, z[2], z[3], z[4], z[5],z[6],z[7],z[8],z[9],
                 z[10],z[11],z[12],z[13],z[14],z[15],z[16],z[17],z[18],
                 z[19],z[20],z[21],z[22],z[23],z[24],z[25],z[26],z[27],z[28],z[29],z[30],z[31]) for z, tok in zip(tqdm((z for z in gen_a),desc="reading file"), 
                                                             sentence_segment(x[1] for x in gen_b))]
    elif args.model_type == "mhhtan":
        data = [(z[0], tok_rt, z[2], z[3], z[4], z[5],z[6],z[7],z[8],z[9],
                 z[10],z[11],z[12],z[13],z[14],z[15],z[16],z[17],z[18],
                 z[19],z[20],z[21],z[22],z[23],z[24],z[25],z[26],z[27],z[28],z[29],z[30],z[31]) 
                 for z, tok_rt in zip(tqdm((z for z in gen_a),desc="reading file"),sentence_segment_2(x[1] for x in gen_b))]
    else:
        raise Exception("Not found cancer type: {}".format(args.cancer_type))
    
    print(f"total patients count: {len(data)}")

    splits = get_split_id()
    
    rows = get_rows()

    return {"data":data,"splits":splits,"rows":rows}


def main(args):

    ds = build_dataset2(args)
    os.makedirs("./pkl_data",exist_ok=True)
    pkl.dump(ds,open(args.output,"wb"))
    print(f"pickle file: {args.output} created")

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str)
    parser.add_argument("--output", type=str, default="./pkl_data/sentences.pkl")

    # mhhtan: Each report is assigned to a corresponding report type.
    # han: Only the report itself is required, without categorization.
    parser.add_argument("--model-type", type=str, default="mhhtan") 

    args = parser.parse_args()


    main(args)