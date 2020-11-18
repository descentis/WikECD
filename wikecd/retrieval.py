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
import wikipedia
from internetarchive import download
from pyunpack import Archive
import time


class instances(object):
    """
    creating the instance of each object.
    The init function defined stores each instance's attribute which can be analyzed separately
    """

    def __init__(self, instance, title):
        # self.test = 'jsut to check the instances class'
        # print(self.test)
        # print(instance.tag)
        self.instanceId = instance.attrib['Id']
        self.instanceType = instance.attrib['InstanceType']
        self.instanceTitle = title
        if instance.attrib.get('RevisionId') is not None:
            self.revId = instance.attrib['RevisionId']
        self.instance_attrib = {}
        for ch1 in instance:
            if 'TimeStamp' in ch1.tag:
                self.instance_attrib['TimeStamp'] = {}
                for ch2 in ch1:
                    if 'CreationDate' in ch2.tag:
                        self.instance_attrib['TimeStamp']['CreationDate'] = ch2.text
                    if 'LastEditDate' in ch2.tag:
                        self.instance_attrib['TimeStamp']['LastEditDate'] = ch2.text
                    if 'LastActivityDate' in ch2.tag:
                        self.instance_attrib['TimeStamp']['LastActivityDate'] = ch2.text
                    if 'CommunityOwnedDate' in ch2.tag:
                        self.instance_attrib['TimeStamp']['CommunityOwnedDate'] = ch2.text
                    if 'ClosedDate' in ch2.tag:
                        self.instance_attrib['TimeStamp']['ClosedDate'] = ch2.text

            if 'Contributors' in ch1.tag:
                self.instance_attrib['Contributors'] = {}
                for ch2 in ch1:
                    if 'OwnerUserId' in ch2.tag:
                        self.instance_attrib['Contributors']['OwnerUserId'] = ch2.text
                    if 'OwnerUserName' in ch2.tag:
                        self.instance_attrib['Contributors']['OwnerUserName'] = ch2.text
                    if 'LastEditorUserId' in ch2.tag:
                        self.instance_attrib['Contributors']['LastEditorUserId'] = ch2.text

            if 'Body' in ch1.tag:
                self.instance_attrib['Body'] = {}
                for ch2 in ch1:
                    if 'Text' in ch2.tag:
                        self.instance_attrib['Body']['Text'] = {}
                        self.instance_attrib['Body']['Text']['#Type'] = ch2.attrib['Type']
                        self.instance_attrib['Body']['Text']['#Bytes'] = ch2.attrib['Bytes']
                        self.instance_attrib['Body']['Text']['text'] = ch2.text

            if 'Tags' in ch1.tag:
                self.instance_attrib['Tags'] = ch1.text

            if 'Credit' in ch1.tag:
                self.instance_attrib['Credit'] = {}
                for ch2 in ch1:
                    if 'Score' in ch2.tag:
                        self.instance_attrib['Credit']['Score'] = ch2.text
                    if 'CommentCount' in ch2.tag:
                        self.instance_attrib['Credit']['CommentCount'] = ch2.text
                    if 'ViewCount' in ch2.tag:
                        self.instance_attrib['Credit']['ViewCount'] = ch2.text
                    if 'AnswerCount' in ch2.tag:
                        self.instance_attrib['Credit']['AnswerCount'] = ch2.text
                    if 'FavouriteCount' in ch2.tag:
                        self.instance_attrib['Credit']['FavouriteCount'] = ch2.text

    def is_question(self):
        """
        Returns True if the instance is a question
        Works with QnA based knolml dataset

        Returns
        -------
        \*\*closed : bool
            Returns true if the post is a question , if applicable
        """
        if self.instanceType == 'Question':
            return True

    def is_answer(self):
        """
        Returns True if the instance is an answer
        Works with QnA based knolml dataset

        Returns
        -------
        \*\*closed : bool
            Returns true if the post is an answer, if applicable
        """
        if self.instanceType == 'Answer':
            return True

    def is_comment(self):
        """
        Returns True if the instance is a comment
        Works with QnA based knolml dataset
        
        Returns
        -------
        \*\*closed : bool
            Returns true if the post is a comment, if applicable
        """
        if self.instanceType == 'Comments':
            return True

    def is_closed(self):
        """
        Returns True if the qna thread is closed
        Works with QnA based knolml dataset
        
        Returns
        -------
        \*\*closed : bool
            Returns true if the post is close, if applicable
        """
        if self.instance_attrib['TimeStamp'].get('ClosedDate') is None:
            return True

    def just_to_check(self):
        print("just to check function")
        print(self.instanceId)
        print(self.instanceType)

    def get_editor(self):
        """
        Returns the edior details

        Returns
        -------
        \*\*editor : dictionary
            Details related to the editor of this instance
        """
        di = {}
        if self.instance_attrib['Contributors'].get('OwnerUserId') is not None:
            di['OwnerUserId'] = self.instance_attrib['Contributors']['OwnerUserId']
        if self.instance_attrib['Contributors'].get('OwnerUserName') is not None:
            di['OwnerUserName'] = self.instance_attrib['Contributors']['OwnerUserName']
        if self.instance_attrib['Contributors'].get('LastEditorUserId') is not None:
            di['LastEditorUserId'] = self.instance_attrib['Contributors']['LastEditorUserId']
        return di

    def get_title(self):
        """
        Returns the title

        Returns
        -------
        \*\*title : str
            Title of the Knowledge Data
        """
        return self.instanceTitle

    def get_tags(self):
        """
        Returns the tag details
        Works for QnA dataset
        
        Returns
        -------
        \*\*tags : list
            List of tags, if available
        """
        if self.instance_attrib.get('Tags') is not None:
            return self.instance_attrib['Tags'].split('><')
        else:
            print("No tags are found")

    def get_timestamp(self):
        """
        Returns the timestamp details
        
        Returns
        -------
        \*\*timestamp : dictionary
            Timestamp details of this instance
        """
        di = {}
        if self.instance_attrib['TimeStamp'].get('CreationDate') is not None:
            di['CreationDate'] = self.instance_attrib['TimeStamp']['CreationDate']
        if self.instance_attrib['TimeStamp'].get('LastEditDate') is not None:
            di['LastEditDate'] = self.instance_attrib['TimeStamp']['LastEditDate']
        if self.instance_attrib['TimeStamp'].get('LastActivityDate') is not None:
            di['LastActivityDate'] = self.instance_attrib['TimeStamp']['LastActivityDate']
        if self.instance_attrib['TimeStamp'].get('CommunityOwnedDate') is not None:
            di['CommunityOwnedDate'] = self.instance_attrib['TimeStamp']['CommunityOwnedDate']
        if self.instance_attrib['TimeStamp'].get('ClosedDate') is not None:
            di['ClosedDate'] = self.instance_attrib['TimeStamp']['ClosedDate']
        return di

    def get_score(self):
        """
        Returns the score details
        
        Returns
        -------
        \*\*score : dictionary
            A dictionary of score values, if available
        """
        if self.instance_attrib.get('Credit') is None:
            return 'Score value is not available'
        di = {}
        if self.instance_attrib['Credit'].get('Score') is not None:
            di['Score'] = self.instance_attrib['Credit']['Score']
        if self.instance_attrib['Credit'].get('CommentCount') is not None:
            di['CommentCount'] = self.instance_attrib['Credit']['CommentCount']
        if self.instance_attrib['Credit'].get('ViewCount') is not None:
            di['ViewCount'] = self.instance_attrib['Credit']['ViewCount']
        if self.instance_attrib['Credit'].get('AnswerCount') is not None:
            di['AnswerCount'] = self.instance_attrib['Credit']['AnswerCount']
        if self.instance_attrib['Credit'].get('FavouriteCount') is not None:
            di['FavouriteCount'] = self.instance_attrib['Credit']['FavouriteCount']
        return di

    def get_text(self, *args, **kwargs):
        """
        Returns the text data
        
        Parameters
        ----------
        \*\*clean : bool, optional
        
        Returns
        -------
        \*\*text : str
            actual text of the instance
        """
        di = {}

        if self.instance_attrib['Body']['Text'].get('text') is not None:
            di['text'] = self.instance_attrib['Body']['Text']['text']
        clean = False
        if kwargs.get('clean') is not None:
            clean = kwargs['clean']
            if clean:
                di['text'] = getCleanText(di['text'])

                '''
                qe = QueryExecutor()
                qe.setOutputFileDirectoryName('lol')
                qe.setNumberOfProcesses(5)
                qe.setNumberOfBytes(2000000000)
                qe.setTextValue(di['text'])
                qe.runQuery()
                return qe.result()
                '''
        return di

    def get_bytes(self):
        """
        Returns the bytes detail
        
        Returns
        -------
        \*\*bytes : int
            number of bytes given text has
        """
        if self.instance_attrib['Body']['Text'].get('#Bytes') is not None:
            return int(self.instance_attrib['Body']['Text']['#Bytes'])

    def __count_words(self, text):
        """Returns number of words in the text

        Parameters
        ----------
        text : str
            TODO
        """
        text = text.lower()
        skips = [".", ",", ":", ";", "'", '"']
        for ch in skips:
            text = text.replace(ch, "")
        word_counts = Counter(text.split(" "))
        return word_counts

    def __get_emailid(self, text):
        """Returns the email ids in the text

        Parameters
        ----------
        text : str
            TODO

        """
        lst = re.findall('\S+@\S+', text)
        return lst

    def __get_url(self, text):
        """
        Returns all the the urls in the text

        Parameters
        ----------
        text : str
            TODO

        """
        url = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
        return url

    def get_text_stats(self, *args, **kwargs):
        """
        Returns the email ids in the text

        Parameters
        ----------
        title : bool, optional

        count_words : str, optional

        url : str, optional

        """
        title = False
        if kwargs.get('title') is not None:
            if kwargs['title'] is True:
                title = True
        if title:
            if kwargs.get('count_words') is not None:
                return self.__count_words(self.title)
            if kwargs.get('email_id') is not None:
                return self.__get_emailid(self.title)
            if kwargs.get('url') is not None:
                return self.__get_url(self.title)
        else:
            if kwargs.get('count_words') is not None:
                return self.__count_words(self.get_text(clean=True)['text'])
            if kwargs.get('email_id') is not None:
                return self.__get_emailid(self.get_text()['text'])
            if kwargs.get('url') is not None:
                return self.__get_url(self.get_text()['text'])


