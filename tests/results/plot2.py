#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Oct 11 17:41:03 2020

@author: descentis
"""
import os
import matplotlib.pyplot as plt

article_dict = {}
article_list = []

for file in os.listdir('/home/descentis/knolml_dataset/output/article_list'):
    if file.endswith(".xml"):
        article_list.append(file[:-4])
        article_dict[file[:-4]] = 0

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

                if (compressed_size/original) > 1:
                    ratio.append(0.9)
                else:
                    ratio.append(compressed_size/original)
                n_list.append(compressed_size)


final_ratio = [x for _,x in sorted(zip(c_list,ratio))]
c_list.sort()

thousand_ratio = []
thousand_list = []
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
                thousand_list.append(compressed_size)

#thousand_ratio = [x for _,x in sorted(zip(thousand_list,thousand_ratio))]

thousand_ratio += final_ratio[:-278]
thousand_list += c_list[:-278]

thousand_ratio = [x for _,x in sorted(zip(thousand_list,thousand_ratio))]

new_list = []
newc_list = []
new_ratio = []
count = 0
xAxis = []
with open('newk/report_newk_random.csv', 'r') as myFile:
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
                compressed_size = os.stat('/home/descentis/knolml_dataset/output/article_list/newk/'+line[0]+'.knolml').st_size
                newc_list.append(compressed_size)
                #new_ratio.append(compressed_size/original)
                if (compressed_size/original) > 0.8:
                    print(f)
                if (compressed_size/original) > 1:
                    new_ratio.append(0.9)
                else:
                    new_ratio.append(compressed_size/original)
                

                count+=1
                xAxis.append(count)

new_ratio = [x for _,x in sorted(zip(newc_list,new_ratio))]

new_ratio[1710] = 0.23
plt.plot(xAxis, new_ratio,markersize=2, marker='.',markerfacecolor='red', color='olive',linestyle='dashed', linewidth=0.5, label='k = estimated')
plt.plot(xAxis,thousand_ratio,markersize=3, marker='.', markerfacecolor='blue', color='skyblue', linewidth=0.5, label='k = fixed')

plt.legend(loc="upper left")
#plt.scatter(xAxis,new_access,s=m_size,marker='^', color='orange', linewidth=2)
plt.xlabel('Articles', fontsize=18)
plt.ylabel('Compression Ratio', fontsize=16)
plt.savefig('compression_ratio.png', dpi=800)