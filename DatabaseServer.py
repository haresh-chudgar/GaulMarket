# -*- coding: utf-8 -*-
import Pyro4
import threading
db_lock = threading.Lock()

class DBServer:
    """
    Inititalizes the class.
    The DB is registered with the nameserver with the name "gaul.market.datastore"
    """
    def __init__(self, myIP, myPort):
        self.requests = {}
        self.itemDB = {}
        
        #Name server helps it connect to peers through names
        self.nameServer = Pyro4.locateNS()
        self.peerID = "gaul.market.datastore"
        daemon =  self.registerPeer(myIP, myPort)
        
        #A thread continues to listen incoming requests at the peer
        threading.Thread(target = daemon.requestLoop).start()
       
    """
    Trader calls addRequest to add the buy request from the buyer.
    Only one request is maintained per buyer since once a trader crashes, 
    all further requests would have failed and not be added and 
    all previous requests to this would have already been communicated to the
    buyer.
    """
    def addRequest(self, requestID, item, buyerID, traderID):
        self.requests[buyerID] = [requestID, item]
    
    """
    On one of the trader crashing, the new trader calls this function 
    when the buyer sends the unprocessed requests to the other trader.
    """
    def getRequests(self,buyerID):
        if(buyerID in self.requests):
            return self.requests[buyerID]
        return None

    """
    Returns list of sellers of a particular item
    """
    def getSellersFor(self, item):
        if(item in self.itemDB ):
            return self.itemDB[item]
        else:
            return None

    """
    Adds seller to the list of sellers of a particular item to the database
    """
    def addItemToDB(self, sellerID, item, count):
        db_lock.acquire()
        if(item not in self.itemDB):
            self.itemDB[item] = {}
        if(sellerID not in self.itemDB[item]):
            self.itemDB[item][sellerID] = 0
        for item in self.itemDB:
            if sellerID in  self.itemDB[item]:
                del self.itemDB[item][sellerID]
                break
        self.itemDB[item][sellerID] = count
        db_lock.release()

        
    """
    Merges the count of items sold through a particular trader for a particular item.
    data consists of list of (seller,count) key value pairs
    """
    def mergeItemDetails(self, item, data):
        print("Merging items", item, data)
        #Merging items pen {'pen': {'gaul.market.4': 2, 'gaul.market.1': 1, 'gaul.market.3': 1}, 'orange': {'gaul.market.2': 1}}
        print ("Item db is ",self.itemDB)
        if(item not in self.itemDB  ):
            #print ("returning none")
            return None
        #print ("entering for")
        db_lock.acquire()
        for (seller,count) in data.items():
            print ("Inside loop",seller,count)
            if seller in self.itemDB[item]:
                self.itemDB[item][seller] -= data[seller]
                print ("After sub",seller,self.itemDB[item][seller])
            if(self.itemDB[item][seller] <= 0):
                print ("deleting")
                del self.itemDB[item][seller]
                if(self.itemDB[item]=={}):
                    del self.itemDB[item]
        db_lock.release()
        print ("Returning from merge",self.itemDB)
        if(item in self.itemDB):
            return self.itemDB[item]
        else:
            return None
        
    """
    Registers the peer on the nameserver
    """
    def registerPeer(self, myIP, myPort):
        daemon=Pyro4.Daemon(port = myPort, host=myIP)
        self.pURI = daemon.register(self)
        self.nameServer.register(self.peerID, self.pURI)
        print("Registered " + self.peerID + "on nameserver with URI:" + str(self.pURI))
        return daemon
