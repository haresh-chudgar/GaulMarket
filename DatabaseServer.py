# -*- coding: utf-8 -*-
import Pyro4
import threading

class DBServer:
    def __init__(self, myIP, myPort):
        self.requests = {}
        self.itemDB = {}
        
        #Name server helps it connect to peers through names
        self.nameServer = Pyro4.locateNS()
        self.peerID = "gaul.market.datastore"
        daemon =  self.registerItems(myIP, myPort)
        
        #A thread continues to listen incoming requests at the peer
        threading.Thread(target = daemon.requestLoop).start()
        
    def addRequest(self, requestID, item, buyerID, traderID):
        if(traderID not in self.requests):
            self.requests[traderID] = {}
        self.requests[traderID][buyerID] = [requestID, item]
    
    def getSellersFor(self, item):
        if(item in self.itemDB):
            return self.itemDB[item]

    def addItemToDB(self, sellerID, item, count):
        if(item not in self.itemDB):
            self.itemDB[item] = {}
        if(sellerID not in self.itemDB[item]):
            self.itemDB[item][sellerID] = 0
        self.itemDB[item][sellerID] = self.itemDB[item][sellerID] + count
    
    def updateDataFor(self, item, sellerID, deduction):
        #TODO: check for consistency?
        self.itemDB[item][sellerID] = self.itemDB[item][sellerID] - deduction
        
    def registerItems(self, myIP, myPort):
        daemon=Pyro4.Daemon(port = myPort, host=myIP)
        self.pURI = daemon.register(self)
        self.nameServer.register(self.peerID, self.pURI)
        print("Registered " + self.peerID + "on nameserver with URI:" + str(self.pURI))
        return daemon