class wikiRetrieval(object):
    '''
    The class with organize the full revision history of Wikipedia dataset
    '''
    def __init__(self, *args, **kwargs):
        if kwargs.get('interval_length') != None:
            self.interval_length = kwargs['interval_length']
        else:
            self.interval_length = 'newk'
    
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
                    current_str = "";
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
            with open(file_path,"w",encoding='utf-8') as myFile:
                myFile.write("<?xml version='1.0' encoding='utf-8'?>\n")
                myFile.write("<KnolML>\n")
                myFile.write('<Def attr.name="sha" attrib.type="string" for="Instance" id="sha"/>\n')
               
            prefix = '{http://www.mediawiki.org/xml/export-0.10/}'    #In case of Wikipedia, prefic is required
            f = 0
            title_text = ''
            #try:
            count = 0
            m = intervalLength
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
                    
                    
                    if count % intervalLength != 0:
                        with open(file_path,"a",encoding='utf-8') as myFile:
                            prev_str = self.wiki_file_writer(elem=elem,myFile=myFile,prefix=prefix,prev_str=prev_str,compression=compression)
                        # print("Revision ", count, " written")
            			
                        #m = m - 1
                        #if m == 0:
                            #m = intervalLength+1
                    
                    else:
                        with open(file_path,"a",encoding='utf-8') as myFile:
                            prev_str = self.wiki_file_writer(elem=elem,myFile=myFile,prefix=prefix,prev_str=prev_str,compression='none')
                        #m = m-1
                    count+=1
                    
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
                if kwargs['k'] == 1:
                    intervalLength = 1
                if kwargs['k'] == 'rootn':
                    intervalLength = int(length**(1/2))
                    print(intervalLength)
                if kwargs['k'] == 'thousand':
                    intervalLength = 1000
                if kwargs['k'] == 'n':
                    intervalLength = length-1                
                
            
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
 
        #testing the extraction with new interval
        if (n-1)%m != 0:
            count = int((n-1)/m)*m + 1
            prev_str = revisionsDict[count]
            result = prev_str
            while count < n:
                count += 1
                current_str = revisionsDict[count]
                patches = dmp.patch_fromText(current_str)
                result, _ = dmp.patch_apply(patches, prev_str)
                prev_str = result
        
        else:
            prev_str = revisionsDict[n]
            result = prev_str

        '''
        if n % m != 0:
            interval = n - (n % m) + 1
            #print('interval', interval)
            n = n - interval + 1
            count = interval
            prev_str = revisionsDict[count]
            result = prev_str
            while count < original:
                #print("yes")
                count += 1
                #print(repr(revisionsDict[count]))
                current_str = revisionsDict[count]
                #print(revisionsDict[count])
                patches = dmp.patch_fromText(current_str)
                result, _ = dmp.patch_apply(patches, prev_str)
                
                prev_str = result
        else:
            interval = n - (m - 1)
            n = n - interval + 1
            count = interval
            prev_str = revisionsDict[count]
            result = prev_str
        '''
        return result

    def instance_retreival(self, file_name, *args, **kwargs):
        # method to retrieve the revisions from the compressed format
        if kwargs.get('interval_length') != None:
            interval_length = kwargs['interval_length']
        else:
            interval_length = 'rootn'
        
        if kwargs.get('instance_num') != None:
            n = kwargs['instance_num']
        tree = ET.parse(file_name)
        r = tree.getroot()
        revisionsDict = {}

        for child in r:
            if ('KnowledgeData' in child.tag):
                root = child
        length = len(root.findall('Instance'))
        for each in root.iter('Instance'):
            instanceId = int(each.attrib['Id'])
            for child in each:
                if 'Body' in child.tag:
                    revisionsDict[instanceId] = child[0].text
        
        if interval_length == 'rootn':
            intervalLength = int((length)**(1/2))
            #print('length', length)
            #print('intervalLength', intervalLength)
            #t1 = time.time()
            result = self.__extract_instance(revisionDict=revisionsDict, intervalLength=intervalLength, instance_num=n)
            #t2 = time.time()
            #print(t2-t1)
        
        if interval_length == 'thousand':
            intervalLength = 1001
            #print('length', length)
            #print('intervalLength', intervalLength)
            #t1 = time.time()
            result = self.__extract_instance(revisionDict=revisionsDict, intervalLength=intervalLength, instance_num=n)
            #t2 = time.time()
            #print(t2-t1)
            
        if interval_length == 'n':
            intervalLength = length - 1
            #print('length', length)
            #print('intervalLength', intervalLength)
            #t1 = time.time()
            result = self.__extract_instance(revisionDict=revisionsDict, intervalLength=intervalLength, instance_num=n)
            #t2 = time.time()
            #print(t2-t1)

        if interval_length == 'one':
            intervalLength = 1
            #print('length', length)
            #print('intervalLength', intervalLength)
            #t1 = time.time()
            result = self.__extract_instance(revisionDict=revisionsDict, intervalLength=intervalLength, instance_num=n)
            #t2 = time.time()
            #print(t2-t1)
        return result
    '''
    Following methods are used to download the relevant dataset from archive in Knol-ML format
    '''

    def extract_from_bzip(self, *args, **kwargs):
        """Finds the correct name of articles present on Wikipedia

        Parameters
        ----------
        article_list : list[str] or str
            List of article names or single article name for which to find the correct name

        """
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
article_list = ['George_W._Bush.xml', 'Donald_Trump.xml', 'List_of_WWE_personnel.xml', 'United_States.xml']

