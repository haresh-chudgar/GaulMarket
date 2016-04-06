# -*- coding: utf-8 -*-
"""
Created on Sat Mar  5 00:06:52 2016

@author: haresh
"""
from Peer import Peer
import sys
import time
import timeit
import threading

if(len(sys.argv)!=5):
    print("USAGE python peer1.py <PEER_ID> <PEER_TYPE> <MY IP> <PORT>")
    print ("PeerType : BUYER or SELLER")
    print ("PeerID : 1 to N")
    print("Rest features are in config file")
    exit(-1)

peerID = sys.argv[1]
peerType = sys.argv[2]
myIP = sys.argv[3]
port = int(sys.argv[4])
#print(peerID)

f = open('config.txt', 'r')
for line in f:
    line =  line.strip()
    line = line.split('=')
    #print (line)
    if(line[0]=='maxID '):
        line[1].replace(" ","")
        maxID = line[1]
    elif(line[0]=='num_neighbour '):
        num_neighbour = int(line[1])
    elif(line[0]=='hopCount '):
        hopCount = int(line[1])
    elif(line[0]=='items '):
        itmLst = line[1].split(',')
    elif(line[0]=='numItem '):
        numItem = int(line[1])
    elif(line[0]=='serverIP '):
        serverIP = line[1]



print("--------------------------------------------------------------------------------------------------------")
print("\t\t\t\tPeer ID is ",peerID," and Type is ",peerType)
print("--------------------------------------------------------------------------------------------------------")
print("\t\t\t The server IP is ", serverIP)
p1 = Peer(peerType,peerID,maxID,num_neighbour,itmLst,numItem,hopCount,myIP,port)

print(peerID, maxID)
if(int(peerID) == 1):#int(maxID)):
    print("Starting Election")
    p1.startElection()


if(peerType=="SELLER"):
    print("Seller is ready to sell")
time.sleep(5)

item_no=1
if(peerType=="BUYER"):
    print("Buyer is Ready, starting to buy")
    while(1):
        start = timeit.default_timer()
        print ("Start time to buy this item is ",start," Item is "+str(item_no) )
        threading.Thread(target = p1.buyAnotherItem).start()
        time.sleep(3)



#get my ip address and port (any)