#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import threading
import socket
import time

class UserInterface(threading.Thread):
    def __init__(self,addrdev):
        super(UserInterface,self).__init__()
        # 创建接收数据的socket
        self.rda = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 绑定到addrdev
        self.rda.bind(addrdev)

        # 数据流格式版本
        self.fileVersion = 3

        self.dataInfo = None
        self.dataCache = []

        self.lock = threading.RLock()

        self.daemon = True
        self.start()

    # 线程函数，用来接收远程数据，不要修改
    def run(self): # 线程，从udp读取数据
        dataInfo = {'dataType':None,'srate':0,'chs':0,'includeEvt':0,'includeEvtSoft':0,'totalch':0}
        ddtype = [np.float32,np.float64]
        while True: # 通过udp socket接收数据
            buf,_ = self.rda.recvfrom(65535)
            # 获得数据
            # 获得头信息
            headLen = np.frombuffer(buf[:4],dtype=np.int32)[0]
            headBuffer = buf[:4*headLen]
            dataBuffer = buf[4*headLen:]

            head = np.frombuffer(headBuffer,dtype=np.int32)

            # 文件类型校验
            if self.fileVersion != head[1]:
                continue

            dataInfo = {'dataType':ddtype[head[2]],'srate':head[3],'chs':head[4],
                        'includeEvt':head[5],'includeEvtSoft':head[6]}
            totalch = head[4]
            if dataInfo['includeEvt']:  totalch += 1
            if dataInfo['includeEvtSoft']: totalch += 1

            dataInfo['totalch'] = totalch

            raway = np.frombuffer(dataBuffer,dtype=dataInfo['dataType'])
            sampleN = int(raway.size//totalch)
            eeg = raway.reshape(sampleN,totalch).transpose()

            with self.lock:
                self.dataCache.append(eeg)
                self.dataCache = self.dataCache[-100:]
                self.dataInfo = dataInfo.copy()
                
    def getData(self):
        # 从线程获取数据
        # 修复：先给局部变量赋初值，避免 self.dataInfo 为 None 时 UnboundLocalError
        userDataInfo = None
        userDataCache = []
        with self.lock:
            if self.dataInfo is not None:
                userDataInfo = self.dataInfo
                self.dataInfo = None

                userDataCache = self.dataCache
                self.dataCache = []
        
        if len(userDataCache)>0:
            eeg = np.hstack(userDataCache)
        else:
            eeg = None
        
        return userDataInfo,eeg


if __name__ == '__main__':
    # 远程地址，由用户通过dec.js字段remoteAccess定义
    addrdev = ('127.0.0.1',8090)
    # 创建接口
    uif = UserInterface(addrdev)
    time.sleep(0.25)
    
    while True:
        # 读取数据
        Info,eeg = uif.getData()
        if eeg is not None:
            # 开始处理信号.....
            print(Info)
        
        time.sleep(0.2)