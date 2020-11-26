from socket import *
from socket import error as SocketError
import os
import math
import hashlib
import pickle
import time
import threading 
import random
import logging
import errno
import tqdm
class fileDistributed:
    """
    A class used to represent a file distributed by the Tracker

    Attributes
    ----------
    name : str
          the name of the file
    numberOfChunks : int
          the number of chunks in a file
    md5Hash : str
        the md5 hash of the file
    chunks : [chunk]
        file chunks
    """
    def __init__(self, name, number_of_chunks , md5Hash, chunks):
        self.name = name
        self.number_of_chunks = number_of_chunks
        self.md5Hash = md5Hash
        self.chunks = chunks
    def __str__(self):
        s = "Filename: {0}\tNumber of Chunks: {1} md5: {2} chunks:".format(self.name,self.number_of_chunks,self.md5Hash)
        if(len(self.chunks)> 0):
          s+= " ["
          for chunk in self.chunks:
               s+= chunk.toString()
               s+= " ,"
          s = s[0:len(s)-2]
          s+= "]"
        else:
             s+= " Empty"
        return s
    def set_chunks(self, chunks): 
        self.chunks = chunks 

class chunk:
    """
    A class used to represent a distributed file chunk

    Attributes
    ----------
    fileName : str
          the name of the chunk or file 
    order : int
          the order of the chunk
    peerPort : int
        the listening port of the peer having the chunk 
    """
    def __init__(self, fileName,order ,peerPort):
        self.fileName = fileName
        self.order = order
        self.peerPort = peerPort
    
    def toString(self):
        return "(Chunk filename: {0} Order: {1} peerPort: {2})".format(self.fileName,self.order,self.peerPort)
    def __str__(self):
        return "Chunk filename: {0} Order: {1} peerPort: {2}".format(self.fileName,self.order,self.peerPort)
     


def splitIntoChunks(filePath, numberOfChunks):
     """Splits the files given its path into N number of chunks"""
     files = []
     fileSize = os.path.getsize(filePath) 
     CHUNK_SIZE = math.ceil((fileSize/numberOfChunks)) # divide the file into N chuncks


     file_number = 1
     with open(filePath, "rb") as f:
          chunk = f.read(CHUNK_SIZE)
          while chunk:
               filename = str(file_number)+ filePath
               files.append(filename)
               with open(filename,"wb") as chunk_file:
                    chunk_file.write(chunk)
               file_number += 1
               chunk = f.read(CHUNK_SIZE)
          f.close()
     return files

def getFileMD5Hash(filePath):
     """Returns the md5 has of the files given its path"""
     with open(filePath,"rb") as f:
          bytes = f.read() # read file as bytes
          readable_hash = hashlib.md5(bytes).hexdigest()
          return readable_hash

def deletedFiles(listOfPathsToFiles):
     """Delete the files in the listOfPathsToFiles Array"""
     for path in listOfPathsToFiles:
          os.remove(path)
          

def removePeerFromManifest(port):
     """Remove peer from the manifest in case of a peer timeout. Return the files that
     the tracker will need to request back from other peers"""
     filesToRequest = []
     for i in range(len(manifest)):
          fileWithChunks = manifest[i]
          modifiedchunks = []
          modifiedchunks.extend(fileWithChunks.chunks)
          for j in range(len(fileWithChunks.chunks)):
               chunk = fileWithChunks.chunks[j]
               if chunk.peerPort == port:
                    modifiedchunks.remove(chunk)
                    # add to files to request later
                    if(chunk.fileName not in filesToRequest):     
                         filesToRequest.append(chunk.fileName)   
          fileWithChunks.set_chunks(modifiedchunks)
          fileWithChunks.number_of_chunks = len(modifiedchunks)
          manifest[i] = fileWithChunks
     return filesToRequest

def getListOfPeersPortsHavingtheChunkFileName(chunkFileName):
     """Get all peers having the chunk"""
     listOfPorts = []
     for files in manifest:
          for chunk in files.chunks:
               if(chunk.fileName == chunkFileName):
                    listOfPorts.append(chunk.peerPort)
     return listOfPorts

def addPeerChunkToManifest(chunk):
     for i in range(len(manifest)):
          fileWithChunks = manifest[i]
          chunks = fileWithChunks.chunks
          if fileWithChunks.name in chunk.fileName :
               chunks.append(chunk)
               fileWithChunks.set_chunks(chunks)
               fileWithChunks.number_of_chunks = len(chunks)
               manifest.pop(i)
               manifest.append(fileWithChunks)

