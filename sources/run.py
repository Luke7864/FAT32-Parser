from flask import *
from werkzeug.utils import secure_filename
from fat32_lib.parser import *
import os
import shutil


app = Flask(__name__)
nowdir = os.getcwd()

@app.route("/", methods=["GET"])
def home():
    return render_template("upload.html")

@app.route("/upload", methods=["POST"])
def upload_imgfile():
    f = request.files['file']
    global filename
    filename = secure_filename(f.filename)
    f.save(nowdir + "/uploaded/"+filename)
    return redirect("/parse")

@app.route("/parse", methods=["GET"])
def parse():
    sector_size = 512
    getSector(sector_size, nowdir + "/uploaded/"+filename)

    # Reserved Area
    global OEM, reservedSector, sectorsPerCluster, FAT_Tables, mediaType, totalSector, fatAreaSize
    global rootDirectoryClusterOffset, fsinfoOffset, backupBootSector, volumeSerialNumber, volumeLabel, fileSystemType
    OEM = getAsciiDataByOffset(0, 3, 10)  # 이미지의 OEM 정보를 가져옵니다.
    reservedSector = getNumbericDataByOffset(0, 14, 15)  # 예약된 섹터 수
    sectorsPerCluster = getNumbericDataByOffset(0, 13, 13)  # 1클러스터 당 섹터 수 보통 8
    FAT_Tables = getNumbericDataByOffset(0, 16, 16)  # FAT 테이블 수 보통 2개
    mediaType = getRawDataByOffset(0, 21, 21)  # f8이면 fixed disk, 아니면 removable
    totalSector = getNumbericDataByOffset(0, 32, 35)  # 전체 섹터 수
    fatAreaSize = getNumbericDataByOffset(0, 36, 39)  # FAT32의 1개 FAT 영역 섹터 수
    rootDirectoryClusterOffset = getNumbericDataByOffset(0, 44, 47)  # 루트 디렉토리가 속한 클러스터
    fsinfoOffset = getNumbericDataByOffset(0, 48, 49)  # FSINFO가 기록되어있는 위치 오프셋
    backupBootSector = getNumbericDataByOffset(0, 50, 51)  # 부트섹터의 백업이 있는 섹터 보통 0x06
    volumeSerialNumber = getRawDataByOffset(0, 67, 70)  # 볼륨 시리얼 넘버
    volumeLabel = getAsciiDataByOffset(0, 71, 81)  # 볼륨 라벨명
    fileSystemType = getAsciiDataByOffset(0, 82, 89)  # 파일시스템 종류, FAT32 파서이므로 FAT32여야 함

    # FSINFO
    global numberOfFreeCluster, leftsize_byte
    numberOfFreeCluster = getNumbericDataByOffset(fsinfoOffset, 488, 491)  # 사용가능한 클러스터 수(빈 클러스터)
    leftsize_byte = numberOfFreeCluster * sectorsPerCluster * sector_size  # 사용 가능한 용량 바이트

    # FAT Area
    # FAT 영역 LIST로 구현
    global fatArea
    fatArea = []
    for i in range(reservedSector, reservedSector + fatAreaSize):
        count = 0
        for k in range(int(sector_size / 4)):
            fatArea.append(getRawDataByOffset(i, count, count + 3))
            count += 4

    # DATA AREA
    global dataAreaStartSector, dataAreaSectors
    dataAreaStartSector = reservedSector + (fatAreaSize * FAT_Tables)  # 데이터 영역 시작 섹터
    dataAreaSectors = totalSector + 1 - dataAreaStartSector

    reciveDiskinfo(dataAreaStartSector, sectorsPerCluster, fatArea)
    return "<script>alert('Successfly Uploaded and Parsed.'); window.location.href = '/search';</script>"

@app.route("/search", methods=["GET"])
def search():
    requested_cluster = request.args.get('cluster')
    global DirEntry
    if requested_cluster == None or requested_cluster.isdigit() == False:
        DirEntry = getDirectoryEntry(rootDirectoryClusterOffset)
    else:
        DirEntry = getDirectoryEntry(int(requested_cluster))
    diskinfo = [OEM, reservedSector, sectorsPerCluster, FAT_Tables, mediaType, totalSector,
                fatAreaSize, rootDirectoryClusterOffset, fsinfoOffset, backupBootSector, volumeSerialNumber,
                volumeLabel, fileSystemType]
    return render_template("table.html", DirEntry=DirEntry, diskinfo=diskinfo)

@app.route("/carve", methods=["GET"])
def carve():
    os.chmod("./carved",700)
    shutil.rmtree('./carved/*', ignore_errors=True)
    requested_cluster = request.args.get('cluster')
    requested_size = request.args.get('size')
    requested_type = request.args.get('type')
    if requested_type != "file":
        return redirect("/search?cluster="+requested_cluster)
    try:
        DirEntry
    except:
        return "<script>alert('You should use Search function before carve the file');</script>"
    if requested_cluster.isdigit() == False:
        return "<script>alert('Error: Prohibited param type');</script>"
    else:
        requested_cluster = int(requested_cluster)
    carved_file = autoCarveByCluster(DirEntry, requested_cluster, requested_size)
    if carved_file == "Error":
        return "Error: Not a File Type!"
    else:
        return send_file("./carved/"+carved_file, as_attachment=True)

@app.route("/delete", methods=["GET"])
def delete():
    os.chmod("./carved",700)
    os.chmod("./uploaded",700)
    shutil.rmtree('./carved', ignore_errors=True)
    shutil.rmtree('./uploaded', ignore_errors=True)
    os.mkdir("./carved")
    os.mkdir("./uploaded")
    return "<script>alert('All of Your Disk Img and Cache Data Removed'); window.location.href = '/';</script>"

if __name__ == '__main__':
    app.run(port=8080, debug=False)