import binascii
import os
from operator import itemgetter

#필요한 정보를 web.py에서 받아오기
def reciveDiskinfo(a, b, c):
    global dataAreaStartSector
    dataAreaStartSector = a
    global sectorsPerCluster
    sectorsPerCluster = b
    global fatArea
    fatArea = c

#get sector
def getSector(sectorsize, filename):
    global sector_size
    sector_size = sectorsize
    imgfile = filename
    filesize = os.path.getsize(imgfile)
    sector_count = int(filesize / sector_size)

    # 이미지를 각 섹터별로 구분
    global sector
    sector = []
    f = open(imgfile, "rb")

    for i in range(sector_count):
        offset = sector_size * i
        f.seek(0 + offset)
        data = f.read(sector_size)
        hex_data = binascii.hexlify(data)
        sector.append(hex_data.decode())
    f.close()

#섹터번호, 오프셋을 이용하여 Ascii 문자 데이터를 추출하는 함수
def getAsciiDataByOffset(sectornum,start,end):
    end = end+1
    count = 0
    sector_data = []
    for i in range(int(len(sector[sectornum]) / 2)):
        sector_data.append(sector[sectornum][count:count + 2])
        count += 2
    data = "".join(sector_data[start:end])
    return binascii.unhexlify(data).decode()

#섹터번호, 오프셋을 이용하여 수 형식의 데이터를 추출하는 함수
def getNumbericDataByOffset(sectornum,start,end):
    end = end+1
    count = 0
    sector_data = []
    for i in range(int(len(sector[sectornum]) / 2)):
        sector_data.append(sector[sectornum][count:count + 2])
        count += 2
    data = sector_data[start:end]
    count = 0
    numdata = ""
    for i in range(len(data)):
        count = count - 1
        numdata += data[count]
    return int(numdata,16)

#섹터번호, 오프셋을 이용하여 RAW 데이터를 추출하는 함수
def getRawDataByOffset(sectornum,start,end):
    end = end+1
    count = 0
    sector_data = []
    for i in range(int(len(sector[sectornum]) / 2)):
        sector_data.append(sector[sectornum][count:count + 2])
        count += 2
    data = "".join(sector_data[start:end])
    return data

def hexstrToUnicode(hexstr):
    count=0
    newstring=""
    for i in range(int(len(hexstr)/4)):
        a=hexstr[count:count+2]
        b=hexstr[count+2:count+4]
        unicode = chr(int(b+a,16))
        newstring = newstring + unicode
        count+=4
    return newstring

