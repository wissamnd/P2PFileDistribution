from socket import *
import time
import random
import tqdm
import os
import pickle
import threading
import time
import hashlib
from socket import error as SocketError
import errno
import math

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
     

manifest = []

def getFileMD5Hash(path):
     with open(path,"rb") as f:
          bytes = f.read() # read file as bytes
          readable_hash = hashlib.md5(bytes).hexdigest()
          return readable_hash
          
def combineFiles(listOfPathsTofiles, combined_file):
     output_file = open(combined_file,'wb')
     for path in listOfPathsTofiles:
          fileSize = os.path.getsize(path)
          input_file = open(path, 'rb')
          while True:
               bytes = input_file.read(fileSize)
               if not bytes:
                    break
               output_file.write(bytes)
          input_file.close()
     output_file.close()
def deletedFiles(listOfPathsTofiles):
     for path in listOfPathsTofiles:
          os.remove(path)

def getManifestObjects():
    filehandler = open("manifest.obj", 'rb') 
    manifest = pickle.load(filehandler)
    return manifest

def checkIfFileIsInManifest(filename, manifest):
    for f in manifest:
        if filename == f.name:
             return True
    return False

def requestFileFromPeer(filename, peerPort):
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
    # Recieving the requested file or manifest file from the tracker
    recieveFile(Socket)
    Socket.close()


def requestFileFromTracker(filename):
    serverName = "127.0.0.1"
    serverPort = 12000
    clientSocket = socket(AF_INET, SOCK_STREAM)
    clientSocket.connect((serverName,serverPort))
    # Handshaking with the tracker
    clientSocket.send(("Hello "+ str(peerPort)).encode())

    acceptanceMessage = clientSocket.recv(2048)
    print("From Tracker:", acceptanceMessage.decode())

    # Requesting the file from the tracker
    clientSocket.send(filename.encode())
    
    # Recieving the requested file or manifest file from the tracker
    returnedfileNameFromTracker = recieveFile(clientSocket)

    # handle the case where the tracker sends the peer a file
    if("manifest.obj" == returnedfileNameFromTracker):
        manifest = getManifestObjects()

        # establish a connection with each peer containing a chunk and then combine them
        files = []
        
        for f in manifest:
            if(f.name == filename):
                for c in f.chunks:
                    # if the peer doesn't have the chunk and if the chunk is not already retrieved
                    if(c.peerPort != peerPort and c.fileName not in files):
                        print(c.fileName)
                        print("requesting "+c.fileName+" from", c.peerPort)
                        try:
                            time.sleep(1)
                            requestFileFromPeer(c.fileName, c.peerPort)
                        except SocketError as e:
                            if e.errno != errno.ECONNRESET and e.errno != errno.EPIPE:
                                raise # Not error we are looking for
                            pass # Handle error here.
                        files.append(c.fileName)
                combineFiles(files,filename)
                deletedFiles(files)
                if(f.md5Hash == getFileMD5Hash(filename)):
                    print("File is successfully recieved")
    clientSocket.close()
    

def recieveFile(peerSocket):
    SEPARATOR = "<SEPARATOR>"
    BUFFER_SIZE = 4096 # send 4096 bytes each time step
    received = peerSocket.recv(BUFFER_SIZE).decode()
    filename, filesize = received.split(SEPARATOR)
    # remove absolute path if there is
    filename = os.path.basename(filename)
    filesize = int(filesize)
    print ("From Tracker: Sending", filename)
    # recieving file
    progress = tqdm.tqdm(range(math.ceil((filesize)/BUFFER_SIZE)), "Receiving "+filename, unit="B", unit_scale=True, unit_divisor=1024)
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

def sendFile(filename, socket):
     # send file info
     SEPARATOR = "<SEPARATOR>"
     BUFFER_SIZE = 4096 # send 4096 bytes each time step
     filesize = os.path.getsize(filename)
     socket.send((filename+SEPARATOR+str(filesize)).encode())
     # start sending the file
     progress = tqdm.tqdm(range(math.ceil((filesize)/BUFFER_SIZE)), "Sending "+filename, unit="B", unit_scale=True, unit_divisor=1024)
     with open(filename, "rb") as f:
          for _ in progress:
               bytes_read = f.read(BUFFER_SIZE)
               if not bytes_read:
                    break
               socket.sendall(bytes_read)
               progress.update(len(bytes_read))

    
    
# open a listining port for the peer
peerPort = random.randint(49152,65535)
peerSocket = socket(AF_INET,SOCK_STREAM)
peerSocket.bind(('',peerPort))
peerSocket.listen(4)

def listenForIncomingIncomingRequests():
    """Listen for incoming requests from peers and tracker
    handles three events:
    - recieving a file chunk from the tracker to be stored
    - recieving a request to send a file chunk back to the tracker
    - recieving a request to send a file chunk to a peer
    """
    while True:
        connectionSocket, addr = peerSocket.accept()
        action = connectionSocket.recv(2048).decode()
        if(action == "Sending File"):
            # Make the tracker know that you confirm storing a chunk on your side
            connectionSocket.send(("OK: Send your file").encode())
            # recieve file from tracker
            recieveFile(connectionSocket)
        elif ("Requesting file" in action):
            connectionSocket.send(("OK: Sending your file").encode())
            message, filename = action.split("|")
            sendFile(filename, connectionSocket)
        connectionSocket.close()



def userPrompt():
     """Prompt the user to enter the file he wants to request from the traker"""
     while True:
         filename = input("Input filename: ")
         if(filename == "quit" ):
             break
         requestFileFromTracker(filename)


def pingTracker():
    """Ping the tracker with UDP messages (every 5s) indicating that the peer is still in the connection.

       Message Format: sequence Number|peerPort|timestamp
    """
    serverName = '127.0.0.1'
    serverPort = 12001
    clientSocket = socket(AF_INET, SOCK_DGRAM)
    sequenceNumber = 0
    while True:
        message = str(sequenceNumber)+"|" + str(peerPort)+ "|"+str(time.time())
        clientSocket.sendto(message.encode(),(serverName, serverPort))
        sequenceNumber+= 1
        time.sleep(5)
    clientSocket.close()


t1 = threading.Thread(target=listenForIncomingIncomingRequests, args=()) 
t1.start()
time.sleep(2)
t2 = threading.Thread(target=userPrompt, args=()) 
t2.start()
t3 = threading.Thread(target=pingTracker, args=())
t3.start()
t1.join()

