#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Feb 28 19:46:39 2021

@author: descentis
"""

from itertools import combinations
import xml.etree.ElementTree as ET


def lindexsplit(List, lindex):
    index_list = lindex
    index_list.sort()

    new_list = []

    #print(index_list)

    len_index = len(index_list)
    for idx_index, index in enumerate(index_list):
        if len(index_list) == 1:
            new_list = [List[:index+1], List[index+1:]]
        else:
            if idx_index==0:
                new_list.append(List[:index+1])
                # print('Start', List[:index+1])
            elif idx_index==len_index-1:
                new_list.append(List[index_list[idx_index - 1] + 1:index + 1])
                # print('End', List[index_list[idx_index - 1] + 1:index + 1])
                if List[index+1:]:
                    new_list.append(List[index+1:])
                    # print('End', List[index+1:])
            else:
                new_list.append(List[index_list[idx_index-1]+1:index+1])
                # print('Between', List[index_list[idx_index-1]+1:index+1])

    return new_list

memory_cost_list = []
time_cost_list = []
lable_list = []


#parsing the Wikipedia file and getting the text length
context_wiki = ET.iterparse('/home/descentis/knolml_dataset/output/article_list/12-inch_coast_defense_mortar.xml', events=("start","end"))
# Turning it into an iterator
context_wiki = iter(context_wiki)

# getting the root element
event_wiki, root_wiki = next(context_wiki)

l = []
count = 1
for event, elem in context_wiki:
    if event == "end" and 'revision' in elem.tag:
        for ch in elem:
            if 'text' in ch.tag:
                l.append(len(ch.text))

        elem.clear()
        root_wiki.clear() 

mem_cost = 0
time_cost = 0
ls = ''
for e in range(len(l)-1):
    ls += str(l[e]) + '.'
    mem_cost += abs(l[e] - l[e+1])
    time_cost += l[e] + abs(l[e] - l[e+1])    
ls += str(l[len(l)-1])
lable_list.append(ls)
memory_cost_list.append(mem_cost)
time_cost_list.append(time_cost)    
indices = [i for i in range(len(l)-1)]

for ind in range(1,len(l)):
    a = list(combinations(indices,ind))
    for each in a:
        each = list(each)
        split_result = lindexsplit(l,each)
        mem_cost = 0
        time_cost = 0
        lable_string = ''
        for k in split_result:
            if len(k) == 1:
                mem_cost += k[0]
                time_cost += 1
                lable_string += str(k[0])+'|'
            else:
                mem_cost += k[0]
                for rev_index in range(len(k)-1):
                    mem_cost += abs(k[rev_index] - k[rev_index+1])
                    time_cost += k[rev_index] + abs(k[rev_index] - k[rev_index+1]) + 1
                    lable_string += str(k[rev_index])+'.'
                lable_string += str(k[len(k)-1])+'|'
        lable_string = lable_string[:-1]
        lable_list.append(lable_string)
        memory_cost_list.append(mem_cost)
        time_cost_list.append(time_cost)


from operator import add
total_list = list( map(add, memory_cost_list, time_cost_list) )
ind = [i for i in range(len(total_list))]
zipped_pairs = zip(total_list, ind)
z = [x for _, x in sorted(zipped_pairs)]

#plotting all the possibilities
'''
# libraries
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
 
# Create a dataframe
value1=memory_cost_list
value2=time_cost_list
df = pd.DataFrame({'group':lable_list, 'value1':value1 , 'value2':value2 })
 
# Reorder it following the values of the first value:
ordered_df = df.sort_values(by='value1')
my_range=range(1,len(df.index)+1)
 
# The horizontal plot is made using the hline function
plt.hlines(y=my_range, xmin=ordered_df['value1'], xmax=ordered_df['value2'], color='grey', alpha=0.4)
plt.scatter(ordered_df['value1'], my_range, color='skyblue', alpha=1, label='value1')
plt.scatter(ordered_df['value2'], my_range, color='green', alpha=0.4 , label='value2')
plt.legend()
 
# Add title and axis names
plt.yticks(my_range, ordered_df['group'])
plt.title("Comparison of the value 1 and the value 2", loc='left')
plt.xlabel('Value of the variables')
plt.ylabel('Group')

fig = plt.gcf()
fig.set_size_inches(18.5, 18.5)
fig.savefig('test2png.png', dpi=100)

# Show the graph
#plt.show()            
'''