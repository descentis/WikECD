#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 16 16:46:26 2021

@author: descentis
"""

import xml.etree.ElementTree as ET
from operator import add

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

diff_list = []
diff_indices = []
time_list = []

for i in range(len(l) - 1):
    diff_list.append(abs(l[i]-l[i+1]) - l[i+1])
    time_list.append(l[i]+abs(l[i]-l[i+1]))
    diff_indices.append(i)
    
total_cost = list( map(add, diff_list, time_list) )
zipped_pairs = zip(total_cost, diff_indices)
sorted_indices = [x for _, x in sorted(zipped_pairs)]

memory = sum(l)
time = len(l)
cost = memory + time

new_cost = 0

k = ['|' for i in range(len(l))]

for i in sorted_indices:
    new_cost = cost + total_cost[i] - 1
    if new_cost <= cost:
        cost = new_cost
        k[i] = '.'
