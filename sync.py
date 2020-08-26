#2.建立TCP socket 连接
#3.以server为基准校准文件，校准完之后两边数据库是一致的，之后的文件变动只与自身作比较
#4.间隔n秒检测一次，当发现有变动，TCP传送新的文件给另一端

import struct
import json
import pickle
import os
import hashlib
import time
from socket import *
config={}
def LoadConfig():
    global config
    with open('./config.json','r',encoding='utf8')as fp:
        config = json.load(fp)

def GetFileDatabase():
    global config
    filedatabase={}
    for root,dirs,files in os.walk(config['path']):
        for name in files:
            fullpath=os.path.join(root,name)
            flag=False
            for i in config['allowtype']:
                if fullpath.endswith(i):
                    flag=True
            if flag:
                print(fullpath)
                with open(fullpath,'r') as f:
                    thehash=hashlib.md5()
                    theline=f.readline()
                    while(theline):
                        thehash.update(theline.encode("utf8"))
                        theline=f.readline()
                finalhash=thehash.hexdigest()
                print(finalhash)
                filedatabase[fullpath]=finalhash
    return filedatabase

def ReceiveData(socketid,sync,firstbyte):

    if sync:
        n=4
        totaldata=b''
    else:
        n=3
        totaldata+=firstbyte
    while True:
        data=socketid.recv(n)
        if data:
            totaldata+=data
            n=n-len(data)
        if n==0:
            n=struct.unpack("i",totaldata)[0]
            break
                

    data=b''
    totaldata=b''
    while True:
        data=socketid.recv(n)
        if data:
            totaldata+=data
            n=n-len(data)
        if n==0:
            break
    jsondata=pickle.loads(totaldata)

    return jsondata

def SendData(socketid,jsondata):

    bytejsondata=pickle.dumps(jsondata)
    length=struct.pack("i",len(bytejsondata))
    socketid.sendall(length)
    socketid.sendall(bytejsondata)


def EncodeFile(path):
    return 1
    pass

def SocketConnect():

    HOST =config['ip'] 
    PORT = config['port']
    ADDRESS = (HOST, PORT)
    if config['server']:
        # 创建监听socket
        tcpServerSocket = socket(AF_INET, SOCK_STREAM)
        # 绑定IP地址和固定端口
        tcpServerSocket.bind(ADDRESS)
        print("服务器启动，监听端口{}...".format(ADDRESS[1]))
        tcpServerSocket.listen(5)
        client_socket, client_address = tcpServerSocket.accept()
        print("客户端已连接")
        filehash=GetFileDatabase()
        SendData(client_socket,filehash)
        data=ReceiveData(client_socket,True,0)
        sendbytes={}
        for i in data:
            filedata=EncodeFile(i)
            sendbytes[i]=filedata
        SendData(client_socket,sendbytes)
    else:
        tcpClientSocket = socket(AF_INET, SOCK_STREAM)
        tcpClientSocket.connect(ADDRESS)
        data=ReceiveData(tcpClientSocket,True,0)
        oldfiles=[]
        for i in data:
            print(i)
            oldfiles.append(i)
        SendData(tcpClientSocket,oldfiles)




if __name__=='__main__':
    LoadConfig()
    SocketConnect()
