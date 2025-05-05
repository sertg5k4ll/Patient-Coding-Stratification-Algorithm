import os
import gzip
import json
import codecs
import argparse
import jsonlines
import pandas as pd
from collections import Counter


def process_patient_score(cancers,cancer_registry,labels_count,patient_score,raw_data_path,raw_path,file_encoding):
    for cancer in cancers:
        # each cancer registry task
        print(raw_data_path+f"/{raw_path[cancer]}")
        with codecs.open(raw_data_path+f"/{raw_path[cancer]}",'r',encoding=file_encoding) as file:
            reader = jsonlines.Reader(file)
            for i in reader:
                for j in cancer_registry:
                    if j not in labels_count[cancer]:
                        labels_count[cancer][j] = Counter()
                        labels_count[cancer][j].update([i[j]])
                    else:
                        labels_count[cancer][j].update([i[j]])

            # reset readhead
            file.seek(0)

            # each patient data 
            for i in reader:
                if i["ID"] not in patient_score[cancer]:
                        patient_score[cancer][i["ID"]] = {}

                # each cancer registry task
                for j in cancer_registry:
                    patient_score[cancer][i["ID"]][j] = labels_count[cancer][j][i[j]]/sum(labels_count[cancer][j].values())

    return labels_count, patient_score

def process_label_distribute(labels_count,label2csv_p):
    labels_distribute = {}
    for cancer_name, labels in labels_count.items():
        labels_distribute[cancer_name] = {}
        for label, counter in labels.items():
            labels_distribute[cancer_name][label] = len(counter)
    ld = pd.DataFrame(labels_distribute)
    ld.to_csv(label2csv_p,encoding="utf-8")
    
    return labels_distribute

def process_patient_id_output(patient_dataset_id_,id2csv_p):
    c, t, i = [], [], []

    for k,v in patient_dataset_id_.items():
        for k1,v1 in v.items():
            c.extend([k]*len(v1))
            t.extend([k1]*len(v1))
            i.extend(v1)  
    id_pd = pd.DataFrame({
        "cancer":c,
        "type":t,
        "id":i
    })

    id_pd.to_csv(id2csv_p,index=False,encoding="utf-8")

    return id_pd

def get_patient_sum(cancers,patient_score):
    patient_sum = {i:{} for i in cancers}
    for k, v in patient_score.items():
        for k2, v2 in v.items():
            patient_sum[k][k2] = sum(v2.values())
    return patient_sum

def get_patient_list(cancers,patient_sum):
    patient_list = {i:[] for i in cancers}
    for k, v in patient_sum.items():
        patient_list[k] = sorted(patient_sum[k].items(),key=lambda x:x[1])
    return patient_list

def get_patient_dataset_id(cancers,patient_list,spilt_func,n,trainz=0.8,validz=0.1):
    patient_dataset_id = {i:{"training":[],"test":[],"dev":[]} for i in cancers}
    for k, v in patient_list.items():
        patient_dataset_id[k]["training"],patient_dataset_id[k]["test"],patient_dataset_id[k]["dev"] = spilt_func(v,n,tz=trainz,vz=validz)
    return patient_dataset_id

def split_data2(d,n,tz,vz):
    """
    To split a list into n equal parts and sample them in proportion.
    """
    try:
        n_s = round(len(d) / n)
        if n_s == 0:
            raise ValueError("ValueError: given argument n is too big.")
        i_l = [i*n_s for i in range(n)]
        
        tr,t,v = [],[],[]
        for i,j in enumerate(i_l):
            chunk_l = d[j:i_l[i+1]] if i != len(i_l)-1 else d[j:]
            l = len(chunk_l)
            train_size = int(l * tz)
            valid_size = int(round(l*vz) if l>10 else 1)
        
            train, valid, test = [i [0] for i in chunk_l[:train_size]],[i [0] for i in chunk_l[train_size:train_size+valid_size]],[i[0] for i in chunk_l[train_size+valid_size:]]
            tr.extend(train)
            t.extend(test)
            v.extend(valid)
        return tr,t,v
    except Exception as e:
        print(e)