#Directory Entry를 얻어오는 함수
def getDirectoryEntry(cluster):
    dirEntryList = []
    usingSector = dataAreaStartSector+sectorsPerCluster * (cluster-2)
    lfn_info=[]
    for i in range(8):
        count = 0
        for k in range(int(sector_size / 32)):
            #LFN처리
            if (getRawDataByOffset(usingSector, count + 11, count + 11) == "0f"):
                filename = getRawDataByOffset(usingSector, count + 1,
                                              count + 10) + getRawDataByOffset(
                    usingSector, count + 14, count + 25) + getRawDataByOffset(usingSector,
                                                                                    count + 28,
                                                                                    count + 31)
                lfn_num=int(getRawDataByOffset(usingSector, count, count),16)
                lfn_info.append({"num":int(lfn_num), "filename": filename})

            else:
                #LFN을 사용하는 SFN 처리
                if ("7e31" in getRawDataByOffset(usingSector, count , count + 7)):
                    #삭제된 파일의 경우 LFN정렬 방법이 다름
                    if(lfn_info[0]["num"] == 0xE5):
                        data = list(reversed(lfn_info))
                    #LFN에서 획득한 파일명을 조합 => 파일명 추출
                    else:
                        data = sorted(lfn_info, key=itemgetter("num"))
                    lfn_info=[]
                    filename = ""
                    for z in range(len(data)):
                        filename+=data[z]["filename"]
                    filename = hexstrToUnicode(filename)
                    if '\x00' in filename:
                        cutAfterNull = filename.index('\x00')
                        filename = filename[:cutAfterNull]
                    #파일 상태 정보 추출(삭제, 비어있음, 일반)
                    statusbyte = getRawDataByOffset(usingSector, count, count)
                    if(statusbyte=="e5"):
                        status = "deleted"
                    elif(statusbyte=="00"):
                        status = "empty"
                    else:
                        status = "normal"
                    #파일 형태 추출(읽기전용, 숨김, os파일, 볼륨, lfn, dir, 파일)
                    attrbyte = getRawDataByOffset(usingSector, count+11, count+11)
                    if(attrbyte=="01"):
                        filetype = "readonly"
                    elif(attrbyte=="02"):
                        filetype = "hidden"
                    elif(attrbyte=="04"):
                        filetype = "ossystem"
                    elif(attrbyte=="08"):
                        filetype = "volume"
                    elif(attrbyte=="0f"):
                        filetype = "lfn"
                    elif(attrbyte=="10"):
                        filetype = "dir"
                    elif(attrbyte=="20"):
                        filetype = "file"
                    else:
                        filetype = ""
                    #클러스터 번호 추출
                    highcluster = getRawDataByOffset(usingSector, count+20, count+21)
                    lowcluster = getRawDataByOffset(usingSector, count+26, count+27)
                    makecluster = lowcluster+highcluster
                    filecluster = ""
                    a=6
                    for m in range(4):
                        filecluster += makecluster[a:a+2]
                        a -= 2
                    filecluster = int(filecluster,16)
                    # 생성시각
                    createTimeRaw = getRawDataByOffset(usingSector, count + 14, count + 15)
                    createTimeRaw = [createTimeRaw[2], createTimeRaw[3], createTimeRaw[0], createTimeRaw[1]]
                    binTime = ""
                    for craw in createTimeRaw:
                        foo = bin(int(craw,16)).replace("0b","",1)
                        while True:
                            if len(foo) != 4:
                                foo = "0"+foo
                            else:
                                break
                        binTime += foo
                    hour = int(binTime[0:5],2)
                    min = int(binTime[5:11],2)
                    sec = int(binTime[11:16],2)*2
                    createTime = str(hour)+":"+str(min)+":"+str(sec)
                    # 생성날짜
                    createDateRaw = getRawDataByOffset(usingSector, count + 16, count + 17)
                    createDateRaw = [createDateRaw[2], createDateRaw[3], createDateRaw[0], createDateRaw[1]]
                    binDate = ""
                    for cdraw in createDateRaw:
                        bar = bin(int(cdraw, 16)).replace("0b", "", 1)
                        while True:
                            if len(bar) != 4:
                                bar = "0" + bar
                            else:
                                break
                        binDate += bar
                    year = 1980 + int(binDate[0:7], 2)
                    month = int(binDate[7:11], 2)
                    date = int(binDate[11:16], 2)
                    createDate = str(year) + "/" + str(month) + "/" + str(date)
                    # 수정시각
                    lastwTimeRaw = getRawDataByOffset(usingSector, count + 22, count + 23)
                    lastwTimeRaw = [lastwTimeRaw[2], lastwTimeRaw[3], lastwTimeRaw[0], lastwTimeRaw[1]]
                    binlwt = ""
                    for lwtraw in lastwTimeRaw:
                        lfoo = bin(int(lwtraw, 16)).replace("0b", "", 1)
                        while True:
                            if len(lfoo) != 4:
                                lfoo = "0" + lfoo
                            else:
                                break
                        binlwt += lfoo
                    lhour = int(binlwt[0:5], 2)
                    lmin = int(binlwt[5:11], 2)
                    lsec = int(binlwt[11:16], 2) * 2
                    lastWrittenTime = str(lhour) + ":" + str(lmin) + ":" + str(lsec)
                    # 수정날짜
                    lastwDateRaw = getRawDataByOffset(usingSector, count + 24, count + 25)
                    lastwDateRaw = [lastwDateRaw[2], lastwDateRaw[3], lastwDateRaw[0], lastwDateRaw[1]]
                    binlwd = ""
                    for lwdraw in lastwDateRaw:
                        lbar = bin(int(lwdraw, 16)).replace("0b", "", 1)
                        while True:
                            if len(lbar) != 4:
                                lbar = "0" + lbar
                            else:
                                break
                        binlwd += lbar
                    lyear = 1980 + int(binlwd[0:7], 2)
                    lmonth = int(binlwd[7:11], 2)
                    ldate = int(binlwd[11:16], 2)
                    lastWrittenDate = str(lyear) + "/" + str(lmonth) + "/" + str(ldate)
                    #파일크기
                    filesize = getNumbericDataByOffset(usingSector, count+28, count+31)
                    #Volume Type 정리
                    if filecluster == 0:
                        filecluster = filecluster + 2
                    dirEntryList.append({"filename": filename, "status":status, "type":filetype, "cluster":filecluster,
                                         "createtime":createTime, "createdate":createDate,
                                         "lastwrittentime":lastWrittenTime, "lastwrittendate":lastWrittenDate,
                                         "filesize":filesize})

                else:
                    #SFN 처리
                    try:
                        if getRawDataByOffset(usingSector, count, count) == "e5":
                            filename = getAsciiDataByOffset(usingSector, count+1, count + 7)
                        else:
                            filename = getAsciiDataByOffset(usingSector, count, count + 7)
                        if(filename!="\x00\x00\x00\x00\x00\x00\x00\x00"):
                            ext = getAsciiDataByOffset(usingSector, count+8, count+10)
                            if(ext.isspace()!=True):
                                filename = filename + "." + ext
                            filename = filename.replace(" ","")

                            # 파일 상태 정보 추출(삭제, 비어있음, 일반)
                            statusbyte = getRawDataByOffset(usingSector, count, count)
                            if (statusbyte == "e5"):
                                status = "deleted"
                            elif (statusbyte == "00"):
                                status = "empty"
                            else:
                                status = "normal"
                            # 파일 형태 추출(읽기전용, 숨김, os파일, 볼륨, lfn, dir, 파일)
                            attrbyte = getRawDataByOffset(usingSector, count + 11, count + 11)
                            if (attrbyte == "01"):
                                filetype = "readonly"
                            elif (attrbyte == "02"):
                                filetype = "hidden"
                            elif (attrbyte == "04"):
                                filetype = "ossystem"
                            elif (attrbyte == "08"):
                                filetype = "volume"
                            elif (attrbyte == "0f"):
                                filetype = "lfn"
                            elif (attrbyte == "10"):
                                filetype = "dir"
                            elif (attrbyte == "20"):
                                filetype = "file"
                            else:
                                filetype = ""
                            # 클러스터 번호 추출
                            highcluster = getRawDataByOffset(usingSector, count + 20, count + 21)
                            lowcluster = getRawDataByOffset(usingSector, count + 26, count + 27)
                            makecluster = lowcluster + highcluster
                            filecluster = ""
                            a = 6
                            for m in range(4):
                                filecluster += makecluster[a:a + 2]
                                a -= 2
                            filecluster = int(filecluster, 16)
                            # 생성시각
                            createTimeRaw = getRawDataByOffset(usingSector, count + 14, count + 15)
                            createTimeRaw = [createTimeRaw[2], createTimeRaw[3], createTimeRaw[0], createTimeRaw[1]]
                            binTime = ""
                            for craw in createTimeRaw:
                                foo = bin(int(craw, 16)).replace("0b", "", 1)
                                while True:
                                    if len(foo) != 4:
                                        foo = "0" + foo
                                    else:
                                        break
                                binTime += foo
                            hour = int(binTime[0:5], 2)
                            min = int(binTime[5:11], 2)
                            sec = int(binTime[11:16], 2) * 2
                            createTime = str(hour) + ":" + str(min) + ":" + str(sec)
                            # 생성날짜
                            createDateRaw = getRawDataByOffset(usingSector, count + 16, count + 17)
                            createDateRaw = [createDateRaw[2], createDateRaw[3], createDateRaw[0], createDateRaw[1]]
                            binDate = ""
                            for cdraw in createDateRaw:
                                bar = bin(int(cdraw, 16)).replace("0b", "", 1)
                                while True:
                                    if len(bar) != 4:
                                        bar = "0" + bar
                                    else:
                                        break
                                binDate += bar
                            year = 1980 + int(binDate[0:7], 2)
                            month = int(binDate[7:11], 2)
                            date = int(binDate[11:16], 2)
                            createDate = str(year) + "/" + str(month) + "/" + str(date)
                            # 수정시각
                            lastwTimeRaw = getRawDataByOffset(usingSector, count + 22, count + 23)
                            lastwTimeRaw = [lastwTimeRaw[2], lastwTimeRaw[3], lastwTimeRaw[0], lastwTimeRaw[1]]
                            binlwt = ""
                            for lwtraw in lastwTimeRaw:
                                lfoo = bin(int(lwtraw, 16)).replace("0b", "", 1)
                                while True:
                                    if len(lfoo) != 4:
                                        lfoo = "0" + lfoo
                                    else:
                                        break
                                binlwt += lfoo
                            lhour = int(binlwt[0:5], 2)
                            lmin = int(binlwt[5:11], 2)
                            lsec = int(binlwt[11:16], 2) * 2
                            lastWrittenTime = str(lhour) + ":" + str(lmin) + ":" + str(lsec)
                            # 수정날짜
                            lastwDateRaw = getRawDataByOffset(usingSector, count + 24, count + 25)
                            lastwDateRaw = [lastwDateRaw[2], lastwDateRaw[3], lastwDateRaw[0], lastwDateRaw[1]]
                            binlwd = ""
                            for lwdraw in lastwDateRaw:
                                lbar = bin(int(lwdraw, 16)).replace("0b", "", 1)
                                while True:
                                    if len(lbar) != 4:
                                        lbar = "0" + lbar
                                    else:
                                        break
                                binlwd += lbar
                            lyear = 1980 + int(binlwd[0:7], 2)
                            lmonth = int(binlwd[7:11], 2)
                            ldate = int(binlwd[11:16], 2)
                            lastWrittenDate = str(lyear) + "/" + str(lmonth) + "/" + str(ldate)
                            #파일 크기
                            filesize = getNumbericDataByOffset(usingSector, count + 28, count + 31)
                            # Volume Type 정리
                            if filecluster == 0:
                                filecluster = filecluster + 2
                            dirEntryList.append(
                                {"filename": filename, "status": status, "type": filetype, "cluster": filecluster,
                                 "createtime": createTime, "createdate": createDate,
                                 "lastwrittentime": lastWrittenTime, "lastwrittendate": lastWrittenDate,
                                 "filesize": filesize})

                    #한글로된 파일명의 경우 처리
                    except UnicodeDecodeError:
                        if "7e31" in getRawDataByOffset(usingSector, count , count + 7):
                            filename = getRawDataByOffset(usingSector, count + 1,
                                                          count + 10) + getRawDataByOffset(
                                usingSector, count + 14, count + 25) + getRawDataByOffset(usingSector,
                                                                                          count + 28,
                                                                                          count + 31)
                            lfn_num = int(getRawDataByOffset(usingSector, count, count), 16)
                            lfn_info.append({"num": int(lfn_num), "filename": filename})
                        if (lfn_info[0]["num"] == 0xE5):
                            data = list(reversed(lfn_info))
                        else:
                            data = sorted(lfn_info, key=itemgetter("num"))
                        lfn_info = []
                        filename = ""
                        for z in range(len(data)):
                            filename += data[z]["filename"]
                        filename = hexstrToUnicode(filename)
                        if '\x00' in filename:
                            cutAfterNull = filename.index('\x00')
                            filename = filename[:cutAfterNull]

                        # 파일 상태 정보 추출(삭제, 비어있음, 일반)
                        statusbyte = getRawDataByOffset(usingSector, count, count)
                        if (statusbyte == "e5"):
                            status = "deleted"
                        elif (statusbyte == "00"):
                            status = "empty"
                        else:
                            status = "normal"
                        # 파일 형태 추출(읽기전용, 숨김, os파일, 볼륨, lfn, dir, 파일)
                        attrbyte = getRawDataByOffset(usingSector, count + 11, count + 11)
                        if (attrbyte == "01"):
                            filetype = "readonly"
                        elif (attrbyte == "02"):
                            filetype = "hidden"
                        elif (attrbyte == "04"):
                            filetype = "ossystem"
                        elif (attrbyte == "08"):
                            filetype = "volume"
                        elif (attrbyte == "0f"):
                            filetype = "lfn"
                        elif (attrbyte == "10"):
                            filetype = "dir"
                        elif (attrbyte == "20"):
                            filetype = "file"
                        else:
                            filetype = ""
                        # 클러스터 번호 추출
                        highcluster = getRawDataByOffset(usingSector, count + 20, count + 21)
                        lowcluster = getRawDataByOffset(usingSector, count + 26, count + 27)
                        makecluster = lowcluster + highcluster
                        filecluster = ""
                        a = 6
                        for m in range(4):
                            filecluster += makecluster[a:a + 2]
                            a -= 2
                        filecluster = int(filecluster, 16)
                        # 생성시각
                        createTimeRaw = getRawDataByOffset(usingSector, count + 14, count + 15)
                        createTimeRaw = [createTimeRaw[2], createTimeRaw[3], createTimeRaw[0], createTimeRaw[1]]
                        binTime = ""
                        for craw in createTimeRaw:
                            foo = bin(int(craw, 16)).replace("0b", "", 1)
                            while True:
                                if len(foo) != 4:
                                    foo = "0" + foo
                                else:
                                    break
                            binTime += foo
                        hour = int(binTime[0:5], 2)
                        min = int(binTime[5:11], 2)
                        sec = int(binTime[11:16], 2) * 2
                        createTime = str(hour) + ":" + str(min) + ":" + str(sec)
                        # 생성날짜
                        createDateRaw = getRawDataByOffset(usingSector, count + 16, count + 17)
                        createDateRaw = [createDateRaw[2], createDateRaw[3], createDateRaw[0], createDateRaw[1]]
                        binDate = ""
                        for cdraw in createDateRaw:
                            bar = bin(int(cdraw, 16)).replace("0b", "", 1)
                            while True:
                                if len(bar) != 4:
                                    bar = "0" + bar
                                else:
                                    break
                            binDate += bar
                        year = 1980 + int(binDate[0:7], 2)
                        month = int(binDate[7:11], 2)
                        date = int(binDate[11:16], 2)
                        createDate = str(year) + "/" + str(month) + "/" + str(date)
                        # 수정시각
                        lastwTimeRaw = getRawDataByOffset(usingSector, count + 22, count + 23)
                        lastwTimeRaw = [lastwTimeRaw[2], lastwTimeRaw[3], lastwTimeRaw[0], lastwTimeRaw[1]]
                        binlwt = ""
                        for lwtraw in lastwTimeRaw:
                            lfoo = bin(int(lwtraw, 16)).replace("0b", "", 1)
                            while True:
                                if len(lfoo) != 4:
                                    lfoo = "0" + lfoo
                                else:
                                    break
                            binlwt += lfoo
                        lhour = int(binlwt[0:5], 2)
                        lmin = int(binlwt[5:11], 2)
                        lsec = int(binlwt[11:16], 2) * 2
                        lastWrittenTime = str(lhour) + ":" + str(lmin) + ":" + str(lsec)
                        # 수정날짜
                        lastwDateRaw = getRawDataByOffset(usingSector, count + 24, count + 25)
                        lastwDateRaw = [lastwDateRaw[2], lastwDateRaw[3], lastwDateRaw[0], lastwDateRaw[1]]
                        binlwd = ""
                        for lwdraw in lastwDateRaw:
                            lbar = bin(int(lwdraw, 16)).replace("0b", "", 1)
                            while True:
                                if len(lbar) != 4:
                                    lbar = "0" + lbar
                                else:
                                    break
                            binlwd += lbar
                        lyear = 1980 + int(binlwd[0:7], 2)
                        lmonth = int(binlwd[7:11], 2)
                        ldate = int(binlwd[11:16], 2)
                        lastWrittenDate = str(lyear) + "/" + str(lmonth) + "/" + str(ldate)
                        #파일 크기
                        filesize = getNumbericDataByOffset(usingSector, count + 28, count + 31)
                        # Volume Type 정리
                        if filecluster == 0:
                            filecluster = filecluster + 2
                        dirEntryList.append(
                            {"filename": filename, "status": status, "type": filetype, "cluster": filecluster,
                             "createtime": createTime, "createdate": createDate,
                             "lastwrittentime": lastWrittenTime, "lastwrittendate": lastWrittenDate,
                             "filesize": filesize})

            count += 32
        usingSector+=1
    return dirEntryList


