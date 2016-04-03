# -*- coding: utf-8 -*-

import Pyro4
import random
import threading
import timeit

buy_lock = threading.Lock()#Lock used by buyer when it establishes a connection with the seller to buy the product
sell_lock = threading.Lock()#Lock used by seller to decrement he count of object when it is sold
request_map_lock  = threading.Lock()#Lock to update the request map

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
        if(self.peerID == domain+str(self.maxID)):
            #create a graph and add the neighbors
            self.create_graph()
        #else:
        #chill
        
        
        self.peerType = peerType
        self.hopCount = hopCount
        self.currentRequestID = 0
        self.requestMap = {}
        self.itemList = itemList
        self.noItems = noItems
        self.maxItems = noItems
        self.item = itemList[1]
        self.chooseItem()
        self.requestID = 0
        self.boughtItemsTime = {}
        self.averageTime = 0
        self.itemsBought = 0
        self.maxHops = maxHops
        self.parent = -1
        self.max = self.peerID
        self.isLeader = False
    
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
        self.parent = self.peerID
        for pID,pURI in self.neighbours.items():
            print ("Calling lookup for "+self.peerID+" "+str(self.requestID)+" "+self.item+" to neighbor "+pID)
            if(pURI.check_parent()):
                threading.Thread(target = pURI.election_lookup, args=[self.peerID]).start()
            #Check if parent is -1, take lock, set parent, release lock and call lookup
        #pURI.lookup(self.peerID, self.peerID, self.requestID, self.item, self.maxHops)
        pass
    
    def election_lookup( self, requestingPeerID):
        if(self.parent==-1):
            self.parent = requestingPeerID
            forwarded = False
            for pID,pURI in self.neighbours.items():
                if(pID != requestingPeerID):
                    if(pURI.check_parent()):
                        self.requestMap[(pID,"election")]= 1
                        threading.Thread(target = pURI.election_lookup, args=[self.peerID]).start()
                        forwarded = True
            if(forwarded ==False):
                self.neighbours[requestingPeerID].reply(self.peerID)

    def reply(self, requestingPeerID):
        #If I started election then this function should return by noting down the leader and call broadcast leader
        #broadcast leader will update the requestmap of all reply and election types...
        
        if(self.peerID < requestingPeerID):#extract peer id number here
            self.max = requestingPeerID
        self.requestMap[(requestingPeerID,"reply")] = 1
        all_set = False
        for pID,pURI in self.neighbours.items():
            if(self.requestMap[(requestingPeerID,"election")]==1):
                if(not (self.requestMap[(requestingPeerID,"reply")] ==1)):
                    all_set=False
                    break
            all_set=True
        if(all_set):
            for pID,pURI in self.neighbours.items():
                if(pID != self.parent):
                    threading.Thread(target = pURI.election_lookup, args=[self.max]).start()

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
    
    """this procedure should search the network; all matching sellers
    respond to this message with their IDs. The hopcount is decremented at 
    each hop and the message is discarded when it reaches 0"""
    def lookup (self,requestingPeerID, originID, requestID, item, hopCount):
        print("Function lookup of "+self.peerID," Origin is ",originID," request id is ",requestID," hop count",hopCount)

        try:
            if(self.peerType == "SELLER" and self.item == item and self.noItems > 0):
                #print (self.neighbours)
                #print(requestingPeerID," Reuqesting id")
                print("Reply from seller for request originated at ",originID," and id is ",requestID)
                #threading.Thread(target = self.neighbours[requestingPeerID].reply, args=[self.peerID, originID, requestID]).start()
                self.neighbours[requestingPeerID].reply(self.peerID, originID, requestID)
            elif hopCount > 0:
                hopCount = hopCount - 1
            
#                request_map_lock.acquire()
#                self.requestMap[(originID, requestID)] = requestingPeerID
#                request_map_lock.release()
            
                for pID,pURI in self.neighbours.items():
                    if(pID != requestingPeerID and pID!=originID):
                        if(not( pURI.contains_key(originID,requestID))):
                            threading.Thread(target = pURI.lookup, args=[self.peerID, originID, requestID, item, hopCount]).start()
        except:
            print("Exiting lookup")

    def contains_key(self, originID,requestID):
        return (originID,requestID) in self.requestMap.keys()
    
    """this is a reply message with the peerID of the seller"""
    def reply(self, sellerID, originID, requestID):
        print(" Function reply from "+self.peerID," Origin is ",originID," Reuqest id is ",requestID)
        try:
            if(originID == self.peerID):
                #TODO:Lock required here
                buy_lock.acquire()
                #print (self.requestMap)

                if((originID,requestID) in self.requestMap):
                    sellerURI = self.nameServer.lookup(sellerID)
                    seller = Pyro4.Proxy(sellerURI)
                    if(seller.buy(self.item, self.peerID)):
                        print ("Item name: ", self.item, "has been bought",(originID,requestID),"seller is ",sellerID)
                        del self.requestMap[(originID,requestID)]
                        self.boughtItemsTime[self.requestID] = timeit.default_timer() - self.boughtItemsTime[self.requestID]
                        print ("Total Time for ", self.requestID, "is", self.boughtItemsTime[self.requestID])
                        self.itemsBought += 1
                        self.averageTime = (self.averageTime * (self.itemsBought - 1) + self.boughtItemsTime[self.requestID]) / self.itemsBought
                        print ("Average Time:", self.averageTime, " ",self.itemsBought)
                        #end = timeit.default_timer()
                        #print ("END TIME IS ",end )
                buy_lock.release()
            else:
                #print ("It is here")
                requestingPeerID = self.requestMap[(originID,requestID)]
                #print ("Done this too It is here",requestingPeerID)
                #threading.Thread(target = self.neighbours[requestingPeerID].reply, args=[sellerID, originID, requestID]).start()
                self.neighbours[requestingPeerID].reply(sellerID, originID, requestID)
        except:
            print("Exiting reply")

    """ if multiple sellers respond, the buyer picks one at random, and 
    contacts it directly with the buy message. A buy causes the seller to 
    decrement the number of items in stock."""
    def buy(self, item, peerID):
        #TODO:locking required
        try:
            sell_lock.acquire()
            if(self.item == item and self.noItems > 0):
                self.noItems -= 1
                if(self.noItems == 0):
                    self.chooseItem()
                print("SOLD  item = "+item+" to peer = "+peerID, "Items left = ",self.noItems)
                sell_lock.release()
                return True
            else:
                sell_lock.release()
                return False
        except:
            print("Exiting buy")

    def buyAnotherItem(self):
        self.chooseItem()
        print ("Planning to buy",self.item)
        self.requestID += 1
        self.boughtItemsTime[self.requestID] = timeit.default_timer()
        self.requestMap[(self.peerID,self.requestID)] = self.peerID
        #print (self.requestMap,"Request map begore buying")
        for pID,pURI in self.neighbours.items():
            print ("Calling lookup for "+self.peerID+" "+str(self.requestID)+" "+self.item+" to neighbor "+pID)
            threading.Thread(target = pURI.lookup, args=[self.peerID, self.peerID, self.requestID, self.item, self.maxHops]).start()
                #pURI.lookup(self.peerID, self.peerID, self.requestID, self.item, self.maxHops)
        pass
    

