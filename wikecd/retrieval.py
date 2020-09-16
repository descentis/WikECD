#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Sep  6 20:56:47 2020

@author: descentis
"""

import os
from multiprocessing import Process, Lock
import time
import numpy as np
import glob
import difflib
import xml.etree.ElementTree as ET
import math
import textwrap
import html
import requests
import io


class wikiRetrieval(object):
    '''
    The class with organize the full revision history of Wikipedia dataset
    '''
    
    instance_id = 1
    
    
    def indent(self,elem, level=0):
        i = "\n" + level*"  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self.indent(elem, level+1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i    

    def is_number(self, s):
        try:
            int(s)
            return True
        except ValueError:
            return False

    def encode(self, str1, str2):
    	output = ""
    	s = [x.replace("\n", "`").replace("-", "^") for x in str1.split(" ")]
    
    	s2 = [x.replace("\n", "`").replace("-", "^") for x in str2.split(" ")]
    
    	i = 0
    	while(True):
    		if i == len(s):
    			break;
    		if s[i].isspace() or s[i] == '':
    			del s[i]
    		else:	
    			i += 1	
    	i = 0
    	while(True):
    		if i == len(s2):
    			break;
    		if s2[i].isspace() or s2[i] == '':
    			del s2[i]
    		else:	
    			i += 1	
    			
    	d = difflib.Differ()
    	result = list(d.compare(s, s2))
    
    	pos = 0
    	neg = 0
    
    	for x in result:
    		if x[0] == " ":
    			pos += 1
    			if neg != 0:
    				output += "-"+str(neg)+" "
    				neg = 0
    		elif x[0] == "-":
    			neg += 1
    			if pos != 0:
    				output += str(pos)+" "
    				pos = 0	
    		elif x[0] != "?":
    			if pos != 0:
    				output += str(pos)+" "
    				pos = 0	
    			if neg != 0:
    				output += "-"+str(neg)+" "
    				neg = 0
    			if self.is_number(x[2:]):
    				output += "'"+x[2:]+"' "
    			else:			
    				output += x[2:]+" "
    	if pos != 0:
    		output += str(pos)+" "
    	if neg != 0:
    		output += "-"+str(neg)+" "
    	return output.replace("\t\t\t", "")


    def wiki_file_writer(self, elem,myFile,prefix):
        global instance_id
        t = '\t'
    
        Instance = t+t+"<Instance "
        
      
        for ch_elem in elem:        
                        
            if(('id' in ch_elem.tag) and ('parentid' not in ch_elem.tag)):             
                Instance = Instance+ "Id="+'"'+str(self.instance_id)+'"'+" InstanceType="+'"'+"Revision/Wiki"+'"'+" RevisionId="+ '"'+str(ch_elem.text)+'"'+">\n"
                myFile.write(Instance)
                
                '''
                RevisionId = t+t+t+"<RevisionId>"+ch_elem.text+"</RevisionId>\n"
                myFile.write(RevisionId)
                '''
            
            '''
            if(ch_elem.tag==prefix+'parentid'):
                ParentId = t+t+t+"<ParentId>"+ch_elem.text+"</ParentId>\n" 
                myFile.write(ParentId)
            '''

            '''
            Timestamp Information
            '''
            if('timestamp' in ch_elem.tag):
                '''
                if(f_p!=1):
                    Instance = Instance+" InstanceType= "+'"'+"wiki/text"+'"'+">\n"
                    myFile.write(Instance)
                '''
                Timestamp = t+t+t+"<TimeStamp>\n"
                myFile.write(Timestamp)
                CreationDate = t+t+t+t+"<CreationDate>"+ch_elem.text[:-1]+'.0'+"</CreationDate>\n"
                myFile.write(CreationDate)
                Timestamp = t+t+t+"</TimeStamp>\n"
                myFile.write(Timestamp)            

            '''
            Contributors information
            '''
            if('contributor' in ch_elem.tag):            
                Contributors = t+t+t+"<Contributors>\n"
                myFile.write(Contributors)
                for contrib in ch_elem:
                    if('ip' in contrib.tag):
                        LastEditorUserName = t+t+t+t+"<OwnerUserName>"+html.escape(contrib.text)+"</OwnerUserName>\n"
                        myFile.write(LastEditorUserName)                        
                    else:
                        if('username' in contrib.tag):
                            try:
                                LastEditorUserName = t+t+t+t+"<OwnerUserName>"+html.escape(contrib.text)+"</OwnerUserName>\n"
                            except:
                                LastEditorUserName = t+t+t+t+"<OwnerUserName>None</OwnerUserName>\n"
                            myFile.write(LastEditorUserName)                        
                        if(('id' in contrib.tag) and ('parentid' not in contrib.tag)):
                            LastEditorUserId = t+t+t+t+"<OwnerUserId>"+contrib.text+"</OwnerUserId>\n"
                            myFile.write(LastEditorUserId)
                    
                        
                Contributors = t+t+t+"</Contributors>\n"
                myFile.write(Contributors)


            '''
            Body/Text Information
            '''
            if('text' in ch_elem.tag):
                Body = t+t+t+"<Body>\n"
                myFile.write(Body)
                if(ch_elem.attrib.get('bytes')!=None):
                    text_field = t+t+t+t+"<Text Type="+'"'+"wiki/text"+'"'+" Bytes="+'"'+ch_elem.attrib['bytes']+'">\n'
                elif(ch_elem.text != None):
                    text_field = t+t+t+t+"<Text Type="+'"'+"wiki/text"+'"'+" Bytes="+'"'+str(len(ch_elem.text))+'">\n'
                else:
                    text_field = t+t+t+t+"<Text Type="+'"'+"wiki/text"+'"'+" Bytes="+'"'+str(0)+'">\n'
                myFile.write(text_field)
                if(ch_elem.text == None):                
                    text_body = "";
                else:
                   
                    text_body = textwrap.indent(text=ch_elem.text, prefix=t+t+t+t+t)
                    text_body = html.escape(text_body)
                Body_text = text_body+"\n"
                myFile.write(Body_text)
                text_field = t+t+t+t+"</Text>\n"
                myFile.write(text_field)        
                Body = t+t+t+"</Body>\n"
                myFile.write(Body)            
            
    
            
            if('comment' in ch_elem.tag):
                Edit = t+t+t+"<EditDetails>\n"
                myFile.write(Edit)
                if(ch_elem.text == None):                
                    text_body = "";
                else:
                    text_body = textwrap.indent(text=ch_elem.text, prefix=t+t+t+t+t)
                    text_body = html.escape(text_body)
                
                EditType = t+t+t+t+"<EditType>\n"+text_body+"\n"+t+t+t+t+"</EditType>\n"
                #Body_text = text_body+"\n"
                myFile.write(EditType)
                
                Edit = t+t+t+"</EditDetails>\n"
                myFile.write(Edit)    
    
            if('sha1' in ch_elem.tag):
                sha = ch_elem.text
                if(type(sha)!=type(None)):
                    shaText = t+t+t+'<Knowl key="sha">'+sha+'</Knowl>\n'
                    myFile.write(shaText)
                else:
                    shaText = ''
                
        Instance = t+t+"</Instance>\n"
        myFile.write(Instance)  
        self.instance_id+=1             

    def wiki_knolml_converter(self, name, *args, **kwargs):
        #global instance_id
        #Creating a meta file for the wiki article
        
        
        
        # To get an iterable for wiki file
        
        file_name = name
        context_wiki = ET.iterparse(file_name, events=("start","end"))
        # Turning it into an iterator
        context_wiki = iter(context_wiki)
        
        # getting the root element
        event_wiki, root_wiki = next(context_wiki)
        file_name = name[:-4]+'.knolml'
        file_path = file_name
        if kwargs.get('output_dir')!=None:
            file_path = file_path.replace('output','wikipedia_articles')
        
        if not os.path.exists(file_path):
            with open(file_path,"w",encoding='utf-8') as myFile:
                myFile.write("<?xml version='1.0' encoding='utf-8'?>\n")
                myFile.write("<KnolML>\n")
                myFile.write('<Def attr.name="sha" attrib.type="string" for="Instance" id="sha"/>\n')
               
            prefix = '{http://www.mediawiki.org/xml/export-0.10/}'    #In case of Wikipedia, prefic is required
            f = 0
            title_text = ''
            #try:
            for event, elem in context_wiki:
                
                if event == "end" and 'id' in elem.tag:
                    if(f==0):
                        with open(file_path,"a",encoding='utf-8') as myFile:
                             myFile.write("\t<KnowledgeData "+"Type="+'"'+"Wiki/text/revision"+'"'+" Id="+'"'+elem.text+'"'+">\n")
                             
                        f=1
                            
                if event == "end" and 'title' in elem.tag:
                    title_text = elem.text
        
                if(f==1 and title_text!=None):            
                    Title = "\t\t<Title>"+title_text+"</Title>\n"
                    with open(file_path,"a",encoding='utf-8') as myFile:
                        myFile.write(Title)
                    title_text = None
                if event == "end" and 'revision' in elem.tag:
             
                    with open(file_path,"a",encoding='utf-8') as myFile:
                        self.wiki_file_writer(elem,myFile,prefix)
                        
                        
                    elem.clear()
                    root_wiki.clear() 
            #except:
            #    print("found problem with the data: "+ file_name)
        
            with open(file_path,"a",encoding='utf-8') as myFile:
                myFile.write("\t</KnowledgeData>\n")
                myFile.write("</KnolML>\n") 
        
            self.instance_id = 1

    def compress(self, file_name, directory):
    	# file_name = input("Enter path of KML file:")
    
        tree = ET.parse(file_name)
        r = tree.getroot()
        for child in r:
            if('KnowledgeData' in child.tag):
                child.attrib['Type'] = 'Wiki/text/revision/compressed'
                root = child
                
        last_rev = ""
        length = len(root.findall('Instance'))
    
        print(length, "revisions found")
    
        count = 0
        intervalLength =  int((math.log(length)) ** 2)  
    
        # Keep the Orginal text after every 'm' revisions
        m = intervalLength+1
        for each in root.iter('Text'):
            count += 1
            if m != intervalLength+1:
                current_str = each.text
                each.text = self.encode(prev_str, current_str)
                prev_str = current_str
                # print("Revision ", count, " written")
    			
                m = m - 1
                if m == 0:
                    m = intervalLength+1
            else:
                prev_str = each.text
                # print("Revision ", count, " written")
                m = m - 1
                continue
    
        print("KnolML file created")
        # Creating directory 
        if not os.path.exists(directory):
            os.mkdir(directory)
    
        # Changing file path to include directory
        file_name = file_name.split('/')
        file_name = directory+'/'+file_name[-1]
        '''
        file_name.insert(-1, directory)
        separator = '/'
        file_name = separator.join(file_name)
        '''
    
        tree.write(file_name[:-7]+'.knolml')
        f = open(file_name[:-7]+'.knolml')
        f_str = f.read()
        f.close()
    
        f2 = open(file_name[:-7]+'.knolml', "w")
        f2.write("<?xml version='1.0' encoding='utf-8'?>\n"+f_str)
        f2.close()


    def serialCompress(self, file_name, *args, **kwargs):
        context_wiki = ET.iterparse(file_name, events=("start","end"))
        # Turning it into an iterator
        context_wiki = iter(context_wiki)
        
        # getting the root element
        event_wiki, root_wiki = next(context_wiki)
        
        length = 0
        last_rev = ""
        
        for event, elem in context_wiki:            
            if event == "end" and 'Instance' in elem.tag: 
                length += 1
        
                
                elem.clear()
                root_wiki.clear() 
                
        count = 0
        intervalLength =  int((math.log(length)) ** 2)
        
        # Keep the Orginal text after every 'm' revisions
        m = intervalLength+1
        if not os.path.exists(file_path):
        

        #print(length)
    def wikiConvert(self, *args, **kwargs):

        if(kwargs.get('output_dir')!=None):
            output_dir = kwargs['output_dir']        
        if(kwargs.get('file_name')!=None):
            file_name = kwargs['file_name']
            self.wiki_knolml_converter(file_name)
            file_name = file_name[:-4] + '.knolml'
            self.compress(file_name,output_dir)
            os.remove(file_name)            
       
        if(kwargs.get('file_list')!=None):
            path_list = kwargs['file_list']
            for file_name in path_list:            
                self.wiki_knolml_converter(file_name)
                file_name = file_name[:-4] + '.knolml'
                self.compress(file_name,output_dir)
                os.remove(file_name)
        
        if((kwargs.get('file_name')==None) and (kwargs.get('file_list')==None)):
            print("No arguments provided")