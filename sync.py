#2.建立TCP socket 连接
#3.以server为基准校准文件，校准完之后两边数据库是一致的，之后的文件变动只与自身作比较
#4.间隔n秒检测一次，当发现有变动，TCP传送新的文件给另一端

import base64
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
                total=b""
                with open(fullpath,'rb') as f:
                    thehash=hashlib.md5()
                    while True:
                        temp=f.read(1024)
                        if temp==b"":
                            break
                        else:
                            thehash.update(temp)
                finalhash=thehash.hexdigest()
                print(finalhash)
                filedatabase[fullpath.replace(config['path'],'',1)]=finalhash
    return filedatabase

def ReceiveData(socketid):

    n=4
    totaldata=b''
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

    print("receive data:")
    print(jsondata)
    return jsondata

def SendData(socketid,jsondata):

    bytejsondata=pickle.dumps(jsondata)
    length=struct.pack("i",len(bytejsondata))
    socketid.sendall(length)
    socketid.sendall(bytejsondata)
    print("send data:")
    print(jsondata)

    
# {
#     "path":{"b64file":"value","flag":1}
# }
def CompareDatabase(old,new):
    print("Compare old , new")
    print(old)
    print(new)
    res={}
    # 先处理大家都有的,改动的
    # 然后处理new有old没有的,新增的
    # 最后处理old有new没有的,删除的
    for (key,value) in new.items():
        # key=key.replace(config['path'],'',1)
        if old.get(key)!=None:
            if value!=old[key]:
                res[key]={"b64file":EncodeFile(config['path']+key),"flag":1}
    for (key,value) in new.items():
        # key=key.replace(config['path'],'',1
        if old.get(key)==None:
            res[key]={"b64file":EncodeFile(config['path']+key),"flag":2}

    for (key,value) in old.items():
        # key=key.replace(config['path'],'',1)
        if new.get(key)==None:
            res[key]={"b64file":b"","flag":3}
    return res



def EncodeFile(path):
    total=b""
    with open(path,'rb') as f:
        while True:
            temp=f.read(1024)
            if temp==b"":
                break
            else:
                total+=temp
    res=base64.b64encode(total)
    return res


def DecodeFile(path,b64file):
    filedata=base64.b64decode(b64file)
    with open(path,mode="wb") as f:
        f.write(filedata)

def EventLoop(socketid):
    if config['master']:
        data=ReceiveData(socketid)
        filehash=GetFileDatabase()
        sendbytes=CompareDatabase(data,filehash)
        SendData(socketid,sendbytes)
    else:
        filehash=GetFileDatabase()
        SendData(socketid,filehash)
        data=ReceiveData(socketid)
        ProcessDiffStrucct(data)
    socketid.setblocking(False)
    while True:
        try:
            socketid.recv(1,MSG_PEEK)
        except BlockingIOError:
            pass
        print("waiting ")
        time.sleep(1)



# {
#     "path":{"b64file":"value","flag":1}
# }
def ProcessDiffStrucct(diffstruct):
    for (key,value) in diffstruct.items():
        key=config['path']+key
        if value['flag']==3:
            #delete
            os.remove(key)
        if value['flag']==2:
            #add
            DecodeFile(key,value['b64file'])

        if value['flag']==1:
            #edit
            DecodeFile(key,value['b64file'])

        pass
    pass

def SocketConnect():

    HOST =config['ip'] 
    PORT = config['port']
    ADDRESS = (HOST, PORT)
    if config['server']:
        # 创建监听socket
        tcpServerSocket = socket(AF_INET, SOCK_STREAM)
        tcpServerSocket.setsockopt( SOL_SOCKET,SO_REUSEADDR, 1 )
        # 绑定IP地址和固定端口
        tcpServerSocket.bind(ADDRESS)
        print("服务器启动，监听端口{}...".format(ADDRESS[1]))
        tcpServerSocket.listen(5)
        client_socket, client_address = tcpServerSocket.accept()
        print("客户端已连接")
        EventLoop(client_socket)
    else:
        tcpClientSocket = socket(AF_INET, SOCK_STREAM)
        tcpClientSocket.connect(ADDRESS)
        print("服务器已连接")
        EventLoop(tcpClientSocket)
        
        




if __name__=='__main__':
    # file1=EncodeFile("/root/temp/test.c")
    # DecodeFile("/root/temp/test2.c",file1)
    # total=b""
    # with open("/root/SyncFile/README.md","rb") as f:
    #     total=f.read(1024)
    # 
    # with open("/root/SyncFile/README2.md","wb") as f:
    #     f.write(total)
    LoadConfig()
    SocketConnect()
    