def format_data(data):
    # han
    return (data["ID"],[{"Sentences":c["Sentences"]}for c in data["Reports"]],data["HISTOLOGY"],data["BEHAVIOR"],
                data["GRADE_P"],data["DIAG_CONFIRM"],data["MCONF_DT"],data["PI"],data["LVI"],data["NODE_EXAMINED"],
                data["NODE_POSITIVE"],data["SDIAG_DT"],data["SDIAG"],data["PATH_T"],data["PATH_N"],data["PATH_M"],data["PATH_STAGE_GROUP"],
                data["PDESCR"],data["AJCC"],data["FIRST_OP_DATE"],data["OPDEF_DT"],data["OPTYPE"],data["MISURGERY"],
                data["OPMARGS"],data["SMARGING_D"],data["OPLNSCOPE"],data["CHEMO"],data["IMMUNO"],data["TARGET"],
                data["HORMONE"],data["CASITE"],data["LATERALITY"])  

def format_data_v2(data):
    # mhhtan
    return (data["ID"],[{"Sentences":c["Sentences"],"Reports_Type":c["Reports_Type"]}for c in data["Reports"]],data["HISTOLOGY"],data["BEHAVIOR"],
                data["GRADE_P"],data["DIAG_CONFIRM"],data["MCONF_DT"],data["PI"],data["LVI"],data["NODE_EXAMINED"],
                data["NODE_POSITIVE"],data["SDIAG_DT"],data["SDIAG"],data["PATH_T"],data["PATH_N"],data["PATH_M"],data["PATH_STAGE_GROUP"],
                data["PDESCR"],data["AJCC"],data["FIRST_OP_DATE"],data["OPDEF_DT"],data["OPTYPE"],data["MISURGERY"],
                data["OPMARGS"],data["SMARGING_D"],data["OPLNSCOPE"],data["CHEMO"],data["IMMUNO"],data["TARGET"],
                data["HORMONE"],data["CASITE"],data["LATERALITY"])

def output_json(cancers,hospital,patients_id,raw_data_path,raw_path,json_path,file_encoding,data_rows,format_func,s_number,model_type):
    for cancer in cancers:
        patient_id_train = patients_id[(patients_id.cancer == cancer) & (patients_id.type == "training")].id.values
        patient_id_test = patients_id[(patients_id.cancer == cancer) & (patients_id.type == "test")].id.values
        patient_id_valid = patients_id[(patients_id.cancer == cancer) & (patients_id.type == "dev")].id.values
        with codecs.open(raw_data_path+f"/{raw_path[cancer]}",'r',encoding=file_encoding) as file:
            reader = jsonlines.Reader(file)
            input_ = {"data":[],"splits":[],"rows":data_rows}
            file.seek(0)
            for i in reader:
                id_ = i["ID"]
                if i["ID"] in patient_id_train:
                    input_["data"].append(format_func(i))
                    input_["splits"].append(0)
                elif i["ID"] in patient_id_test:
                    input_["data"].append(format_func(i))
                    input_["splits"].append(1)
                elif i["ID"] in patient_id_valid:
                    input_["data"].append(format_func(i))
                    input_["splits"].append(2)
                else:
                    print(f"no such id in dataset_id: {id_}")
            with open(json_path+f"/{hospital}_{cancer.lower()}_split_{s_number}_{model_type}.json","w",encoding="utf-8") as json_file:
                json.dump(input_,json_file)
        print(f"json file: {json_path+f'/{hospital}_{cancer.lower()}_split_{s_number}_{model_type}.json'} created!")

def output_gzip(cancers,hospital,json_path,gzip_path,s_number,model_type):
    # output gzip file
    for o in cancers:
        js_file = json_path+f"/{hospital}_{o.lower()}_split_{s_number}_{model_type}.json"
        gp_file = gzip_path+f"/{hospital}_{o.lower()}_split_{s_number}_{model_type}.json.gz"
        with open(js_file,'r') as f:
            data = json.load(f)
            json_str = json.dumps(data)
            json_bytes = json_str.encode('utf-8')
            with gzip.open(gp_file,'w') as f:
                f.write(json_bytes)

        print(f"gzip file: {gp_file} created!")
            


