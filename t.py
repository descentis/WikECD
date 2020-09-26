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
from diff_match_patch import diff_match_patch
import math
import textwrap
import html
import requests
import io

import time


class wikiRetrieval(object):
    '''
    The class with organize the full revision history of Wikipedia dataset
    '''
    
    instance_id = 1
    
    def __init__(self):
            print("in init")
    
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


    def wiki_file_writer(self, *args, **kwargs):
        elem = kwargs['elem']
        myFile = kwargs['myFile']
        prefix = kwargs['prefix']
        prev_str = kwargs['prev_str']
        current_str = ''
        
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
                    text_field = t+t+t+t+"<Text Type="+'"'+"wiki/text"+'"'+" Bytes="+'"'+ch_elem.attrib['bytes']+'">'
                elif(ch_elem.text != None):
                    text_field = t+t+t+t+"<Text Type="+'"'+"wiki/text"+'"'+" Bytes="+'"'+str(len(ch_elem.text))+'">'
                else:
                    text_field = t+t+t+t+"<Text Type="+'"'+"wiki/text"+'"'+" Bytes="+'"'+str(0)+'">'
                myFile.write(text_field)
                
                if(ch_elem.text == None):                
                    text_body = ""
                    dmp = diff_match_patch()
                    p = dmp.patch_make(prev_str,text_body)
                    ch_elem.text = dmp.patch_toText(p)
                   

                else:
                    current_str = ch_elem.text
                    
                    if kwargs['compression'].lower() == 'difflib':
                        ch_elem.text = self.encode(prev_str, current_str)
                    elif kwargs['compression'].lower() == 'diff_match':
                        dmp = diff_match_patch()
                        
                        
                        p = dmp.patch_make(prev_str,current_str)
                        ch_elem.text = dmp.patch_toText(p)
                    
                text_body = html.escape(ch_elem.text)                          
                Body_text = text_body
                myFile.write(Body_text)
                text_field = "</Text>\n"
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
        return current_str          

    def wiki_knolml_converter(self, *args, **kwargs):
        #global instance_id
        #Creating a meta file for the wiki article
        
        
        
        # To get an iterable for wiki file
        name = kwargs['name']
        compression = kwargs['compression_method']
        intervalLength = kwargs['interval_length']
        file_name = name
        context_wiki = ET.iterparse(file_name, events=("start","end"))
        # Turning it into an iterator
        context_wiki = iter(context_wiki)
        
        # getting the root element
        event_wiki, root_wiki = next(context_wiki)
        file_name = name[:-4]+'.knolml'
        file_path = file_name
        prev_str= ''
        
        if kwargs.get('output_dir')!=None:
            file_name = file_name.split('/')[-1]
            file_path = kwargs['output_dir']+'/'+file_name
        
        if not os.path.exists(file_path):
            os.mkdir(kwargs['output_dir'])
            with open(file_path,"w",encoding='utf-8') as myFile:
                myFile.write("<?xml version='1.0' encoding='utf-8'?>\n")
                myFile.write("<KnolML>\n")
                myFile.write('<Def attr.name="sha" attrib.type="string" for="Instance" id="sha"/>\n')
               
            prefix = '{http://www.mediawiki.org/xml/export-0.10/}'    #In case of Wikipedia, prefic is required
            f = 0
            title_text = ''
            #try:
            count = 0
            m = intervalLength+1
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
                    

                    count+=1
                    print(count)
                    
                    if m != intervalLength+1:
                        with open(file_path,"a",encoding='utf-8') as myFile:
                            prev_str = self.wiki_file_writer(elem=elem,myFile=myFile,prefix=prefix,prev_str=prev_str,compression=compression)
                        # print("Revision ", count, " written")
            			
                        m = m - 1
                        if m == 0:
                            m = intervalLength+1
                    
                    else:
                        with open(file_path,"a",encoding='utf-8') as myFile:
                            prev_str = self.wiki_file_writer(elem=elem,myFile=myFile,prefix=prefix,prev_str=prev_str,compression='none')
                        m = m-1
                        
                    elem.clear()
                    root_wiki.clear() 
            #except:
            #    print("found problem with the data: "+ file_name)
        
            with open(file_path,"a",encoding='utf-8') as myFile:
                myFile.write("\t</KnowledgeData>\n")
                myFile.write("</KnolML>\n") 
        
            self.instance_id = 1

    @staticmethod
    def read_xml(file_name):
        
        context_wiki = ET.iterparse(file_name, events=("start","end"))
        context_wiki = iter(context_wiki)
        
        # getting the root element
        i=0
        event_wiki, root_wiki = next(context_wiki)
        avg_revision_length =[]
        for event, elem in context_wiki:
            if event == "end" and  'revision' in elem.tag:
                i=i+1
                print(i)
            
                for ch_elem in elem:
                    if 'text' in ch_elem.tag:
                        
                        if ch_elem.attrib.get('bytes')!=None:
                            
                            
                            avg_revision_length.append(ch_elem.attrib['bytes'])
                            
                        
                        elif ch_elem.text!=None:
                            
                            avg_revision_length.append(len(ch_elem.text))
                        else:
                            avg_revision_length.append(0)

                elem.clear()
                root_wiki.clear()
        
        return avg_revision_length

    @staticmethod
    def get_revision(revision,k,file_name):
        context_wiki = ET.iterparse(file_name, events=("start","end"))
        
        context_wiki = iter(context_wiki)
        event_wiki, root_wiki = next(context_wiki)

        intervalLength =k;  
        # Keep the Orginal text after every 'm' revisions
        m = intervalLength+1
        dmp = diff_match_patch()

        #offset and factor
        rev = revision
        print(rev)

        factor_length = (rev//m)*m
        offset = rev-factor_length
        count = 0
        reference_revision=''
        
        for event , elem in context_wiki:
            if event =="end" and 'Instance' in elem.tag:
                for ch_elem in elem:
                    if 'Body' in ch_elem.tag:
                        for each in ch_elem:
                            if count == factor_length:
                                reference_revision = each.text
                                if offset == 0:
                                    return reference_revision

                            if count>factor_length:
                                
                                if offset==0:
                                    return reference_revision
                                
                                current_str = each.text
                                patches = dmp.patch_fromText(current_str)
                                temp, _ = dmp.patch_apply(patches, reference_revision)
                                reference_revision = temp
                                offset = offset-1
                            
                            
                            count = count+1


        




    
    
    
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
        
                
        count = 0
        intervalLength =  int((math.log(length)) ** 2)
        
        # Keep the Orginal text after every 'm' revisions
        m = intervalLength+1

        

        #print(length)
    def wikiConvert(self, *args, **kwargs):

        if(kwargs.get('output_dir')!=None):
            output_dir = kwargs['output_dir']  
        if kwargs.get('compression_method') != None:
            compression_method = kwargs['compression_method']
        else:
            compression_method = 'diff_match'
        if(kwargs.get('file_name')!=None):
            file_name = kwargs['file_name']
            context_wiki = ET.iterparse(file_name, events=("start","end"))
            # Turning it into an iterator
            context_wiki = iter(context_wiki)
            
            # getting the root element
            event_wiki, root_wiki = next(context_wiki)
            
            length = 0
            for event, elem in context_wiki:
                if event == "end" and 'revision' in elem.tag:
                    length+=1

                    elem.clear()
                    root_wiki.clear() 
            
            if kwargs.get('k') != None:
                intervalLength = kwargs['k']
            
            self.wiki_knolml_converter(name=file_name,compression_method=compression_method, output_dir=output_dir,interval_length=intervalLength)
            #file_name = file_name[:-4] + '.knolml'
            #self.compress(file_name,output_dir)
            #os.remove(file_name)            
       
        if(kwargs.get('file_list')!=None):
            path_list = kwargs['file_list']
            for file_name in path_list:            
                self.wiki_knolml_converter(name=file_name,compression_method=compression_method)
                file_name = file_name[:-4] + '.knolml'
                self.compress(file_name,output_dir)
                os.remove(file_name)
        
        if((kwargs.get('file_name')==None) and (kwargs.get('file_list')==None)):
            print("No arguments provided")

    
    def __extract_instance(self, *args, **kwargs):
        
        revisionsDict = kwargs['revisionDict']
        m = kwargs['intervalLength']
        n = kwargs['instance_num']
        returnResult = []
        original = n
        dmp = diff_match_patch()
        #m = int((math.log(length)) ** 2) + 1
        factor = int((n-1)/(m+1))
        near_k = ((m+1)*factor)+1
        print('near k isi',near_k)
        current_str=''
        prev_str=''

        if near_k == n:
            print('full')
            prev_str = revisionsDict[n]
            result = prev_str
        else:
            print('diff')
            prev_str = revisionsDict[near_k]
            result = prev_str
            count = near_k
            while count<n:
                
                count=count+1
                print(count)
                current_str = revisionsDict[count]
                patches = dmp.patch_fromText(current_str)
                result, _ = dmp.patch_apply(patches, prev_str)
                prev_str = result

                
        return result
    


    @staticmethod
    def wiki_decompress2(filename,k,directory,decompress_time_list):
        context_wiki = ET.iterparse(filename, events=("start","end"))
        
        context_wiki = iter(context_wiki)
        event_wiki, root_wiki = next(context_wiki)
        intervalLength =k;  
        
        dmp = diff_match_patch()
    
        # Keep the Orginal text after every 'm' revisions
        m = intervalLength+1
        g=0
        start = time.thread_time()
        for event , elem in context_wiki:
            if event =="end" and 'Instance' in elem.tag:
                for ch_elem in elem:
                    if 'Body' in ch_elem.tag:
                        for each in ch_elem:
                            g=g+1
                            print(g)
                            if m!= intervalLength+1:
                                #print(each.text)
                                current_str = each.text
                                #print(current_str)
                                #print(current_str,prev_str)
                                if prev_str==None:
                                    prev_str=""
                                patches = dmp.patch_fromText(current_str)
                                each.text, _ = dmp.patch_apply(patches, prev_str)
                                #each.text = wikiConverter.encode(prev_str, current_str)
                                #p = dmp.patch_make(prev_str,current_str)
                                
                                #each.text = dmp.patch_toText(p)
                                
                                prev_str = each.text
                                # print("Revision ", count, " written")
                                
                                m = m - 1
                                if m == 0:
                                    m = intervalLength+1
                            else:
                                
                                prev_str = each.text
                                # print("Revision ", count, " written")
                                m = m - 1
                                continue

                elem.clear()
                root_wiki.clear()
        end = time.thread_time()
        decompress_time_list.append(end-start)
        print("KnolML file created")

        # Creating directory 
        





    @staticmethod 
    def wiki_decompress(file_name,k,directory,decompress_time_list):
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
        intervalLength =k;  
        
        dmp = diff_match_patch()
    
        # Keep the Orginal text after every 'm' revisions
        m = intervalLength+1
        g=0
        start = time.time()
        for each in root.iter('Text'):
            g=g+1
            print(g)
            count += 1
            if m!= intervalLength+1:
                #print(each.text)
                current_str = each.text
                #print(current_str)
                #print(current_str,prev_str)
                patches = dmp.patch_fromText(current_str)
                each.text, _ = dmp.patch_apply(patches, prev_str)
                #each.text = wikiConverter.encode(prev_str, current_str)
                #p = dmp.patch_make(prev_str,current_str)
                
                #each.text = dmp.patch_toText(p)
                
                prev_str = each.text
                # print("Revision ", count, " written")
    			
                m = m - 1
                if m == 0:
                    m = intervalLength+1
            else:
                
                prev_str = each.text
                # print("Revision ", count, " written")
                m = m - 1
                continue
        end = time.time()
        decompress_time_list.append(end-start)
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

    def instance_retreival(self, file_name, *args, **kwargs):
        # method to retrieve the revisions from the compressed format
        if kwargs.get('interval_length') != None:
            interval_length = kwargs['interval_length']
        
        if kwargs.get('instance_num') != None:
            n = kwargs['instance_num']

        context_wiki = ET.iterparse(file_name, events=("start","end"))
        context_wiki = iter(context_wiki)
        event_wiki, root_wiki = next(context_wiki)
        
        #tree = ET.parse(file_name)
        #r = tree.getroot()
        revisionsDict = {}

        """
        for child in r:
            if ('KnowledgeData' in child.tag):
                root = child
        length = len(root.findall('Instance'))
        for each in root.iter('Instance'):
            instanceId = int(each.attrib['Id'])
            for child in each:
                if 'Body' in child.tag:
                    revisionsDict[instanceId] = child[0].text
        """
        for event , elem in context_wiki:
            if event =="end" and 'Instance' in elem.tag:
                instanceId = int(elem.attrib['Id'])
                #print(instanceId)
                for ch_elem in elem:
                    if 'Body' in ch_elem.tag:
                        for each in ch_elem:
                            revisionsDict[instanceId]=each.text
        start = time.time()
        result = self.__extract_instance(revisionDict=revisionsDict, intervalLength=interval_length, instance_num=n)
        end = time.time()
        print(result)
        return end-start

    '''
    Following methods are used to download the relevant dataset from archive in Knol-ML format
    '''

    '''
    def extract_from_bzip(self, *args, **kwargs):
        # file, art, index, home, key
        file = kwargs['file']
        art = kwargs['art']
        index = kwargs['index']
        home = kwargs['home']
        key = kwargs['key']
        filet = home + "/knolml_dataset/bz2t/" + file + 't'
        chunk = 1000
        try:
            f = SeekableBzip2File(self.dump_directory + '/' + file, filet)
            f.seek(int(index))
            strData = f.read(chunk).decode("utf-8")
            artName = art.replace(" ", "_")
            artName = artName.replace("/", "__")
            if not os.path.isdir(home + '/knolml_dataset/output/' + key):
                os.makedirs(home + '/knolml_dataset/output/' + key)
            if not os.path.exists(home + '/knolml_dataset/output/' + key + '/' + artName + ".xml"):
                article = open(home + '/knolml_dataset/output/' + key + '/' + artName + ".xml", 'w+')
                article.write('<mediawiki>\n')
                article.write('<page>\n')
                article.write('\t\t<title>' + art + '</title>\n')
                # article.write(strData)
                while '</page>' not in strData:
                    article.write(strData)
                    strData = f.read(chunk).decode("utf-8", errors="ignore")
                end = strData.find('</page>')
                article.write(strData[:end])
                article.write("\n")
                article.write('</page>\n')
                article.write('</mediawiki>')
            f.close()
        except:
            print("please provide the dump information")
    def get_article_name(self, article_list):
        """Finds the correct name of articles present on Wikipedia
        Parameters
        ----------
        article_list : list[str] or str
            List of article names or single article name for which to find the correct name
        """
        if type(article_list) == list:
            articles = []
            for article in article_list:
                wiki_names = wikipedia.search(article)
                if article in wiki_names:
                    articles.append(article)
                    pass
                else:
                    print(
                        "The same name article: '" + article + "' has not been found. Using the name as: " + wiki_names[
                            0])
                    articles.append(wiki_names[0])
            return articles
        else:
            wiki_names = wikipedia.search(article_list)
            if article_list in wiki_names:
                return article_list
            else:
                print("The same name article: '" + article_list + "' has not been found. Using the name as: " +
                      wiki_names[0])
                return wiki_names[0]
    def download_from_dump(self, home, articles, key):
        if not os.path.isdir(home + '/knolml_dataset/phase_details'):
            download('knolml_dataset', verbose=True, glob_pattern='phase_details.7z', destdir=home)
            Archive('~/knolml_dataset/phase_details.7z').extractall('~/knolml_dataset')
        if not os.path.isdir(home + '/knolml_dataset/bz2t'):
            download('knolml_dataset', verbose=True, glob_pattern='bz2t.7z', destdir=home)
            Archive('~/knolml_dataset/bz2t.7z').extractall(home + '/knolml_dataset')
        fileList = glob.glob(home + '/knolml_dataset/phase_details/*.txt')
        for files in fileList:
            if 'phase' in files:
                with open(files, 'r') as myFile:
                    for line in myFile:
                        l = line.split('#$*$#')
                        if l[0] in articles:
                            print("Found hit for article " + l[0])
                            # file, art, index, home, key
                            self.extract_from_bzip(file=l[1], art=l[0], index=int(l[2]), home=home, key=key)
    '''
"""
article_list = ['Canberra.xml']



w = wikiRetrieval()

t1 = time.time()

#w.wikiConvert(file_name='Canberra.xml', output_dir='a', k='rootn')
d=[]
#w.wiki_decompress('a/Canberra.knolml',69,'aaa',[])

w.read_xml(name='Canberra.xml')

t2 = time.time()
print(t2-t1)
"""