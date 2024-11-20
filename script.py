# this is the sample run
import os
import math
import t as wc
import csv 

def get_new_k(revision_len):
    n = len(revision_len)
    m = (sum(revision_len)*0.001)/n
    diff=0
    for i in range(n-1):
        diff=diff+ abs(revision_len[i]-revision_len[i+1])
    d = (diff*0.01)/n

    t1 = n*(m-d)
    t2 = m*d

    new_k = int(math.sqrt(t1/t2))
    return new_k


def compress_func(files,w):
    stats={}
    for file in files:
        d_temp={}
        revision_len = w.read_xml(file)
        n = len(revision_len)
        root_n = int(math.sqrt(n))
        new_k = get_new_k(revision_len)
        k_list = {'one':1,'rootn':root_n,'newk':new_k,'thousand':1000,'n-1':n-1}
        k_list = [(k, v) for k, v in k_list.items()] 
        d_temp["file_size"]=files[file]
        d_temp["n"]=n
        
        for verbal,k in k_list:
            w.wikiConvert(file_name=file,output_dir = file+'_'+str(k),k=k)
            temp = file+'_'+str(k)+'/'+file[:-4]+'.knolml'
            compressed_size = os.stat(temp).st_size/1000000
            d_temp[verbal+'_'+str(k)] = compressed_size
        
        
        stats[file] = d_temp

    return stats
def create_csv(stats):
    fields = ["filename","file_size","total revisions","one","root_n","new_k","1000","n-1"]
    rows=[]
    for file_name in stats:
        temp=[]
        temp.append(file_name)
        info = stats[file_name]
        for key in info:
            temp.append(info[key])
        rows.append(temp)
    with open('report.csv',"w") as f:
        csvwriter = csv.writer(f)
        csvwriter.writerow(fields)
        csvwriter.writerows(rows)
    
def run():

    dir_files = os.listdir()
    files = {}
    #getting files and size

    for file in dir_files:
        if file[-4:]=='.xml':
            #print(os.stat(file).st_size/1000000)
            files[file]=os.stat(file).st_size/1000000
    print(files)
    w = wc.wikiRetrieval()
    stats = compress_func(files,w)
    create_csv(stats)

run()

    



    