def saveToManifest(filename, numberOfChunks, md5Hash, chuncks):
     """Save the distributed file into the manifest and manifest list"""
     distributed_file = fileDistributed(filename,numberOfChunks, md5Hash, chuncks)
     manifest.append(distributed_file)

def dumpTheManifestfile():
     """Save the mainfest list objects into the manifest file"""
     manifestfile = open('manifest.obj', 'wb') 
     pickle.dump(manifest, manifestfile)

def recieveFile(peerSocket):
    """Recieve file on the tracker listening port"""
    SEPARATOR = "<SEPARATOR>"
    BUFFER_SIZE = 4096
    received = peerSocket.recv(BUFFER_SIZE).decode()
    filename, filesize = received.split(SEPARATOR)
    # remove absolute path if there is
    filename = os.path.basename(filename)
    filesize = int(filesize)
    print ("From Peer: Sending", filename)
    # recieving file
    progress = tqdm.tqdm(range(math.ceil((filesize)/BUFFER_SIZE)), "Recieving "+filename, unit="B", unit_scale=True, unit_divisor=1024)
    with open(filename, "wb") as f:
        for _ in progress:
            bytes_read = peerSocket.recv(BUFFER_SIZE)
            if not bytes_read:
                # nothing is received
                # file transmitting is done
                break
            f.write(bytes_read)
            progress.update(len(bytes_read))
    return filename

def sendFile(filePath, connectionSocket):
     """ Send file given the connection socket and file path"""
     SEPARATOR = "<SEPARATOR>"
     BUFFER_SIZE = 4096 # send 4096 bytes each time step
     # send file info
     filesize = os.path.getsize(filePath)
     connectionSocket.send((filePath+SEPARATOR+str(filesize)).encode())
          
     # start sending the file
     progress = tqdm.tqdm(range(math.ceil((filesize)/BUFFER_SIZE)), "Sending "+filePath, unit="B", unit_scale=True, unit_divisor=1024)
     with open(filePath, "rb") as f:
          for _ in progress:
               bytes_read = f.read(BUFFER_SIZE)
               try:
                    connectionSocket.sendall(bytes_read)
               except SocketError as e:
                    if e.errno != errno.EPIPE:
                         raise
                    else:
                         pass
               
               if not bytes_read:
                    break
               progress.update(len(bytes_read))
                    

def shufflingFunction():
     return 0.1

def requestFileFromPeer(peerPort,filename):
    """Request file from peer given his listening port number and the file name requested
    Parameters
    ---------
    peerPort : int
     the listening port number of the peer
    filename : String
     the filename of the requested file
    """
    peerName = "127.0.0.1"
    BUFFER_SIZE = 4096 
    Socket = socket(AF_INET, SOCK_STREAM)
    Socket.connect((peerName,peerPort))
    # Handshaking with the peer
    Socket.send(("Requesting file|"+filename).encode())
    acceptanceMessage = Socket.recv(BUFFER_SIZE)
    print("From Tracker:", acceptanceMessage.decode())
    # Requesting the file from the peer
    Socket.send(filename.encode())
    # Recieving the requested file or manifest file from the peer
    recieveFile(Socket)
    Socket.close()

def StoreFileAtPeer(peerPort, filePath):
     """Store file at peer given his listening port number and the file path
     Parameters
     ---------
     peerPort : int
          the listening port number of the peer
     filePath : String
          the path of the file that the tracker wnats to send
     """
     localhost = "127.0.0.1"
     trackerSocket = socket(AF_INET, SOCK_STREAM)
     trackerSocket.connect((localhost,peerPort))
     trackerSocket.send(("Sending File").encode())
     # used to indicate if the peer is ready to recieve the file
     message = trackerSocket.recv(2048).decode()
     print(message)
     sendFile(filePath,trackerSocket)
     trackerSocket.close()


def listenForIncomingPeerRequests():
     """Listen for incoming requests from peers regarding a file. If found send it to the peer, else send the manifest file."""
     while True:
          connectionSocket, _ = serverSocket.accept()
          # recieve peer listning port for future communications
          # handshake = "Hello + PortNumber"
          handshake = connectionSocket.recv(2048).decode()
          peerPort = int(handshake.split(" ")[1])
          if(peerPort not in peersPorts):
               peersPorts.append(peerPort)
               print(peersPorts)
          connectionSocket.send(("HELLO").encode())
          # recieving the requested filename
          filename = connectionSocket.recv(2048).decode()
          
          if(filename in files):
               sendFile(filename,connectionSocket)
          else:
               sendFile("manifest.obj",connectionSocket)

          connectionSocket.close()

