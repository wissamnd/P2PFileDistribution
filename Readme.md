# A high-level description of the application
The tracker has three tasks to run in parallel to serve the peers in the network:

## Listen for incoming file requests from the peers

If the tracker has the requested file it will send it using a TCP connection to ensure reliable delivery of the file, but in case the file is not found the tracker sends the manifest file to the peer also over a TCP connection.

## Distribute File chunk in order to save space

If the tracker finds that the 3 or more users are in the connection it sends chunks of its files to the volunteering peering through a TCP connection to save space. When the file is distributed its chunks are saved into the manifest file for future reference. (Two copies of each chunk are stored at volunteering peers)

## Keep track of peers in the connection

If the tracker stops receiving UDP packets for 10s indicating that it is still in the connection the tracker disconnects the peer. The tracker will then request the lost files chunks back from the peers having the other copies and then store them at another volunteer.

## Similarly, peers have three tasks that runs in parallel:

## Listen for incoming request from the tracker and peers
 listens for three events:
receiving a file chunk from the tracker to be stored
receiving a request to send the file chunk back to the tracker
receiving a request to send the file chunk back to a peer

## Provide the user with a prompt to request a file from the tracker
Present the user with a prompt to request a file from the tracker. If the tracker sends back a manifest file it checks whether this manifest file contains the required file. In case the file is not found in the manifest it determines which peers are responsible for storing the chunks and requests the chunks from them. Finally, the files are combined and the md5 hash is checked to ensure that the file is successfully received.

## Send UDP packets to the tracker indicating that it is still available 
Ping the tracker with UDP messages (every 5s) indicating that the peer is still in the connection.

# Technology stack
The application was built using python in addition to these python libraries: socket, time, random, tqdm for displaying the file transfer progress, os for getting file metadata, threading for running services in parallel, hashlib to get the md5 hash of a file, pickle for storing the manifest object file and retrieving it back when needed, errno, SocketError for error reporting, math, and random.
