from socket import *
from socket import error as SocketError
import os
import math
import hashlib
import pickle
import tqdm
import time
import threading 
import random
import logging
import errno
class fileDistributed:
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
    def __init__(self, fileName,order ,peerPort):
        self.fileName = fileName
        self.order = order
        self.peerPort = peerPort
    
    def toString(self):
        return "(Chunk filename: {0} Order: {1} peerPort: {2})".format(self.fileName,self.order,self.peerPort)
    def __str__(self):
        return "Chunk filename: {0} Order: {1} peerPort: {2}".format(self.fileName,self.order,self.peerPort)
     
serverPort = 12000
serverSocket = socket(AF_INET,SOCK_STREAM)
serverSocket.bind(('',serverPort))
serverSocket.listen(10)
manifest = []
files = ["file.txt"]
peersPorts = []



def splitIntoChunks(filePath, numberOfChunks):
     files = []
     fileSize = os.path.getsize(filePath) 
     CHUNK_SIZE = math.ceil((fileSize/numberOfChunks)) # divide the file into N chuncks
     file_number = 1
     with open(filePath) as f:
          chunk = f.read(CHUNK_SIZE)
          while chunk:
               filename = str(file_number)+ filePath
               files.append(filename)
               with open(filename,"w+") as chunk_file:
                    chunk_file.write(chunk)
               file_number += 1
               chunk = f.read(CHUNK_SIZE)
          f.close()
     return files

def getFileMD5Hash(path):
     with open(path,"rb") as f:
          bytes = f.read() # read file as bytes
          readable_hash = hashlib.md5(bytes).hexdigest()
          return readable_hash

def getManifestObjects():
    filehandler = open("manifest.obj", 'rb') 
    manifest = pickle.load(filehandler)
    return manifest

# combines the file using a list of chuncks composing that file
def combineFiles(filesPath, combined_file):
     output_file = open(combined_file,'wb')
     for path in files:
          fileSize = os.path.getsize(path)
          input_file = open(path, 'rb')
          while True:
               bytes = input_file.read(fileSize)
               if not bytes:
                    break
               output_file.write(bytes)
          input_file.close()
     output_file.close()

# delete the files in the filesPath Array
def deletedFiles(filesPath):
     for path in filesPath:
          os.remove(path)

# save the splitted file into the manifest and manifest file
def saveToManifest(filename, numberOfChunks, md5Hash, chuncks):
     distributed_file = fileDistributed(filename,numberOfChunks, md5Hash, chuncks)
     manifest.append(distributed_file)

# remove peer from manifest in case of a peer timeout
def removePeerFromManifest(port):
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
          for f in manifest:
               print(f)
     return filesToRequest


def getListOfPeersPortsHavingtheChunkFileName(chunkFileName):
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


def dumpTheManifestfile():
     manifestfile = open('manifest.obj', 'wb') 
     pickle.dump(manifest, manifestfile)

def requestFileFromPeer(peerPort,filename):
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
def recieveFile(peerSocket):
    SEPARATOR = "<SEPARATOR>"
    BUFFER_SIZE = 4096 # send 4096 bytes each time step
    received = peerSocket.recv(BUFFER_SIZE).decode()
    filename, filesize = received.split(SEPARATOR)
    # remove absolute path if there is
    filename = os.path.basename(filename)
    filesize = int(filesize)
    print ("From Server: Sending", filename)
    # recieving file
    progress = tqdm.tqdm(range(filesize), "Receiving "+filename, unit="B", unit_scale=True, unit_divisor=1024)
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


def sendFile(filename, connectionSocket):
     
     SEPARATOR = "<SEPARATOR>"
     BUFFER_SIZE = 4096 # send 4096 bytes each time step
     

     # send file info
     filesize = os.path.getsize(filename)
     connectionSocket.send((filename+SEPARATOR+str(filesize)).encode())
          
     # start sending the file
     progress = tqdm.tqdm(range(filesize), "Sending "+filename, unit="B", unit_scale=True, unit_divisor=1024)
     with open(filename, "rb") as f:
          for _ in progress:
               # read the bytes from the file
               bytes_read = f.read(BUFFER_SIZE)
               if not bytes_read:
                    # file transmitting is done
                    break
               # we use sendall to assure transimission in 
               # busy networks
               connectionSocket.sendall(bytes_read)
               # update the progress bar
               progress.update(len(bytes_read))


def listenForIncomingPeerRequests():
     connectionSocket, _ = serverSocket.accept()
     # recieve client listning port for future communications
     # handshake = "Hello + PortNumber"
     handshake = connectionSocket.recv(2048).decode()
     peerPort = int(handshake.split(" ")[1])
     if(peerPort not in peersPorts):
          peersPorts.append(peerPort)
          print(peersPorts)
     connectionSocket.send(("HELLO").encode())
     # recieving the requested filename
     filename = connectionSocket.recv(2048).decode()
     print(filename)
     
     if(filename in files):
          sendFile(filename,connectionSocket)
     else:
          sendFile("manifest.obj",connectionSocket)

     connectionSocket.close()

def StoreFileAtPeer(peerPort, filePath):
     localhost = "127.0.0.1"
     trackerSocket = socket(AF_INET, SOCK_STREAM)
     trackerSocket.connect((localhost,peerPort))
     trackerSocket.send(("Sending File").encode())
     # used to indicate if the peer is ready to recieve the file
     message = trackerSocket.recv(2048).decode()
     print(message)
     sendFile(filePath,trackerSocket)
     trackerSocket.close()


def threadOne():
     while True:
          # in case a file is requested from any peer
          listenForIncomingPeerRequests()

def threadTwo():
     N = 2
     # while number of peers is less than N
     while (len(peersPorts) < N):
          time.sleep(5)
     time.sleep(5)
     filePath = "filecomb.txt"

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
     
     # store another copy at selected peers
     choosenPeerPorts.reverse()
     i = 0
     for p in choosenPeerPorts:
          StoreFileAtPeer(p,files[i])
          chunksList.append(chunk(files[i],i,p))
          i += 1
     
     # save results to a manifest file
     saveToManifest(filePath, N,getFileMD5Hash(filePath),chunksList)
     dumpTheManifestfile()
     time.sleep(5)
     deletedFiles(files)




def threadThree():
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
                         for f in manifest:
                              print(f)
                         
                         print(filesToRequest)
                         dumpTheManifestfile()
                         # tested till here
                         # request file from another peers
                         # get the peers to request files from 
                         for f in filesToRequest:
                              ports = getListOfPeersPortsHavingtheChunkFileName(f)
                              portOne = ports[0]

                              # send request to peer to get resend the file back
                              try:
                                   requestFileFromPeer(peerPort= portOne,filename= f)
                              except SocketError as e:
                                   if e.errno != errno.ECONNRESET:
                                        raise
                                   pass
                              
                              # restore the file chunk the next peer
                              for p in peersPorts:
                                   if p not in ports:
                                        StoreFileAtPeer(p,f)
                                        newChunk = chunk(fileName=f,order=0,peerPort=p)
                                        addPeerChunkToManifest(chunk=newChunk)
                                        dumpTheManifestfile()
                                        break
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

dumpTheManifestfile()
print ("The tracker is ready to receive")

# start a thread responsible for satisfying users request
t1 = threading.Thread(target=threadOne, args=()) 
t1.start()
# start a thread responsible for distributing filecomb.txt if more then 2 peers are avialable
t2 = threading.Thread(target=threadTwo, args=()) 
t2.start()

t3 = threading.Thread(target=threadThree, args=())
t3.start()

t3.join()