def redistributeFile(filePath):
     """ Redistribute file when the number of peers is equal to 3"""
     N = 3
     # while number of peers is less than N
     while (len(peersPorts) < N):
          time.sleep(5)
     time.sleep(1)

     # split file into N chunks
     files = splitIntoChunks(filePath, numberOfChunks= N)

     # choosen N peers to distribute the file to
     choosenPeerPorts = random.sample(peersPorts, N)
     chunksList = []

     # store files at selected peers
     i = 0
     for p in choosenPeerPorts:
          StoreFileAtPeer(p,files[i])
          chunksList.append(chunk(files[i],i,p))
          i += 1
          time.sleep(1)
     
     # store another copy at selected peers
     random.shuffle(choosenPeerPorts,shufflingFunction)
     i = 0
     for p in choosenPeerPorts:
          StoreFileAtPeer(p,files[i])
          chunksList.append(chunk(files[i],i,p))
          i += 1
          time.sleep(1)
     
     # save results to a manifest file
     saveToManifest(filePath, N,getFileMD5Hash(filePath),chunksList)
     dumpTheManifestfile()
     time.sleep(2)
     files.append(filePath)
     deletedFiles(files)




def checkIfPeersAreStillConnected():
     """Check if the peer is stilled connected to the tracker else remove him from manifest and redistribute files.
     
     The peer is considered disconnected when the tracker stops recieving UDP packets from the peer for 10s.
     
     The tracker maintains a timer for each peer in the connection.
     
     """
     # Listining to UDP packets
     serverPort = 12001
     serverSocket = socket(AF_INET, SOCK_DGRAM)
     serverSocket.bind(('', serverPort))
     serverSocket.settimeout(10.0)
     dictOfPeers = {}

     while 1:
          tempDictOfPeers = {}
          for port, lastContactTime in dictOfPeers.items(): 
               if time.time() - lastContactTime>= 10:
                    print(port+" timeout")
                    if(int(port) in peersPorts):
                         # remove peer from the list of peers
                         peersPorts.remove(int(port))
                         # remove peer from the Manifest
                         filesToRequest = removePeerFromManifest(int(port))
                         print(filesToRequest)
                         dumpTheManifestfile()
                         # request file from another peers
                         # get the peers to request files from 
                         for f in filesToRequest:
                              portsHavingTheFile = getListOfPeersPortsHavingtheChunkFileName(f)
                              portOne = portsHavingTheFile[0]

                              # send request to the first peer having the file to resend the file back
                              try:
                                   requestFileFromPeer(peerPort= portOne,filename= f)
                              except SocketError as e:
                                   if e.errno != errno.ECONNRESET:
                                        raise
                                   pass
                              
                              # restore the file chunk the next peer
                              for p in peersPorts:
                                   
                                   if p not in portsHavingTheFile: # if peer doesn't alreading have the file
                                        StoreFileAtPeer(p,f)
                                        newChunk = chunk(fileName=f,order=0,peerPort=p)
                                        addPeerChunkToManifest(chunk=newChunk)
                                        dumpTheManifestfile()
                                        break
                              time.sleep(1)
                         deletedFiles(filesToRequest)
               else:
                    tempDictOfPeers[port] = lastContactTime
          dictOfPeers = tempDictOfPeers
          
          try:
               message, clientAddress = serverSocket.recvfrom(2048)
               print ('pinging tracker:', message.decode(), 'from IP: %s Port: %s' % clientAddress)
               Info = message.decode().split("|")
               seqNo, port, t = Info 
               timestamp = float(t)
               dictOfPeers[port] = timestamp
          except SocketError as e:
               pass

     serverSocket.close()


serverPort = 12000
serverSocket = socket(AF_INET,SOCK_STREAM)
serverSocket.bind(('',serverPort))
serverSocket.listen(10)

manifest = [] # used to store distributed file objects
files = ["file.txt","sample.mp3"] # used to store paths to the files which the tracker has
peersPorts = [] # used to store identify that can be used to send files to peers

dumpTheManifestfile()
print ("The tracker is ready to receive")

# start a thread responsible for satisfying users request
t1 = threading.Thread(target=listenForIncomingPeerRequests, args=()) 
t1.start()
# start a thread responsible for distributing video.mp4 if 3 peers are avialable
t2 = threading.Thread(target=redistributeFile, args=(["video.mp4"])) 
t2.start()

# start a thread responsible for making sure the peer in still connected
t3 = threading.Thread(target=checkIfPeersAreStillConnected, args=())
t3.start()

t1.join()

