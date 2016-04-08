# -*- coding: utf-8 -*-

import time
import Pyro4
import random
import threading
import timeit
import VectorClock
import copy

buy_lock = threading.Lock()#Lock used by buyer when it establishes a connection with the seller to buy the product
sell_lock = threading.Lock()#Lock used by seller to decrement he count of object when it is sold
request_map_lock  = threading.Lock()#Lock to update the request map
election_lock  =  threading.Lock()

class Peer:
    def __init__(self, peerType, peerID, maxID, num_neighbours, itemList, noItems, myIP, myPort):
        
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
        self.requestsList = []
        self.got_ok = 0
        self.leaderID = None
        self.leaderProxy = None
        
        #For synchronization        
        self.clock = VectorClock.VectorClock(self.maxID)
        
        #If all peers on the network, start election
        if(len(self.neighbours) + 1 == self.maxID):
            threading.Thread(target = self.startElection()).start()
        
    def connectToNeighbours(self):
        for pID, pURI in self.nameServer.list(prefix="gaul.market.").items():
            if(pID != self.peerID):
                self.neighbours[pID]  = Pyro4.Proxy(pURI)
        print(self.neighbours)
    
    def startElection(self):
        print("Starting Election")
        self.isLeaderElected = False
        self.isLeader = False
        self.got_ok = 0
        for pID,pURI in self.neighbours.items():
            id = int(pID.replace("gaul.market.",""))
            myid = int(self.peerID.replace("gaul.market.",""))
            print(id,myid)
            if(id>myid):
                print("Calling lookup", pID)
                threading.Thread(target = pURI.election_lookup, args=[self.peerID]).start()
        time.sleep(1)
        if(not(self.got_ok==1) and not(self.isLeaderElected) ):
            self.broadcastElectionResult(self.peerID) #I am the leader

    def ok(self):
        if(self.isLeaderElected==True):
            return
        self.got_ok=1

    def election_lookup( self, requestingPeerID):
        #reply OK
        print("Lookup called ", requestingPeerID,self.got_ok)
        self.isLeaderElected=False
        if(self.resigning):
            return
        if(len(self.neighbours) < self.maxID):
            self.connectToNeighbours()
            
        self.neighbours[requestingPeerID].ok()
        for pID,pURI in self.neighbours.items():
            id = int(pID.replace("gaul.market.",""))
            myid = int(self.peerID.replace("gaul.market.",""))
            if(id>myid):
                print("Calling lookup", pID)
                threading.Thread(target = pURI.election_lookup, args=[self.peerID]).start()
        time.sleep(1)
        print(self.got_ok)
        if(not(self.got_ok==1) and not(self.isLeaderElected) ):
            self.broadcastElectionResult(self.peerID)
    
    def broadcastElectionResult(self, leaderID):
        
        self.isLeaderElected = True
        self.got_ok=0
        if(self.peerID != leaderID):        
            print("Our new Leader is...", leaderID)
            self.leaderID = leaderID
            self.leaderProxy = self.nameServer.lookup(leaderID)
            self.isLeader = False
            self.leaderProxy = Pyro4.Proxy(self.leaderProxy)
            self.leaderProxy.addItemsFromSeller(self.peerID,{self.itemToSell:self.noItems})
        else:
            self.isLeader = True
            print("I am assigned as leader")
            for pID,pURI in self.neighbours.items():
                threading.Thread(target = pURI.broadcastElectionResult, args=[self.peerID]).start()

        
    def resign_leader(self):
        if(self.isLeader):
            print("I would like to resign")
            #update resigning
            self.resigning = True
            for pID,pURI in self.neighbours.items():
                print("Starting election called of ",pID)
                pURI.startElection()
                break
                #Stop buying anything I am resigning
                #In case he is resigning then dont take part in leader election
                # add a clause that
                #if resiginig then dont forward the request and dont reply anything...

