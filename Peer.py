# -*- coding: utf-8 -*-

import time
import Pyro4
import random
import threading
import timeit
import VectorClock
import pickle

buy_lock = threading.Lock()#Lock used by buyer when it establishes a connection with the seller to buy the product
sell_lock = threading.Lock()#Lock used by seller to decrement he count of object when it is sold
request_map_lock  = threading.Lock()#Lock to update the request map
election_lock  =  threading.Lock()

class Peer:
    def __init__(self, peerType, peerID, maxID, num_neighbours, itemList, noItems, myIP, myPort):
        
        self.traderFilePath = "TraderAccount.pkl"
        
        #Name server helps it connect to peers through names
        self.nameServer = Pyro4.locateNS()
        self.domain = "gaul.market."
        self.peerID = self.domain+peerID
        daemon =  self.registerPeer(myIP, myPort)
        #A thread continues to listen incoming requests at the peer
        threading.Thread(target = daemon.requestLoop).start()
        
        #If the peer ID = maxPeer id then calculate the neighbours and add the edges in a different function
        self.num_neighbours = num_neighbours
        self.neighbours = {}
        
        self.maxID = int(maxID)
        self.connectToNeighbours()

        #Config for selling
        self.itemList = itemList
        self.noItems = noItems
        self.maxItems = noItems
        self.itemToSell = None
        self.chooseItemToSell()
        
        self.money = 0
        self.requestID = 0
        self.boughtItemsTime = {}
        self.averageTime = 0
        
        self.isLeaderElected = False
        
        #Variables for trader        
        self.resigning = False
        self.isLeader = False
        self.itemsInMarket = {}
        self.itemsSold = {}
        self.requestsList = []
        self.got_ok = 0
        self.leaderID = None
        self.leaderProxy = None
        
        #For synchronization        
        self.clock = VectorClock.VectorClock(self.maxID)

        self.dbProxy = None        
        
        #If all peers on the network, start election
        if(len(self.neighbours) + 1 == self.maxID):
            threading.Thread(target = self.startElection()).start()

    #Add the set of neighbors into the neighbor list
    def connectToNeighbours(self):
        for pID, pURI in self.nameServer.list(prefix="gaul.market.").items():
            if(pID != self.peerID and pID != "gaul.market.datastore"):
                self.neighbours[pID]  = Pyro4.Proxy(pURI)
        print(self.neighbours)

    #start the election
    def startElection(self):
        print("Starting Election")
        self.isLeaderElected = False
        self.isLeader = False
        self.got_ok = 0
        #Iterate over all the neighbors
        for pID,pURI in self.neighbours.items():
            id = int(pID.replace("gaul.market.",""))
            myid = int(self.peerID.replace("gaul.market.",""))
            print(id,myid)
            #Call lookup if the id of neighbor is > my id
            if(id>myid):
                print("Calling lookup", pID)
                threading.Thread(target = pURI.election_lookup, args=[self.peerID]).start()
        time.sleep(1)
        #If no one replied with an ok message, I am the leader
        if(not(self.got_ok==1) and not(self.isLeaderElected) ):
            #self.isLeaderElected=True
            leaders = [self.peerID]
            #Iterate over smaller id nodes to ask for 2nd trader
            id=int(self.peerID.replace("gaul.market.","")) - 1
            while id > 0:
                pURI = self.neighbours[self.domain+str(id)]
                ret = pURI.become_trader(self.peerID)
                if(ret==True):
                    leaders.append(self.domain+str(id))
                    break
                id-=1
            self.dbProxy = self.nameServer.lookup('gaul.market.datastore')
            self.dbProxy = Pyro4.Proxy(self.dbProxy)
            print("I am the new leader")
            threading.Thread(target = self.start_beat, args=[leaders[1]]).start()
            #Broadcast the election result among all the peers
            self.broadcastElectionResult(leaders) #I am the leader

    #ok message sent to the peer who caled lookup
    def ok(self):
        if(self.isLeaderElected==True):
            return
        self.got_ok=1

    #Lookup called for election
    def election_lookup( self, requestingPeerID):
        #reply OK
        print("Lookup called ", requestingPeerID,self.got_ok)
        self.isLeaderElected=False
        if(self.resigning):
            return
        election_lock.acquire()
        if(len(self.neighbours) < self.maxID):
            self.connectToNeighbours()
        #Call lookup on ids which are greater than my id
        self.neighbours[requestingPeerID].ok()
        for pID,pURI in self.neighbours.items():
            id = int(pID.replace("gaul.market.",""))
            myid = int(self.peerID.replace("gaul.market.",""))
            if(id>myid):
                print("Calling lookup", pID)
                threading.Thread(target = pURI.election_lookup, args=[self.peerID]).start()
        time.sleep(5)
        election_lock.release()
        print(self.got_ok)
        #If no one replied with ok message then I am the leader
        if(not(self.got_ok==1) and not(self.isLeaderElected) ):
            print("I am the new leader")            
            self.isLeaderElected=True
            leaders = [self.peerID]
            id=int(self.peerID.replace("gaul.market.","")) - 1
            #Query the nodes with id smaller than mine to become the second trader
            while id > 0:
                pURI = self.neighbours[self.domain+str(id)]
                ret = pURI.become_trader(self.peerID)
                if(ret==True):
                    leaders.append(self.domain+str(id))
                    break
                id-=1
            self.dbProxy = self.nameServer.lookup('gaul.market.datastore')
            self.dbProxy = Pyro4.Proxy(self.dbProxy)
            threading.Thread(target = self.start_beat, args=[leaders[1]]).start()
            self.broadcastElectionResult(leaders) #I am the leader
    
    #Reply back agreeing to be become one of the traders
    def become_trader(self, leader_ID):
        print("I am the new leader")
        self.isLeader = True
        self.dbProxy = self.nameServer.lookup('gaul.market.datastore')
        self.dbProxy = Pyro4.Proxy(self.dbProxy)
        #Start the heart beat to track the other leader
        threading.Thread(target = self.start_beat, args=[leader_ID]).start()
        return True
    #This function just sends beat to confirm that I am alive
    def send_beat(self):
        return True
    #A thread which handles the heart beat process of sending the beat and receiving it
    def start_beat(self,leaderID):
        leaderProxy = self.nameServer.lookup(leaderID)
        leaderProxy = Pyro4.Proxy(leaderProxy)
        while True:
            try:
                leaderProxy.send_beat()
                time.sleep(5)
            except:
                print ("I am the only leader left ")
                
                break
        #If no reply or exception then the other leader has died and I need to broadcast that I am the only leader left
        for pID,pURI in self.neighbours.items():
            if(not (self.peerID == pID) and not(leaderID == pID) ):
                threading.Thread(target = pURI.update_leader, args=[self.peerID]).start()
        self.itemsInMarket={}
        self.itemsSold={}
            
    
    #Broadcast message which informs the peers that I am the only leader in the market now.
    def update_leader(self, leaderID):
        print("Our new leader is ",leaderID)
        self.leaderID  = leaderID
        self.leaderProxy = self.nameServer.lookup(self.leaderID)
        self.leaderProxy = Pyro4.Proxy(self.leaderProxy)
        self.leaderProxy.addItemsFromSeller(self.peerID,{self.itemToSell:self.noItems})
        for requestID in self.boughtItemsTime:
            bought  = self.leaderProxy.process_old_request(self.peerID, requestID)
            print("Request processed by new trader")
        self.boughtItemsTime = {}

    #When the new leader gets assigned, the peers ask him to process his old requests by resending the requests
    def process_old_request(self, requestingPeerID, requestID):
        print ("Processing old requests",requestingPeerID, requestID)
        requests = self.dbProxy.getRequests(requestingPeerID)
        print ("requests from db ",requests)
        if(requestID in requests):
            return True
        return False
    #Broadcasts the results of election
    def broadcastElectionResult(self, leaders):
        if(self.isLeaderElected ):
            return
        self.isLeaderElected = True
        self.got_ok=0
        self.clock.reset()
        self.leaderID = random.choice(leaders)

        if(self.peerID not in leaders):
            
            print("Our new Leaders are...",leaders)
            self.leaderProxy = self.nameServer.lookup(self.leaderID)
            self.isLeader = False
            self.leaderProxy = Pyro4.Proxy(self.leaderProxy)
            self.leaderProxy.addItemsFromSeller(self.peerID,{self.itemToSell:self.noItems})
        
        else:
            self.isLeader = True
            print("I am assigned as leader")
            
            for pID,pURI in self.neighbours.items():
                if(pID not in leaders):
                    threading.Thread(target = pURI.broadcastElectionResult, args=[leaders]).start()

