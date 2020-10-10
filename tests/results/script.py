#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct  1 18:09:42 2020

@author: descentis
"""
import os
import statistics as st

article_dict = {}
article_list = []



for file in os.listdir('/home/descentis/knolml_dataset/output/article_list'):
    if file.endswith(".xml"):
        article_list.append(file[:-4])
        article_dict[file[:-4]] = 0
'''
count = 0

thousand_dict = {}
random_count = []
with open('thousand/report_rootn_thousand.csv', 'r') as myFile:
    for line in myFile:
        line = line.replace('"','')
        line = line.split('.knolml,')
        #try:
        val = float(line[1].split(',')[1])*10
        random_count.append(val)
        #except:
            #pass
        for f in article_list:
            if f in line[0]:
                try:
                #print(f)
                    x = line[0][:-len(line[0].replace(f,''))]
                    article_dict[x] = 0
                    thousand_dict[x] = 0
                    count += 1
                except:
                    #print(f)
                    pass        
#print(len(random_count))        
n_dict = {}
n_list = []
with open('n-1/report_n-1_random.csv', 'r') as myFile:
    for line in myFile:
        line = line.replace('"','')
        line = line.split('.knolml,')
        try:
            r = float(line[1].split(',')[1])*10
            n_list.append(r)
        except:
            pass
        for f in article_list:
            if f in line[0]:
                try:
                #print(f)
                    x = line[0][:-len(line[0].replace(f,''))]
                    article_dict[x] = 0
                    if thousand_dict.get(x) == None:
                        try:
                            val = float(line[1].split(',')[1])*10
                            random_count.append(val)
                        except:
                            pass
                        n_dict[x] = 0
                        count += 1
                except:
                    #print(f)
                    pass        
'''
#memory part

n_list = []
c_list = []
ratio = []
with open('n-1/report_n-1_random.csv', 'r') as myFile:
    for line in myFile:
        line = line.replace('"','')
        line = line.split('.knolml,')
        for f in article_list:
            if f in line[0]:
                #try:
                #print(f)
                x = line[0][:-len(line[0].replace(f,''))]
                article_dict[x] = 0  
                original = os.stat('/home/descentis/knolml_dataset/output/article_list/'+f+'.xml').st_size
                compressed_size = os.stat('/home/descentis/knolml_dataset/output/article_list/n-1/'+line[0]+'.knolml').st_size
                c_list.append(compressed_size)
                ratio.append(compressed_size/original)
                n_list.append(compressed_size)
                #except:
                    #print(f)
                    #pass        

'''
final_ratio = [x for _,x in sorted(zip(c_list,ratio), reverse=True)]
thousand_ratio = []
with open('thousand/report_rootn_thousand.csv', 'r') as myFile:
    for line in myFile:
        line = line.replace('"','')
        line = line.split('.knolml,')
        for f in article_list:
            if f in line[0]:
                #try:
                #print(f)
                x = line[0][:-len(line[0].replace(f,''))]
                article_dict[x] = 0  
                original = os.stat('/home/descentis/knolml_dataset/output/article_list/'+f+'.xml').st_size
                compressed_size = os.stat('/home/descentis/knolml_dataset/output/article_list/thousand/'+line[0]+'.knolml').st_size
                thousand_ratio.append(compressed_size/original)
                #thousand_list.append(compressed_size)

thousand_ratio += final_ratio[277:]


with open('thousand/report_rootn_thousand.csv', 'r') as myFile:
    for line in myFile:
        line = line.split(',')
        if len(line) > 2:
            #print(line)
            k = ','.join(line[:-1])
            k = k.replace('"','')
            #print(k)
        else:
            k = line[0]
        for f in article_list:
            if f in k[:-7]:
                try:
                #print(f)
                    x = k[:-7][:-len(k[:-7].replace(f,''))]
                    article_dict[x]['n-1'] = 0
                    count += 1
                except:
                    #print(f)
                    pass
'''

'''
avg_n = []
with open('n-1/report_n-1_full.csv', 'r') as myFile:
    for line in myFile:
        line = line.split(',')
        try:
            avg_n.append(float(line[-1][:-1]))
        except:
            pass

avg = st.mean(avg_n) 
std = st.stdev(avg_n)       
'''
'''
avg_n = []
with open('one/report_one_random.csv', 'r') as myFile:
    for line in myFile:
        line = line.split('knolml,')
        try:
            line = line[1].split(',')
            avg_n.append(float(line[1])*10)
        except:
            pass


avg = st.mean(avg_n) 
std = st.stdev(avg_n)
'''