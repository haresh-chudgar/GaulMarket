# -*- coding: utf-8 -*-

class VectorClock:
    def __init__(self, N):
        self.N = N+1
        self.clock = []
        for i in range(N):
            self.clock.append(0)
        self.clock.append(0)
    
    def reset(self):
        for i in range(self.N):
            self.clock[i] = 0
            
    def compare(self, time):
        lesser = 0
        greater = 0
        for i in range(self.N):
            if(self.clock[i] < time[i]):
                lesser += 1
            elif(self.clock[i] > time[i]):
                greater += 1
        if(lesser > 0 and greater > 0):
            return 0
        elif(lesser > 0):
            return -1
        elif(greater > 0):
            return 1
        else:
            return 0
    
    def addTime(self, p):
        self.clock[p] += 1

    def update(self, time):
        for i in range(self.N):
            if(self.clock[i] < time[i]):
                self.clock[i] = time[i]
                
    def isError(self, p, time):
        if(time[p] - self.clock[p] != 1):
            return True
        #TODO:
        for i in range(self.N):
            if(i != p and self.clock[i] < time[i]):
                #print("Returning true", time, self.clock, i, p)
                return True
        return False
            
    def diff(self, time):
        retVal = 0
        for i in range(self.N):
            retVal += abs(self.clock[i] - time[i])
        return retVal