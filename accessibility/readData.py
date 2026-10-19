
import numpy as np
import matplotlib.pyplot as plt

dtype = ['float32','float64']
dtypelen = [4,8]

class ReadGmData():
    def __init__(self,path):
        self.path = path

    def readfile(self):
        buffer = b''
        with open(self.path,'rb') as f:
            buffer = f.read()

        headLen = np.frombuffer(buffer[:4],dtype=np.int32)[0]
        if headLen > 10:
            raise LookupError("文件可能损坏！")

        head = np.frombuffer(buffer[:4*headLen],dtype=np.int32)
        version = head[1]
        dataType = dtype[head[2]]
        dataTypeLen = dtypelen[head[2]]
        srate = head[3]
        totalchs = chs = head[4]
        includeEvt = head[5]
        includeEvtSoft = head[6]
        if includeEvt:
            totalchs += 1
        if includeEvtSoft:
            totalchs += 1

        if version != 3:
            raise LookupError("文件版本不支持！")

        databuffer = buffer[4*headLen:]
        databufferLen = len(databuffer)

        sampleN = databufferLen // totalchs // dataTypeLen
        databufferLen = sampleN * totalchs * dataTypeLen
        databuffer = databuffer[:databufferLen]

        data = np.frombuffer(databuffer,dtype=dataType)
        data = data.reshape(sampleN,totalchs).transpose()

        plt.plot(data[0,:])
        plt.show()
        return {'srate':srate,'chs':chs,'includeEvt':includeEvt,'includeEvtSoft':includeEvtSoft,'data':data}

if __name__ == '__main__':
    rd = ReadGmData(r'..\dd.dat')
    data = rd.readfile()