path_name = '/home/descentis/knolml_dataset/output/article_list/'

w = wikiRetrieval()

t1 = time.time()
for each in article_list:
    file_name = path_name+each
    w.wikiConvert(file_name=file_name, output_dir='/home/descentis/research/working_datasets/wikced/k_one', k=1)
    w.wikiConvert(file_name=file_name, output_dir='/home/descentis/research/working_datasets/wikced/k_root_n', k='rootn')
    w.wikiConvert(file_name=file_name, output_dir='/home/descentis/research/working_datasets/wikced/k_thousand', k='thousand')
    w.wikiConvert(file_name=file_name, output_dir='/home/descentis/research/working_datasets/wikced/k_n', k='n')

t2 = time.time()
print(t2-t1)


w = wikiRetrieval()

article_list = ['George_W._Bush.knolml', 'Donald_Trump.knolml', 'List_of_WWE_personnel.knolml', 'United_States.knolml']

path_name = '/home/descentis/knolml_dataset/output/article_list/'

from random import randint
from statistics import mean 
time_dict = {}
#for each in article_list:
each = 'George_W._Bush.knolml'
file_name = path_name+each


time1 = []
for i in range(100):
    t1 = time.time()
    x = randint(100, 3000)
    w.wikiConvert(file_name='/home/descentis/research/working_datasets/wikced/k_one/'+each, interval_length='one', instance_num=x)
    t2 = time.time()
    time1.append(t2-t1)
time_dict['k_one'] = mean(time1)


time2 = []
for i in range(100):
    x = randint(100, 3000)
    t1 = time.time()   
    w.instance_retreival(file_name='/home/descentis/research/working_datasets/wikced/k_root_n/'+each, interval_length='root_n', instance_num=x)
    t2 = time.time()
    time2.append(t2-t1)
time_dict['k_root_n'] = mean(time2)

time3 = []
for i in range(100):
    x = randint(100, 3000)
    t1 = time.time()
    w.instance_retreival(file_name='/home/descentis/research/working_datasets/wikced/k_thousand/'+each, interval_length='thousand', instance_num=x)
    t2 = time.time()
    time3.append(t2-t1)
time_dict['k_thousand'] = mean(time3)

time4 = []
for i in range(100):
    x = randint(100, 3000)
    t1 = time.time()
    w.instance_retreival(file_name='/home/descentis/research/working_datasets/wikced/k_n/'+each, interval_length='n', instance_num=x)
    t2 = time.time()
    time4.append(t2-t1)
time_dict['k_n'] = mean(time4)    
'''  