#update the max node id
#if all replies heard great and reply to parent else exit
            
    """Pick randomly from self.items and reset noItems"""
    def chooseItemToSell(self):
        itemIndex = int(random.random() * len(self.itemList))
        if(itemIndex == len(self.itemList)):
            itemIndex = len(self.itemList) - 1
        
        self.itemToSell = self.itemList[itemIndex]
        self.noItems = self.maxItems
    # Choose the item to buy randomly
    def chooseItemToBuy(self):
        itemIndex = int(random.random() * len(self.itemList))
        if(itemIndex == len(self.itemList)):
            itemIndex = len(self.itemList) - 1
        return self.itemList[itemIndex]
    #Register the peer to the nameserver
    def registerPeer(self, myIP, myPort):
        daemon=Pyro4.Daemon(port = myPort, host=myIP)
        self.pURI = daemon.register(self)
        self.nameServer.register(self.peerID, self.pURI)
        print("Registered " + self.peerID + "on nameserver with URI:" + str(self.pURI))
        return daemon

    def getItemsToSell(self):
        print([self.itemToSell, self.noItems])
        return [self.itemToSell, self.noItems]
    #Add the items to database
    def addItemsFromSeller(self,sellerID,itemsdict):
        print("Registering items from {0}".format(sellerID))
        print (itemsdict)
        for item,count in itemsdict.items():
            self.dbProxy.addItemToDB(sellerID, item, count)
    
    def replenishStock(self):
        self.chooseItemToSell()
        self.leaderProxy.addItemsFromSeller(self.peerID,{self.itemToSell: self.noItems})
    #Earn commission for an item
    def commissionForItem(self,item,commission):
        if(self.itemToSell == item and self.noItems > 0):
            self.money += commission
            self.noItems -= 1
            print("Earnings: {0}, Stock: {1} {2}".format(self.money, self.itemToSell, self.noItems))
            if(self.noItems == 0):
                threading.Thread(target = self.replenishStock).start()
            return True
        else:
            return False


    def cmp_to_key(self, mycmp):
        class K(object):
            def __init__(self, obj, *args):
                self.obj = obj
            def __lt__(self, other):
                return mycmp(self.obj, other.obj) < 0
            def __gt__(self, other):
                return mycmp(self.obj, other.obj) > 0
            def __eq__(self, other):
                return mycmp(self.obj, other.obj) == 0
            def __le__(self, other):
                return mycmp(self.obj, other.obj) <= 0
            def __ge__(self, other):
                return mycmp(self.obj, other.obj) >= 0
            def __ne__(self, other):
                return mycmp(self.obj, other.obj) != 0
        return K
    
    #Process the buy request at the trader
    def processBuyRequest(self, item, peerID, timeStamp, requestID):
      
        buyerURI = self.nameServer.lookup(peerID)
        buyerURI = Pyro4.Proxy(buyerURI)
        isSold = False
        sell_lock.acquire()

        if(item not in self.itemsInMarket):
            print ("Item not in cache")
            sellers = self.dbProxy.getSellersFor(item)
            print ("Got the sellers from db",sellers,"for item ", item)
            if(sellers is not None):
                self.itemsInMarket[item] = sellers
                self.itemsSold[item] = {}
            
        if(item in self.itemsInMarket):
            print("Item is in cache")
            print(self.itemsInMarket[item])
            seller = random.choice(list(self.itemsInMarket[item]))
            print(seller, self.itemsInMarket[item][seller])
            URI = self.nameServer.lookup(seller)
            sellerProxy = Pyro4.Proxy(URI)
            isSaleSuccess = sellerProxy.commissionForItem(item,10)
            if(isSaleSuccess):
                self.money += 5
                print("Commission Earned: {0}".format(self.money))
                isSold = True
                self.dbProxy.addRequest(requestID, item, peerID, self.peerID)
            else:
                print("Seller rejected the sell request")
                self.itemsInMarket[item] = self.dbProxy.mergeItemDetails(item, self.itemsSold[item])
                self.itemsSold[item] = {}
                if(self.itemsInMarket[item] is None):
                    del self.itemsInMarket[item]
                    del self.itemsSold[item]
                else:
                    seller = random.choice(list(self.itemsInMarket[item]))
                    URI = self.nameServer.lookup(seller)
                    sellerProxy = Pyro4.Proxy(URI)
                    isSaleSuccess = sellerProxy.commissionForItem(item,10)
                    if(isSaleSuccess):
                        print("Found new seller")
                        self.money += 5
                        print("Commission Earned: {0}".format(self.money))
                        isSold = True
                        self.dbProxy.addRequest(requestID, item, peerID, self.peerID)


        sell_lock.release()
        self.clock.addTime(int(self.peerID.replace("gaul.market.", "")))
        threading.Thread(target = self.multicastClock).start()
        if(isSold is True):
            if(item not in self.itemsSold):
                self.itemsSold[item] = {}
            if(seller not in self.itemsSold[item]):
                self.itemsSold[item][seller] = 0
            self.itemsSold[item][seller] += 1
            self.itemsInMarket[item][seller] -= 1
            print(self.itemsSold[item][seller],self.itemsSold[item])
            print(self.itemsInMarket[item][seller], self.itemsInMarket[item])
            if(self.itemsSold[item][seller] == self.itemsInMarket[item][seller]):
                print ("Calline merge in 345")
                self.itemsInMarket[item] = self.dbProxy.mergeItemDetails(item, self.itemsSold[item])
                print ("returning from merge in 347")
                self.itemsSold[item] = {}
                if(self.itemsInMarket[item] is None):
                    del self.itemsInMarket[item]
                    del self.itemsSold[item]

        else:
            print("Could not sell",item)
        print("Going to buyer")

        buyerURI.sell(isSold, item, timeStamp, requestID)
        requestsList = sorted(self.requestsList, key=self.cmp_to_key(lambda x,y: x.compare(y)))
        self.requestsList.clear()
        for request in requestsList:
            print("Processing {0}".format(request[0]))
            self.buy(request[2], request[1], request[0], request[3])
        
    def buy(self, item, peerID, timeStamp, requestID):
        print("Buy request from {0} for {1} with time {2}".format(peerID, item, timeStamp))
        print("My timestamp: {0}".format(self.clock.clock))
        if(self.isLeader == False):
            print("Illegal buy recieved from {0}".format(peerID))
            return
        if(self.resigning == True):
            print("I resigned. Request from {0}".format(peerID))
            return

        isError = self.clock.isError(int(peerID.replace("gaul.market.", "")), timeStamp)
        isError = False
        if(isError == True):
            print("Time out of order {0} from {1}".format(timeStamp, peerID))
            self.requestsList.append([timeStamp, peerID, item, requestID])
        else:
            self.clock.update(timeStamp)
            self.processBuyRequest(item, peerID, timeStamp, requestID)

    def sell(self, isSold, item, timestamp, requestID):
        self.clock.update(timestamp)
        print("{0} timestamped at {1}: {2}".format(item, timestamp, isSold))
        print("Time: {0}".format(timeit.default_timer() - self.boughtItemsTime[requestID]))
        del self.boughtItemsTime[requestID]
        
    def updateTimeStamp(self, peerID, timestamp):
        peerID = int(peerID.replace("gaul.market.",""))
        isError = self.clock.isError(peerID, timestamp)
        '''
        if(isError == True):
            print("Error in timestamp from {0}! {1} {2}".format(peerID, timestamp, self.clock.clock))
            print("{0}: {1}".format(int(self.peerID.replace("gaul.market.","")), timestamp))
            print("{0}: {1}".format(peerID, self.clock.clock))
        '''
        self.clock.update(timestamp)

    def multicastClock(self):
        return
        for pID, pURI in self.nameServer.list(prefix="gaul.market.").items():
            if(pID != self.leaderID and pID != self.peerID and pID != "gaul.market.datastore"):
                pURIhandle = Pyro4.Proxy(pURI)
                pURIhandle.updateTimeStamp(self.peerID, self.clock.clock)
    
    def buyAnotherItem(self):
        
        self.requestID = (self.requestID + 1) % 2000
        
        if(self.isLeader is True):
            if(self.requestID == 10 and self.peerID == "gaul.market.4"):
                self.resign_leader()
            return
        
        item = self.chooseItemToBuy()
        print ("Planning to buy {0} with request id {1}".format(item, self.requestID))
        self.boughtItemsTime[self.requestID] = timeit.default_timer()
        
        if(self.leaderProxy != None):
            self.clock.addTime(int(self.peerID.replace("gaul.market.", "")))
            threading.Thread(target = self.multicastClock).start()
            self.leaderProxy.buy(item, self.peerID, self.clock.clock, self.requestID)
        else:
            print("Leader not elected yet")
         
