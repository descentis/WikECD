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

    def wiki_file_writer(elem,myFile,prefix):
        global instance_id
        t = '\t'
    
        Instance = t+t+"<Instance "
        
      
        for ch_elem in elem:        
                        
            if(('id' in ch_elem.tag) and ('parentid' not in ch_elem.tag)):             
                Instance = Instance+ "Id="+'"'+str(wikiConverter.instance_id)+'"'+" InstanceType="+'"'+"Revision/Wiki"+'"'+" RevisionId="+ '"'+str(ch_elem.text)+'"'+">\n"
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
        wikiConverter.instance_id+=1             