# -*- coding: utf-8 -*-

class VectorClock:
    def __init__(self, N):
        self.N = N
        self.clock = []
    
    def compare(self, time):
        for i in range(self.N):
            if(self.clock[i] < time.clock[i]):
                return -1
            elif(self.clock[i] == time.clock[i]):
                return 0
            else:
                return 1
    
    def addTime(self, p):
        self.clock[p] += 1
    
    def diff(self, time):
        retVal = 0
        for i in range(self.N):
            retVal += (self.clock[i] - time.clock[i])
        return retVal