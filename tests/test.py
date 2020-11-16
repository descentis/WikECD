#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov  5 17:15:25 2020

@author: descentis
"""

import bz2
import time
import subprocess

url = 'https://dumps.wikimedia.org/enwiki/20201101/'

dump_list = []
with open('all_wiki_dump2.txt', 'r') as myFile:
    for line in myFile:
        line = line.split(' ')
        dump_list.append(line[0])
#dump_list = ['enwiki-20200801-pages-meta-history16.xml-p11423633p11424430.bz2', 'enwiki-20200801-pages-meta-history16.xml-p11424431p11424831.bz2', 'enwiki-20200801-pages-meta-history16.xml-p11424832p11424936.bz2']

t1 = time.time()

for dump in dump_list:
    new_url = url+dump
    subprocess.run(["aria2c", "-x3", new_url])
    t = ''
    ns_flag = 0
    offset = 0
    file_name = dump.split('xml-')[1][:-4]
    file_name += '.txt'
    with bz2.BZ2File(dump, 'r') as myFile:
        for line in myFile:
            line = line.decode('utf-8')
            if line[0] == ' ' and line[1] == ' ' and line[2] == ' ' and line[3] == ' ' and line[4] == '<' and line[5] == 't':
                if '<title>' in line:
                    t = line.split('<title>')[1].replace('</title>\n', '')
                    offset = myFile.tell()
    
            if line[0] == ' ' and line[1] == ' ' and line[2] == ' ' and line[3] == ' ' and line[4] == '<' and line[5] == 'n':
                if '<ns>' in line:
                    ns = line.split('<ns>')[1].replace('</ns>\n', '')
                    if ns == '0' or ns == '1':
                        ns_flag = 1
            
            if ns_flag == 1:
                with open(file_name, 'a') as newFile:
                    newFile.write(t+'$#$'+str(offset)+'\n')
                ns_flag = 0
    
    subprocess.run(["rm", dump])

t2 = time.time()
print(t2-t1)