'''

    def addNeighbour(self, pID, pURI):
        print("Neighbours is being added with node id = ",pID)
        self.neighbours[pID]  = Pyro4.Proxy(pURI)

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
        neigh={1: [ 2, 3], 2: [1, 4], 3: [ 1, 4], 4: [2,3]}
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
        if(self.resigning):
            myid = "gaul.market.0"
            self.neighbours[requestingPeerID].election_reply(myid, self.peerID)
            return
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
                election_lock.release()
                self.neighbours[requestingPeerID].election_reply(self.peerID, self.peerID)
                return
        election_lock.release()

    def election_reply(self, requestingPeerID, neighborID):
        #If I started election then this function should return by noting down the leader and call broadcast leader
        #broadcast leader will update the requestmap of all reply and election types...
       
        print("Election Reply", requestingPeerID)
        reqID = int(requestingPeerID.replace("gaul.market.", ""));
        maxID = int(self.max.replace("gaul.market.", ""));
        election_lock.acquire()        
        if(maxID < reqID):#extract peer id number here
            self.max = requestingPeerID
        election_lock.release()
        self.requestMap[(neighborID,"reply")] = 1
        all_set = False
        for pID,pURI in self.neighbours.items():
            print(self.requestMap)
            #print(self.requestMap[(requestingPeerID,"election")])
            print(requestingPeerID)
            if((pID,"election") in self.requestMap):
                if(not ( (pID,"reply") in self.requestMap)):
                    all_set=False
                    break
            all_set=True
        print(" Replydone", requestingPeerID)

        if(all_set):
            print(self.requestMap)
            print(self.neighbours.items())
            if(self.parent == self.peerID):
                print("Leader is " + self.max)
                threading.Thread(target = self.broadcastElectionResult, args=[self.peerID, self.max]).start()
            else:
                for pID,pURI in self.neighbours.items():
                    if(pID == self.parent):
                        threading.Thread(target = pURI.election_reply, args=[self.max, self.peerID]).start()
            
    '''        