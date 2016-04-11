——————————————————————————————————————————————————————————————————————————————————————————
				HOW TO RUN?
——————————————————————————————————————————————————————————————————————————————————————————
Change the server IP in config file to localhost if running on same machine or the IP of the machine where nameserver will be run

Run name server using following command : python3 -m Pyro4.naming -n ‘MY_IP’

With this we are all set to run the peers using the instruction which is following : 

python3 node.py <NODEID> <MYIP> <PORT NUMBER>

PeerID : 1 to N
Rest features are in config file

eg. python3 node.py 6 192.168.24.173 1116

All the peers need to run on different terminals for smooth running.

If you want to just copy the commands, run.sh has all the commands for 6 peers. You can just copy those commands to run them.


NOTE : Dependency Python3 and Pyro4
To install Pyro4 you need to run pip3 install Pyro4

——————————————————————————————————————————————————————————————————————————————————————————
				CONFIG FILE
——————————————————————————————————————————————————————————————————————————————————————————
This file contains the configuration settings which are common to all the peers. The details are following :

maxID = 6
items = apple,orange,pen
numItem = 4
serverIP =192.168.24.173

In order to change the values, you need to change the values present after the ‘=‘ sign only. maxID tells about the total number nodes which are to be deployed in the P2P network. 
numItem refers to the number of items the seller has in his inventory to cater to the buy requests from buyers. serverIP is the IP address of the server which has the nameserver running. This is helpful to register the peer to the name server.

——————————————————————————————————————————————————————————————————————————————————————————
				CODE FILEs
——————————————————————————————————————————————————————————————————————————————————————————

In the code, we have two files namely Peer.py, VectorClock.py and node.py
Peer.py is a general library which we have built to handle the P2P connections and send messages. It is mostly generic with some features specific to this problem. node.py is the python file which is used to create an object of Peer class, set the parameters and call the functions according to the type of the node.

The code is commented in order to explain the use of each function.

——————————————————————————————————————————————————————————————————————————————————————————
				OUTPUT FORMAT
——————————————————————————————————————————————————————————————————————————————————————————
The outputs are present in the folder named logs which contains different situations showing resignation and the time lag working of clocks.

The delayed message emulation is done by delaying a particular message. This is present in Peer_DelayedMessageEmulation.py