#coding=utf-8
#2.建立TCP socket 连接
#3.以server为基准校准文件，校准完之后两边数据库是一致的，之后的文件变动只与自身作比较
#4.间隔n秒检测一次，当发现有变动，TCP传送新的文件给另一端
import os
import base64
import struct
import json
import pickle
import os
import hashlib
import time
import re
import select


from socket import *
config={}
def LoadConfig():
    global config
    with open('./config.json','r',encoding='utf8')as fp:
        config = json.load(fp)

def GetFileDatabase():
    global config
    filedatabase={}
    for root,dirs,files in os.walk(config['server']['path']):
        for name in files:
            fullpath=os.path.join(root,name)
            fullpath=fullpath.replace('\\','/')
            flag=False
            for i in config['server']['whitelist']:
                if re.search(i,fullpath) :
                    flag=True
            if flag:
                for i in config['server']['blacklist']:
                    if re.search(i,fullpath) :
                        flag=False
            if flag:
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
                filedatabase[fullpath.replace(config['server']['path'],'',1)]=finalhash
    return filedatabase

def ReceiveData(socketid):

    n=4
    totaldata=b''
    while True:
        try:
            data=socketid.recv(n)
            if data:
                totaldata+=data
                n=n-len(data)
            if n==0:
                n=struct.unpack("i",totaldata)[0]
                break
        except BlockingIOError:
            pass
                

    data=b''
    totaldata=b''
    while True:
        try:
            data=socketid.recv(n)
            if data:
                totaldata+=data
                n=n-len(data)
            if n==0:
                break
        except BlockingIOError:
            pass
            
    jsondata=pickle.loads(totaldata)

    print("receive data:")
    print(jsondata)
    return jsondata

def SendData(socketid,jsondata):

    bytejsondata=pickle.dumps(jsondata)
    length=struct.pack("i",len(bytejsondata))
    socketid.send(length)
    inputs=[socketid,]
    splice=0
    while True:
        flag=False
        read_list,write_list,except_list=select.select(inputs,inputs,[],1)
        for w in write_list:
            splice+=1;
            if len(bytejsondata)>splice*1000:
                w.send(bytejsondata[(splice-1)*1000:splice*1000])
            else:
                w.send(bytejsondata[(splice-1)*1000:len(bytejsondata)])
                flag=True
        if flag:
            break


    print("send data:")
    print(jsondata)

    
# {
#     "path":{"b64file":"value","flag":1}
# }
def CompareDatabase(old,new):
    res={}
    # 先处理大家都有的,改动的
    # 然后处理new有old没有的,新增的
    # 最后处理old有new没有的,删除的
    for (key,value) in new.items():
        # key=key.replace(config['server']['path'],'',1)
        if old.get(key)!=None:
            if value!=old[key]:
                res[key]={"b64file":EncodeFile(config['server']['path']+key),"flag":1}
    for (key,value) in new.items():
        # key=key.replace(config['server']['path'],'',1
        if old.get(key)==None:
            res[key]={"b64file":EncodeFile(config['server']['path']+key),"flag":2}

    for (key,value) in old.items():
        # key=key.replace(config['server']['path'],'',1)
        if new.get(key)==None:
            res[key]={"b64file":b"","flag":3}
    return res

def check_and_creat_dir(file_url):
    '''
    判断文件是否存在，文件路径不存在则创建文件夹
    :param file_url: 文件路径，包含文件名
    :return:
    '''
    file_gang_list = file_url.split('/')

    if len(file_gang_list)>1:
        [fname,fename] = os.path.split(file_url)
        if not os.path.exists(fname):
            os.makedirs(fname)
        else:
            return None
        #还可以直接创建空文件
        
    else:
        return None

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
    check_and_creat_dir(path)
    with open(path,mode="wb") as f:
        f.write(filedata)

def EventLoop(socketid):

    global config
    config=ReceiveData(socketid)
    timeout=0

    if config['server']['master']:
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
    old=GetFileDatabase()
    while True:
        while True:
            try:
                ret=socketid.recv(4,MSG_PEEK)
                if ret==b"":
                    break
                data=ReceiveData(socketid)
                if data.get("heartbeat")!=None:
                    timeout=0
                else:
                    ProcessDiffStrucct(data)
                    new=GetFileDatabase()
                    old=new
            except BlockingIOError:
                break
        print(timeout)

        timeout+=1
        if timeout>10:
            socketid.close()
            break
        new=GetFileDatabase()
        sendbytes=CompareDatabase(old,new)
        if  bool(sendbytes):
            print("diff things")
            print(sendbytes)
            SendData(socketid,sendbytes)
        

        
        old=new

        time.sleep(config['server']['syncinterval'])



# {
#     "path":{"b64file":"value","flag":1}
# }
def ProcessDiffStrucct(diffstruct):
    for (key,value) in diffstruct.items():
        key=config['server']['path']+key
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

    HOST ='0.0.0.0' 
    PORT =9011
    ADDRESS = (HOST, PORT)
    # 创建监听socket
    tcpServerSocket = socket(AF_INET, SOCK_STREAM)
    tcpServerSocket.setsockopt( SOL_SOCKET,SO_REUSEADDR, 1 )
    # 绑定IP地址和固定端口
    tcpServerSocket.bind(ADDRESS)
    tcpServerSocket.listen(5)
    while True:
        print("服务器启动，监听端口{}...".format(ADDRESS[1]))
        client_socket, client_address = tcpServerSocket.accept()
        print("accept")
        print("客户端已连接")
        try:
            EventLoop(client_socket)
        except Exception as e:
            print(e.args)
            print(str(e))
            print(repr(e))
        
        




if __name__=='__main__':
    # file1=EncodeFile("/root/temp/test.c")
    # DecodeFile("/root/temp/test2.c",file1)
    # total=b""
    # with open("/root/SyncFile/README.md","rb") as f:
    #     total=f.read(1024)
    # 
    # with open("/root/SyncFile/README2.md","wb") as f:
    #     f.write(total)

    # print(re.search(".*","/root/"))
    # print(re.search("/xx.*","/root/"))
    # LoadConfig()
    SocketConnect()
    

