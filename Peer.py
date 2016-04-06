# -*- coding: utf-8 -*-

import Pyro4
import random
import threading
import timeit
from collections import deque

buy_lock = threading.Lock()#Lock used by buyer when it establishes a connection with the seller to buy the product
sell_lock = threading.Lock()#Lock used by seller to decrement he count of object when it is sold
request_map_lock  = threading.Lock()#Lock to update the request map
election_lock  =  threading.Lock()

class Peer:
    def __init__(self, peerType, peerID, maxID, num_neighbours, hopCount, itemList, noItems, maxHops, myIP, myPort):
        
        #Name server helps it connect to peers through names
        self.nameServer = Pyro4.locateNS()
        
        domain = "gaul.market."
        
        self.peerID = domain+peerID
        
        daemon =  self.registerItems(myIP, myPort)
        
        #A thread continues to listen incoming requests at the peer
        threading.Thread(target = daemon.requestLoop).start()
        
        #If the peer ID = maxPeer id then calculate the neighbours and add the edges in a different function
        self.num_neighbours = num_neighbours
        
        self.neighbours = {}
        
        self.maxID = int(maxID)
        #print (self.peerID)
        #print (domain+str(self.maxID))
        #print (self.peerID == domain+str(self.maxID))
        
        #Create the graph when the node id is same as the max id of the node given in config file
        if(self.peerID == domain+str(1)):#self.maxID)):
            #create a graph and add the neighbors
            self.create_graph()
        #else:
        #chill
        
        self.peerType = peerType
        self.requestMap = {}
        
        #Config
        self.hopCount = hopCount
        self.itemList = itemList
        self.noItems = noItems
        self.maxItems = noItems
        self.item = itemList[1]
        self.maxHops = maxHops
        
        self.money = 0
        self.chooseItem()
        self.requestID = 0
        self.boughtItemsTime = {}
        self.averageTime = 0
        self.itemsBought = 0
        
        self.parent = -1
        self.max = self.peerID
        self.isLeaderElected = False
        self.leaderURI = None

        #Variables for trader        
        self.isLeader = False
        self.itemsInMarket = {}
        self.requestsQueue = deque()
        
        #For synchronization        
        self.vectorClock = []
        for i in range(maxID):
            self.vectorClock.append(0)
    
    #It is used to create connections between the peers in a randomized fashion
    def create_graph(self):
        
        i=1
        neigh={}
        while i<=self.maxID :
            neigh[i]=[]
            i+=1

        i=1

        #covered is the list of nodes which are yet to be covered
        #It helps us ensure that all nodes in the graph are connected.
        covered = list(range(1,self.maxID+1))
        while i<=self.maxID:
            if(i in covered):
                covered.remove(i)
            failed_iter=0
            while len(neigh[i])<self.num_neighbours:
                if(len(covered)>0 ):
                    random.shuffle(covered)
                    if(covered[0]==i):
                        if(len(covered)>1):
                            insert = 1
                        else:
                            tmp = random.randint(1,self.maxID)
                            if(tmp==i):
                                tmp = (tmp)%self.maxID+1
                            covered.append(tmp)
                            insert = 1
                    else:
                        insert=0
                    neigh[i].append(covered[insert])
                    neigh[covered[insert]].append(i)
                    covered.remove(covered[insert])
                else:
                    tmp = random.randint(1,self.maxID)
                    
                    if(not (tmp in neigh[i]) and len(neigh[tmp])<self.num_neighbours and tmp!=i):
                        neigh[i].append(tmp)
                        neigh[tmp].append(i)
                        failed_iter=0
                    else:
                        failed_iter+=1
                        if(failed_iter>5 and tmp!=i and not (tmp in neigh[i])):
                            neigh[i].append(tmp)
                            neigh[tmp].append(i)
            i+=1
        
        #neigh={1: [ 3,4, 5], 2: [ 4,5, 6], 3: [ 1,4, 6], 4: [1,2, 3], 5: [1,2, 3], 6: [1,2, 3]}
        print ("Graph of nodes is the following")

        print (neigh)

        URI={}
        for pID, pURI in self.nameServer.list(prefix="gaul.market.").items():
            id = pID
            id = id.replace("gaul.market.","")
            id = int(id)
            URI[id] = pURI
            
            
            
        for pID, pURI in self.nameServer.list(prefix="gaul.market.").items():
            print (pID)
            id = pID
            id = id.replace("gaul.market.","")
            id = int(id)
            peer = Pyro4.Proxy(pURI)
            for neigh_id in neigh[id]:
                peer.addNeighbour("gaul.market."+str(neigh_id), URI[neigh_id])

        print ("Added all the neighbours of the nodes in respective adjacency lists and everyone is ready to communicate")
    
    def check_parent(self):
        return (self.parent==-1)
    
    def startElection(self):
        print("Starting Election")
        self.isLeaderElected = False
        self.isLeader = False
        self.parent = self.peerID
        self.max = self.peerID
        for pID,pURI in self.neighbours.items():
            self.requestMap[(pID,"election")]= 1
            print ("Election Lookup", pID)
            if(pURI.check_parent()):
                threading.Thread(target = pURI.election_lookup, args=[self.peerID]).start()
    
    def election_lookup( self, requestingPeerID):
        self.isLeaderElected = False
        self.isLeader = False
        election_lock.acquire()
        if(self.parent==-1):
            self.max = self.peerID
            self.parent = requestingPeerID
            forwarded = False
            for pID,pURI in self.neighbours.items():
                if(pID != requestingPeerID):
                    if(pURI.check_parent()):
                        self.requestMap[(pID,"election")]= 1
                        print("Election Lookup", pID)
                        threading.Thread(target = pURI.election_lookup, args=[self.peerID]).start()
                        forwarded = True
            if(forwarded ==False):
                self.neighbours[requestingPeerID].election_reply(self.peerID)
        election_lock.release()

    def election_reply(self, requestingPeerID):
        #If I started election then this function should return by noting down the leader and call broadcast leader
        #broadcast leader will update the requestmap of all reply and election types...
        print("Election Reply", requestingPeerID)
        reqID = int(requestingPeerID.replace("gaul.market.", ""));
        maxID = int(self.max.replace("gaul.market.", ""));
        election_lock.acquire()        
        if(maxID < reqID):#extract peer id number here
            self.max = requestingPeerID
        election_lock.r()
        self.requestMap[(requestingPeerID,"reply")] = 1
        all_set = False
        for pID,pURI in self.neighbours.items():
            print(self.requestMap)
            if(self.requestMap[(requestingPeerID,"election")]==1):
                if(not (self.requestMap[(requestingPeerID,"reply")] ==1)):
                    all_set=False
                    break
            all_set=True
        if(all_set):
            if(self.parent == self.peerID):
                print("Leader is " + self.max)
                threading.Thread(target = self.broadcastElectionResult, args=[self.peerID, self.max]).start()
            else:
                self.requestMap.clear()
                for pID,pURI in self.neighbours.items():
                    if(pID != self.parent):
                        threading.Thread(target = pURI.election_lookup, args=[self.max]).start()
            self.parent=-1

    def broadcastElectionResult(self, requestID, leaderID):
        
        if(self.isLeaderElected == True):
            return
        
        self.leaderID = leaderID
        self.isLeaderElected = True

        print("Our new Leader is...", leaderID)
        if(leaderID == self.peerID):
            self.isLeader = True
            print("I am assigned as leader")
        else:
            self.isLeader = False
            self.leaderURI = self.nameServer.lookup(leaderID)
            
        for pID,pURI in self.neighbours.items():
            if(pID != requestID):
                threading.Thread(target = pURI.broadcastElectionResult, args=[self.peerID, leaderID]).start()
                    