def fileCarve(filename, startCluster, fileType, fileSize):
    filename = "./carved/"+filename
    #Do not try carve if it is not a file
    if fileType != "file":
        print("Error: Not a File type. Type: "+fileType)
        exit()
    startSector = dataAreaStartSector + sectorsPerCluster * (startCluster-2)
    firstclusterdata = fatArea[startCluster]
    clusterlist = [startCluster]
    if firstclusterdata == "ffffff0f":
        pass
    else:
        nextcluster = fatArea[startCluster]
        while True:
            if nextcluster == "ffffff0f":
                break
            else:
                clusterlist.append(int.from_bytes(binascii.unhexlify(nextcluster), byteorder='little'))
                nextcluster = fatArea[int.from_bytes(binascii.unhexlify(nextcluster), byteorder='little')]
    carveData = ""
    count=0
    for carvingCluster in clusterlist:
        for i in range(sectorsPerCluster):
            count+=1
            carvingSector = dataAreaStartSector + sectorsPerCluster * (carvingCluster-2)
            carvingSector = carvingSector+i
            carveData+=getRawDataByOffset(carvingSector,0,sector_size)
    carveData = bytearray.fromhex(carveData)
    carveData = carveData[0:fileSize]
    f=open(filename, "wb")
    f.write(carveData)
    f.close()

def findDictIndexByClusterAndSize(dictlist, searchCluster, filesize):
    for dict in dictlist:
        if dict['cluster'] == searchCluster and dict['filesize'] == int(filesize):
            return dictlist.index(dict)

def autoCarveByCluster(dictlist, searchCluster, size):
    listIndex = findDictIndexByClusterAndSize(dictlist, searchCluster, size)
    carveDict = dictlist[listIndex]
    filename = carveDict["filename"]
    startCluster = carveDict["cluster"]
    fileType = carveDict['type']
    fileSize = carveDict['filesize']
    if fileType != "file":
        return "Error"
    fileCarve(filename, startCluster, fileType, fileSize)
    return filename