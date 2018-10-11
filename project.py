# -*- coding: utf-8 -*-
"""
Created on Fri Apr 13 19:49:56 2018

@author: alex_
"""

import psycopg2 #make the connection to my local database and my clustered database
import boto3 #make the connection to AWS
import csv #use csv files
import time #suspend the execution of my program for few minutes


def connection_postgreSQL (dbname): #connection to the loca database, in this case I used PostgreSQL
    conn_string= "host='localhost' dbname=" + dbname + " user='postgres' password='admin'"
    conn=psycopg2.connect(conn_string)
    cursor = conn.cursor()
    return (cursor,conn);

def close_connection(cursor,conn):
    cursor.close()
    conn.close();
    return 1;    

def convert_to_local_files(directory, database_tables,cursor): #transfer from our local database to local files
    print("Converting data of our local database to local files")
    for table in database_tables:
        query="SELECT * from " + table   #get all records of the tables belong to our local database
        cursor.execute(query)
        records=cursor.fetchall()
        
        with open(directory+table+'.csv',"w") as csvfile: #convert to local files, in this case csv files
            writer=csv.writer(csvfile, delimiter=',')
            for record in records:
                writer.writerow(record)
        csvfile.close()
    

def creating_cluster(cluster_name,key_id, access_key): #create cluster in AWS (RedShift)
    print("Creating our cluster (RedShift)")
    #making the connection
    clientRS = boto3.client('redshift','us-east-2',aws_access_key_id=key_id, aws_secret_access_key=access_key)
    clientRS.create_cluster(  #creating the cluster
        ClusterIdentifier=cluster_name,
        ClusterType='multi-node',
        NodeType='dc2.large',
        MasterUsername='awsuser',
        MasterUserPassword='Admin123',
        NumberOfNodes=2,
        AvailabilityZone='us-east-2c',
        IamRoles=[
            'arn:aws:iam::675582806628:role/myRedshiftRole'
        ],  
    )
    
    #waiting the creation of the cluster
    ind=0
    while ind<6: #we'll wait for 6 min, we have to wait to create the cluster in AWS
        time.sleep(60)
        print("Waiting for our cluster (This prints each minute)")
        ind=ind+1
    print("Cluster is ready to use")

def creating_bucket(bucket_name,key_id, access_key): #create bucket in AWS (S3)
    print("Creating our bucket (S3)")
    #making the connection
    clientS3=boto3.client("s3",aws_access_key_id=key_id, aws_secret_access_key=access_key)
    clientS3.create_bucket( #creating the bucket
        ACL='private',
        Bucket=bucket_name,
        CreateBucketConfiguration={
            'LocationConstraint': 'us-east-2'
        }, 
    )
    
    return clientS3
    

def put_files_bucket(directory,clientS3,bucket_name,tables_names): #transfer local files to my bucket (S3)
    print("Transfering files from local to our bucket (S3)")
    for table in tables_names:
        with open(directory+table+'.csv', 'rb') as data:
            clientS3.upload_fileobj(data, bucket_name, table)
        data.close()
    
    
def copy_from_s3_to_redshift(directory, connect_clustered_database):#copy the files from my bucket (S3) to my database located in my cluster (RedShift)
    
    
    
    f = open(directory+"ZAGDB1.sql", "r") #in this file there are different queries to create my tables
    #read all file
    create_tables = f.read() 
    f.close()   
    
    f = open(directory+"copy_statement.txt", "r") #in this file, there are different statements to transfer data from S3 to AWS using function COPY
    #read all file
    filling_out_tables = f.read() 
    f.close()
    
    f = open(directory+"fact_table.txt", "r") #in this file, there are different queries to create a fact table
    #read all file
    create_dw = f.read() 
    f.close()
    
    conn = psycopg2.connect(connect_clustered_database) #make the connection to our clustered database (in RedShift)
    cur = conn.cursor()
    print("Creating the tables inside our Clustered Database")
    cur.execute(create_tables) #create tables in our cluster
    print("Copying from S3 to Clustered Database (RedShift)")
    cur.execute(filling_out_tables) #fill out all tables from S3 using COPY
    print("Creating our fact table")
    cur.execute(create_dw) #create a fact table in our cluster
    conn.commit()
    print("End")
    
def read_access_AWS(directory):
    f = open(directory+"Access_to_AWS.txt", "r")
    #read all lines
    line_key_id = f.readline() 
    line_access_key = f.readline()
    line_access_db_in_cluster=f.readline()
    
    #manipulating characters in string
    array1=line_key_id.split('"') #cutting the string, i want the one after the sign '='
    key_id=array1[1]
    
    array2=line_access_key.split('"')
    access_key=array2[1]
    
    array3=line_access_db_in_cluster.split('"')
    connect_clustered_database=array3[1]
    f.close()
    
    return key_id,access_key,connect_clustered_database
    
    

def main():
    databaseName="zagdb" #name of my local database
    cluster_name='anothercluster' #name of my cluster (it will be created in RedShift)
    bucket_name= 'bucket-ds530-1' #name of my bucket
    tables_names=['category','region','vendor','product','store',
                'customer','salestransaction','soldvia']  #all tables names we need to make our fact table
    directory="C:/Users/alex_/Desktop/college/DS530-BigData/project/" #directory wehere my project is located
    
    #creating local files from our local database
    cursor,conn=connection_postgreSQL(databaseName) #making our connection to our local database, PostgreSQL  
    convert_to_local_files(directory,tables_names,cursor) #transfer from our local database to local files
    close_connection(cursor,conn)
    
    
    #read the keys to get access to AWS from local
    key_id,access_key,connect_clustered_database=read_access_AWS(directory)
        
    #create cluster in AWS (RedShift)
    creating_cluster(cluster_name,key_id, access_key) 
    
    #create bucket in AWS (S3)
    clientS3=creating_bucket(bucket_name,key_id, access_key)
    
    
    #transfer local files to my bucket (S3)
    put_files_bucket(directory, clientS3,bucket_name,tables_names)
    
    #copy the files from my bucket (S3) to my database located in my cluster (RedShift)
    copy_from_s3_to_redshift(directory,connect_clustered_database) #in the same function, i'll create my tables necessary for my data and the fact table necessary to make our data warehouse


  
if __name__== "__main__":
  main()