#update the max node id
#if all replies heard great and reply to parent else exit

    def addNeighbour(self, pID, pURI):
        print("Neighbours is being added with node id = ",pID)
        self.neighbours[pID]  = Pyro4.Proxy(pURI)
            
    """Pick randomly from self.items and reset noItems"""
    def chooseItem(self):
        itemIndex = int(random.random() * len(self.itemList))
        if(itemIndex == len(self.itemList)):
            itemIndex = len(self.itemList) - 1
        
        self.item = self.itemList[itemIndex]
        self.noItems = self.maxItems
    
    def registerItems(self, myIP, myPort):
        daemon=Pyro4.Daemon(port = myPort, host=myIP)
        self.pURI = daemon.register(self)
        self.nameServer.register(self.peerID, self.pURI)
        print("Registered " + self.peerID + "on nameserver with URI:" + str(self.pURI))
        return daemon

    def addItemsFromSeller(self,sellerID,items):
        #TODO: Lock required
        for item,count in items:
            self.itemsInMarket[item].append([sellerID,count])
    
    def replenishStock(self):
        self.chooseItem()
        self.leaderID.addItemsFromSeller(self.peerID,[self.item, self.noItems])
    
    def commissionForItem(self,item,commission):
        self.money += commission
        self.noItems -= 1
        if(self.noItems == 0):
            threading.Thread(target = self.replenishStock).start()
    
    def buy(self, item, peerID):
        if(self.isLeader == False):
            print("Illegal buy recieved from {0}".format(peerID))
            return
        retValue = False
        try:
            sell_lock.acquire()
            flag = True
            while(flag):
                flag = False
                if(item not in self.itemsInMarket):
                    break
                seller = random.choice(self.itemsInMarket[item])
                seller.commissionForItem(item,10)
                retValue = True
        except:
            print("Exiting buy")
        finally:
            sell_lock.release()
        return retValue            

    def buyAnotherItem(self):
        self.chooseItem()
        print ("Planning to buy",self.item)
        self.requestID += 1
        self.boughtItemsTime[self.requestID] = timeit.default_timer()
        self.requestMap[(self.peerID,self.requestID)] = self.peerID
        #print (self.requestMap,"Request map begore buying")
        if(self.leaderURI != None):
            isSuccess = self.leaderID.buy(self.item, self.peerID)
            if(isSuccess):
                print("Bought {0}".format(self.item))
            else:
                print("Could not buy {0}".format(self.item))
        else:
            print("Leader not elected yet")
            
