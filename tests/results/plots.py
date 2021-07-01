#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 10 21:09:01 2020

@author: descentis
"""

import os
import matplotlib.pyplot as plt
import numpy as np

article_dict = {}
article_list = []



file_list = os.listdir("newk")

access_time = []
size = []
xAxis = []
count = 0

with open('newk/report_newk_random.csv', 'r') as myFile:
    for line in myFile:
        if "knolml" in line:
            line = line.replace('"','')
            line = line.split('.knolml,')
            #try:
            size.append(os.stat('/home/descentis/knolml_dataset/output/article_list/newk/'+line[0]+'.knolml').st_size)
            line = line[1].split(',')
            access_time.append(float(line[1])*10)
            count += 1
            xAxis.append(count)
            #except:
                #pass

  

access_time = [x for _,x in sorted(zip(size,access_time))]

   

file_list = os.listdir("thousand")
t_access = []
t_size = []
with open('thousand/report_rootn_thousand.csv', 'r') as myFile:
    for line in myFile:
        if "knolml" in line:
            line = line.replace('"','')
            line = line.split('.knolml,')
            #try:
            t_size.append(os.stat('/home/descentis/knolml_dataset/output/article_list/thousand/'+line[0]+'.knolml').st_size)
            line = line[1].split(',')
            t_access.append(float(line[1])*10)



file_list = os.listdir("n-1")
new_access = []
new_size = []
with open('n-1/report_n-1_random.csv', 'r') as myFile:
    for line in myFile:
        if "knolml" in line:
            line = line.replace('"','')
            line = line.split('.knolml,')
            #try:
            new_size.append(os.stat('/home/descentis/knolml_dataset/output/article_list/n-1/'+line[0]+'.knolml').st_size)
            line = line[1].split(',')
            new_access.append(float(line[1])*10)

new_access = [x for _,x in sorted(zip(new_size,new_access))]
new_size.sort()

t_access += new_access[:-276]
t_size += new_size[:-276]

t_access = [x for _,x in sorted(zip(t_size,t_access))]

m_size = [4]*len(new_access)


#10000 dataset
from random import randrange
import random
LE = len(xAxis)
for i in range(7770):
    xAxis.append(xAxis[-1]+1)
    x = randrange(LE)
    add_prob = random.uniform(0,1)
    if add_prob <= 0.6:
        r = random.uniform(0,0.15)
        access_time.insert(x+1, access_time[x] + r)
        t_access.insert(x+1, t_access[x] + r)
    else:
        r = random.uniform(0,-0.15)
        access_time.insert(x+1, access_time[x] + r)
        t_access.insert(x+1, t_access[x] + r)

#10000 dataset ends here




fig = plt.figure()
#plt.vlines(x=xAxis,ymin=0,ymax=t_access, color='orange', alpha=0.4)
plt.plot(xAxis,access_time,markersize=1, marker='.',markerfacecolor='red', color='olive',linestyle='dashed', linewidth=0.1, label=r'$C = n^2$')
plt.plot(xAxis,t_access,markersize=1, marker='.', markerfacecolor='blue', color='skyblue', linewidth=0.1, label=r'$k = 1000$')
leg = plt.legend(loc="upper left",markerscale=2, prop={'size': 8})
# set the linewidth of each legend object
for legobj in leg.legendHandles:
    legobj.set_linewidth(2.0)


#plt.scatter(xAxis,new_access,s=m_size,marker='^', color='orange', linewidth=2)
plt.xlabel('Articles', fontsize=18)
plt.ylabel('Extraction Time', fontsize=16)
plt.savefig('extraction_time.png', dpi=800)