def main(args):

    raw_data_path = args.raw_data_folder
    json_path = args.output_json_path
    gzip_path = args.output_gzip_path
    id2csv_p = args.id_proportion_path.replace("./",f"./{args.hospital}_")
    label2csv_p = args.label_distribute_path.replace("./",f"./{args.hospital}_")
    os.makedirs(json_path,exist_ok=True)
    os.makedirs(gzip_path,exist_ok=True)

    hospital = args.hospital
    cancers = args.cancers.split(",")
    raw_path = {i:f"{hospital.upper()}_{i}.json" for i in cancers}
    file_encoding = args.file_encoding
    all_labels = [i.strip() for i in args.labels.split(",")]

    labels_count = {i:{} for i in cancers}
    patient_score = {i:{} for i in cancers}
    data_rows = [i.lower() for i in args.data_rows.split(",")]
    

    labels_count, patient_score = process_patient_score(cancers,all_labels,labels_count,patient_score,raw_data_path,raw_path,file_encoding)
    labels_distribute = process_label_distribute(labels_count,label2csv_p)
    patient_sum = get_patient_sum(cancers,patient_score)  # all patient's score of sum
    patient_list = get_patient_list(cancers,patient_sum)  # sort the score  
    patient_dataset_id_ = get_patient_dataset_id(cancers,patient_list,spilt_func=split_data2,
                                                 n=args.stratification_number,trainz=args.trainset_ratio,
                                                 validz=args.validset_ratio)  # stratification

    patients_id = process_patient_id_output(patient_dataset_id_,id2csv_p)

    format_data_func = format_data_v2 if args.model_type == "mhhtan" else format_data

    output_json(cancers,hospital,patients_id,raw_data_path,raw_path,json_path,file_encoding,data_rows,
                format_data_func,args.stratification_number,args.model_type)
    output_gzip(cancers,hospital,json_path,gzip_path,args.stratification_number,args.model_type)
    


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Patient Coding Stratification')

    parser.add_argument("--model-type",type=str,default="mhhtan",help="han or mhhtan")
    parser.add_argument("--raw-data-folder",type=str,required=True,help="raw data folder path")
    parser.add_argument("--cancers",type=str,default="breast,colorectal,liver,oral,prostate,uterus")
    parser.add_argument("--hospital",type=str,default="kmuh")
    parser.add_argument("--file-encoding",type=str,default="utf-8")

    parser.add_argument("--labels", type=str,default="HISTOLOGY,BEHAVIOR,GRADE_P,DIAG_CONFIRM,PI,LVI," \
    "SDIAG,PATH_T,PATH_N,PATH_M,PATH_STAGE_GROUP,PDESCR,AJCC,OPTYPE,MISURGERY,OPMARGS,OPLNSCOPE,CHEMO," \
    "IMMUNO,TARGET,HORMONE,CASITE,LATERALITY")
    parser.add_argument("--data-rows", type=str, default="id,reports,HISTOLOGY,BEHAVIOR,GRADE_P,DIAG_CONFIRM," \
    "PI,LVI,SDIAG,PATH_T,PATH_N,PATH_M,PATH_STAGE_GROUP,PDESCR,AJCC,OPTYPE,MISURGERY,OPMARGS,OPLNSCOPE,CHEMO,IMMUNO," \
    "TARGET,HORMONE,CASITE,LATERALITY")

    parser.add_argument("--stratification-number",type=int,default=4)
    parser.add_argument("--trainset-ratio",type=float,default=0.8)
    parser.add_argument("--validset-ratio",type=float,default=0.1)
    parser.add_argument("--id-proportion-path", type=str,default="./id_proportion.csv")
    parser.add_argument("--label-distribute-path",type=str,default="./labels_distribute.csv")

    parser.add_argument("--output-json-path",type=str,default="./json_data")
    parser.add_argument("--output-gzip-path",type=str,default="./gzip_data")

    args = parser.parse_args()
    main(args)