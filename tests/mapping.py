#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 16 16:52:16 2020

@author: descentis
"""
import bz2

title = ''
id_tag = ''
ns_flag = 0
title_offset = 0
with bz2.BZ2File('/home/descentis/research/working_datasets/wikipedia_full/enwiki-20201001-pages-meta-history13.xml-p11419487p11422680.bz2', 'r') as fp:
    for line in fp:
        line = line.decode('utf-8')
        if line[0] == ' ' and line[1] == ' ' and line[2] == ' ' and line[3] == ' ' and line[4] == '<' and line[5] == 't':
            if '<title>' in line:
                t = line.split('<title>')[1].replace('</title>\n', '')
                title_offset = fp.tell()

        if line[0] == ' ' and line[1] == ' ' and line[2] == ' ' and line[3] == ' ' and line[4] == '<' and line[5] == 'n':
            if '<ns>' in line:
                ns = line.split('<ns>')[1].replace('</ns>\n', '')
                if ns == '0' or ns == '1':
                    ns_flag = 1
        
        if ns_flag == 1:
            with open('index.txt', 'a') as newFile:
                newFile.write(t+'$#$'+str(title_offset)+'\n')
            ns_flag = 0