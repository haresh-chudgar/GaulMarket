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

If you want to just copy the commands, run.sh has all the commands for 6 peers where 3 will be buyers and 3 sellers. You can just copy those commands to run them.

NOTE : Dependency Python3 and Pyro4
To install Pyro4 you need to run pip3 install Pyro4

——————————————————————————————————————————————————————————————————————————————————————————
				CONFIG FILE
——————————————————————————————————————————————————————————————————————————————————————————
This file contains the configuration settings which are common to all the peers. The details are following :

maxID = 6
num_neighbour = 3
items = apple,orange,pen
numItem = 4
serverIP =192.168.24.173

In order to change the values, you need to change the values present after the ‘=‘ sign only. maxID tells about the total number nodes which are to be deployed in the P2P network. num_neighbour refers to the number of neighbors each node in the overlay network will have. hopCount refers to the number of hops that the message travels in order to search for seller. If the seller is farther than that then the message gets discarded.
items is the list of items that the seller has to sell.
numItem refers to the number of items the seller has in his inventory to cater to the buy requests from buyers. serverIP is the IP address of the server which has the nameserver running. This is helpful to register the peer to the name server.

——————————————————————————————————————————————————————————————————————————————————————————
				CODE FILEs
——————————————————————————————————————————————————————————————————————————————————————————

In the code, we have two files namely Peer.py and node.py
Peer.py is a general library which we have built to handle the P2P connections and send messages. It is mostly generic with some features specific to this problem. node.py is the python file which is used to create an object of Peer class, set the parameters and call the functions according to the type of the node.

The code is commented in order to explain the use of each function.

——————————————————————————————————————————————————————————————————————————————————————————
				OUTPUT FORMAT
——————————————————————————————————————————————————————————————————————————————————————————

BUYER OUTPUT :


Start time to buy this item is  2000.584936809  Item is 1
Planning to buy orange
Calling lookup for gaul.market.3 4 orange to neighbor gaul.market.6
Calling lookup for gaul.market.3 4 orange to neighbor gaul.market.2
Calling lookup for gaul.market.3 4 orange to neighbor gaul.market.4
 Function reply from gaul.market.3  Origin is  gaul.market.3  Request id is  4
 Function reply from gaul.market.3  Origin is  gaul.market.3  Request id is  4
Item name:  orange has been bought ('gaul.market.3', 4) seller is  gaul.market.6
Total Time for  4 is 0.005854158999909487


In the above output, the client is going to buy orange. It calls lookup for neighbors with ids gaul.market.6, gaul.market.2, gaul.market.4
It gets reply and it has bought the item from gaul.market.6
Then it prints the end time and average lag time to get the request processed.

SELLER OUTPUT : 

Function lookup of gaul.market.6  Origin is  gaul.market.1  request id is  6  hop count 0
Reply from seller for request originated at  gaul.market.1  and id is  6
Function lookup of gaul.market.6  Origin is  gaul.market.1  request id is  6  hop count 1
Reply from seller for request originated at  gaul.market.1  and id is  6
Function lookup of gaul.market.6  Origin is  gaul.market.2  request id is  5  hop count 3
Function lookup of gaul.market.6  Origin is  gaul.market.2  request id is  5  hop count 2
Function lookup of gaul.market.6  Origin is  gaul.market.3  request id is  4  hop count 3
Reply from seller for request originated at  gaul.market.3  and id is  4
SOLD  item = orange to peer = gaul.market.3 Items left =  2


Each output tells about the lookup calls made to the seller and the reply it gives. In the end when connection is established directly with the client, it sells the object and prints the number of items left with it.