#update the max node id
#if all replies heard great and reply to parent else exit
            
    """Pick randomly from self.items and reset noItems"""
    def chooseItemToSell(self):
        itemIndex = int(random.random() * len(self.itemList))
        if(itemIndex == len(self.itemList)):
            itemIndex = len(self.itemList) - 1
        
        self.itemToSell = self.itemList[itemIndex]
        self.noItems = self.maxItems
    
    def chooseItemToBuy(self):
        itemIndex = int(random.random() * len(self.itemList))
        if(itemIndex == len(self.itemList)):
            itemIndex = len(self.itemList) - 1
        return self.itemList[itemIndex]
    
    def registerItems(self, myIP, myPort):
        daemon=Pyro4.Daemon(port = myPort, host=myIP)
        self.pURI = daemon.register(self)
        self.nameServer.register(self.peerID, self.pURI)
        print("Registered " + self.peerID + "on nameserver with URI:" + str(self.pURI))
        return daemon

    def addItemsFromSeller(self,sellerID,itemsdict):
        #TODO: Lock required
        print("Registering items from {0}".format(sellerID))
        print (itemsdict)
        for item,count in itemsdict.items():
            if(item not in self.itemsInMarket):
                self.itemsInMarket[item]=[]
            self.itemsInMarket[item].append([sellerID,count])
        print (self.itemsInMarket[item])
    
    def replenishStock(self):
        self.chooseItemToSell()
        self.leaderProxy.addItemsFromSeller(self.peerID,{self.itemToSell: self.noItems})
    
    def commissionForItem(self,item,commission):
        print("asdasd")
        self.money += commission
        self.noItems -= 1
        print("Earnings: {0}, Stock: {1} {2}".format(self.money, self.itemToSell, self.noItems))
        if(self.noItems == 0):
            threading.Thread(target = self.replenishStock).start()

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
    
    def processList(self):
        requestsList = sorted(self.requestsList, key=self.cmp_to_key(lambda x,y: x.compare(y)))
        self.requestsList.clear()
        for request in requestsList:
            print("Processing {0}".format(request[0]))
            self.buy(request[2], request[1], request[0], request[3])
    
    def processBuyRequest(self, item, peerID, timeStamp, requestID):
      
        #print ("Items in market are")
        #print (self.itemsInMarket)
        #print (item)        
        
        buyerURI = self.nameServer.lookup(peerID)
        buyerURI = Pyro4.Proxy(buyerURI)
        isSold = False
            #try:
        print("Acquiring...")
        sell_lock.acquire()
        print("Acquired!")
        if(item in self.itemsInMarket):
            print(self.itemsInMarket[item])
            seller = random.choice(self.itemsInMarket[item])
            print(seller[0], seller[1])
            URI = self.nameServer.lookup(seller[0])
            seller = Pyro4.Proxy(URI)
            print(seller, item)
            seller.commissionForItem(item,10)
            self.money += 5
            print("Commission Earned: {0}".format(self.money))
            isSold = True
        #except:
        #    print("Exiting buy")
        #finally:
        sell_lock.release()
        print("Released")
        self.clock.addTime(int(self.peerID.replace("gaul.market.", "")))
        threading.Thread(target = self.multicastClock).start()
        buyerURI.sell(isSold, item, timeStamp, requestID)
        
    
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
        #isError = False
        if(isError == True):
            print("Time out of order {0} from {1}".format(timeStamp, peerID))
            self.requestsList.append([timeStamp, peerID, item, requestID])
        else:
            self.clock.update(timeStamp)
            self.processBuyRequest(item, peerID, timeStamp, requestID)
            self.processList()

    def sell(self, isSold, item, timestamp, requestID):
        self.clock.update(timestamp)
        print("{0} timestamped at {1}: {2}".format(item, timestamp, isSold))
        print("Time: {0}".format(timeit.default_timer() - self.boughtItemsTime[requestID]))
        del self.boughtItemsTime[requestID]
        
    def updateTimeStamp(self, peerID, timestamp):
        peerID = int(peerID.replace("gaul.market.",""))
        isError = self.clock.isError(peerID, timestamp)
        if(isError == True):
            print("Error in timestamp from {0}! {1} {2}".format(peerID, timestamp, self.clock.clock))
            print("{0}: {1}".format(int(self.peerID.replace("gaul.market.","")), timestamp))
            print("{0}: {1}".format(peerID, self.clock.clock))
        self.clock.update(timestamp)

    def multicastClock(self):
        for pID, pURI in self.nameServer.list(prefix="gaul.market.").items():
            if(pID != self.leaderID and pID != self.peerID):
                pURIhandle = Pyro4.Proxy(pURI)
                pURIhandle.updateTimeStamp(self.peerID, self.clock.clock)
    
    def buyAnotherItem(self):
        
        self.requestID = (self.requestID + 1) % 2000
        
        if(self.isLeader is True):
#            if(self.requestID == 10 and self.peerID == "gaul.market.4"):
#                self.resign_leader()
            return
        
        item = self.chooseItemToBuy()
        print ("Planning to buy {0} with request id {1}".format(item, self.requestID))
        self.boughtItemsTime[self.requestID] = timeit.default_timer()
        
        if(self.leaderProxy != None):
            self.clock.addTime(int(self.peerID.replace("gaul.market.", "")))
            if(self.peerID == "gaul.market.1"):
                localClock = copy.deepcopy(self.clock.clock)
                threading.Thread(target = self.multicastClock).start()
                time.sleep(3)
                print ("Buying {0} with request id {1} now, {2}".format(item, self.requestID, localClock))
                self.leaderProxy.buy(item, self.peerID, localClock, self.requestID)
            else:
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