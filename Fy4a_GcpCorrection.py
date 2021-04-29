import os
import sys
from numpy import deg2rad, rad2deg, arctan, sqrt, cos, sin
from osgeo import gdal, osr
from base import GetFileName


# 各分辨率文件包含的通道号
CONTENTS = {'0500M': (2,),
            '1000M': (1, 2, 3),
            '2000M': tuple([x for x in range(1, 8)]),
            '4000M': tuple([x for x in range(1, 15)])}
# 各分辨率全圆盘数据的行列数
SIZES = {'0500M': 21984,
         '1000M': 10992,
         '2000M': 5496,
         '4000M': 2748}
# 列偏移
COFF = {"0500M": 10991.5,
        "1000M": 5495.5,
        "2000M": 2747.5,
        "4000M": 1373.5}
# 列比例因子
CFAC = {"0500M": 81865099,
        "1000M": 40932549,
        "2000M": 20466274,
        "4000M": 10233137}
LOFF = COFF  # 行偏移
LFAC = CFAC  # 行比例因子
ea = 6378.137  # 地球的半长轴[km]
eb = 6356.7523  # 地球的短半轴[km]
h = 42164  # 地心到卫星质心的距离[km]
λD = deg2rad(104.7)  # 卫星星下点所在经度

# 从文件名获取分辨率
def get_resolution(filename):
    resolution = filename[-15:-10]
    print('影像分辨率为{0}:'.format(resolution))
    return resolution

# 从分辨率获取行列数
def getsize(resolution):
    a = SIZES[resolution]
    print('行列数为{0}:'.format(a))
    return a

# 从分辨率获取目标通道号
def getlayers(resolution):
    b = CONTENTS[resolution]
    return b

# 按分辨率作行列号与经纬度转换
def linecolumn2latlon(line, column, resolution):
    """
    (line, column) → (lat, lon)
    resolution：文件名中的分辨率{'0500M', '1000M', '2000M', '4000M'}
    """
    # Step1.求x,y
    x = deg2rad((column - COFF[resolution]) / (2**-16 * CFAC[resolution]))
    y = deg2rad((line - LOFF[resolution]) / (2**-16 * LFAC[resolution]))
    # Step2.求sd,sn,s1,s2,s3,sxy
    cosx = cos(x)
    cosy = cos(y)
    siny = sin(y)
    cos2y = cosy**2
    hcosxcosy = h * cosx * cosy
    cos2y_ea_eb_siny_2 = cos2y + (ea / eb * siny)**2
    sd = sqrt(hcosxcosy**2 - cos2y_ea_eb_siny_2 * (h**2 - ea**2))
    sn = (hcosxcosy - sd) / cos2y_ea_eb_siny_2
    s1 = h - sn * cosx * cosy
    s2 = sn * sin(x) * cosy
    s3 = -sn * siny
    sxy = sqrt(s1**2 + s2**2)
    # Step3.求lon,lat
    lon = rad2deg(arctan(s2 / s1) + λD)
    lat = rad2deg(arctan(ea**2 / eb**2 * s3 / sxy))
    return lat, lon

# 按分辨率与行列数构建校正点列表
def creatGCP(resolution, size):
    # 新建列表用于存储校正点数据
    list = []
    # radius为圆盘半径
    radius = int(size/2)
    print('全圆盘图半径为{0}:'.format(radius))
    # 一种均匀取值的算法，感谢数学博士老邹提供思路
    #即将外接正方形平分为需要取值的数量级，如100个，
    #计算圆内会有多少个，能够满足需求的话，即确定
    #取值步长，而且循环即可。
    for i in range(1, 11):
        for j in range(1, 11):
            a, b = i * (size/10), j * (size/10)
            # 为防止取点超出圆盘范围，根据勾股定理设置取值点距离圆心小于半径
            if (a-radius)**2 + (b-radius)**2 < radius**2:
                lat, lon = linecolumn2latlon(a, b, resolution)
                list.append(gdal.GCP(lon, lat, 0, b, a))
    print('生成校正点{0}个:'.format(len(list)))
    # for x in list:
    #     print(x)
    return list

# 对fy4全圆盘进行地理校正
def hdf2GeoedTif(hdf):
    resolution = get_resolution(hdf)
    size = getsize(resolution)
    layer = getlayers(resolution)
    # 设置空间参考
    sr = osr.SpatialReference()
    sr.ImportFromEPSG(4326)
    # 创建数据集
    # driver = gdal.GetDriverByName("GTiff")
    # dataset = driver.Create('test.tif', size, size, len(layer), gdal.GDT_UInt16)
    # 生成校正点列表
    gcplist = creatGCP(resolution, size)
    # 读取需要的数据子集
    fy4aSet = gdal.Open(hdf)
    subDataSets = fy4aSet.GetSubDatasets()[layer[0]:(layer[-1]+1)]
    outfile = hdf[0:-10]
    # 设置文件名下标起始
    i = 1
    for subDataSet in subDataSets:
        rasterdataset = gdal.Open(subDataSet[0])
        rasterdataset.SetGCPs(gcplist, sr.ExportToWkt())
        print("开始校正" + subDataSet[0])

        dst_ds = gdal.Warp(outfolder + '\\' + outfile + "_band" + str(i) + ".tif", rasterdataset, format='GTiff',
                           polynomialOrder=2, width=2748, height=2748, dstNodata=65535, srcNodata=65535,
                           resampleAlg=gdal.GRIORA_Bilinear, outputType=gdal.GDT_UInt16)
        print('校正完毕！')
        i = i+1



    # del dataset, subDataSets
    del fy4aSet, subDataSets, gcplist


def fy4a_readfiles(infolder):
    originfiles = GetFileName(infolder, ".HDF")
    for file in originfiles:
        hdf2GeoedTif(file)

if __name__ == '__main__':
    # script_path = os.path.split(os.path.realpath(__file__))[0]
    # infolder, outfolder = r"D:\2021\Fy4a", r"D:\testout"
    try:
        infolder, outfolder = sys.argv[1:3]
        os.chdir(infolder)
        fy4a_readfiles(infolder)

    except Exception as e:
        print(sys.argv)
        print(e)
