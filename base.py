import os
from osgeo import gdal, ogr
import numpy as np


def MeanDEM(pointUL, pointDR):

    '''
    计算影像所在区域的平均高程.
    UL=up left point
    DR=down right point
    '''


    script_path = os.path.split(os.path.realpath(__file__))[0]
    dem_path = os.path.join(script_path, "GMTED2km.tif")

    try:
        demDataSet = gdal.Open(dem_path)
    except Exception as e:
        pass

    DEMBand = demDataSet.GetRasterBand(1)
    geotransform = demDataSet.GetGeoTransform()
    # DEM分辨率
    pixelWidth = geotransform[1]
    pixelHight = geotransform[5]

    # DEM起始点：左上角，X：经度，Y：纬度
    originX = geotransform[0]
    originY = geotransform[3]

    # 研究区左上角在DEM矩阵中的位置
    yoffset1 = int((originY - pointUL['lat']) / pixelWidth)
    xoffset1 = int((pointUL['lon'] - originX) / (-pixelHight))

    # 研究区右下角在DEM矩阵中的位置
    yoffset2 = int((originY - pointDR['lat']) / pixelWidth)
    xoffset2 = int((pointDR['lon'] - originX) / (-pixelHight))

    # 研究区矩阵行列数
    xx = xoffset2 - xoffset1
    yy = yoffset2 - yoffset1

    # 读取研究区内的数据，并计算高程
    DEMRasterData = DEMBand.ReadAsArray(xoffset1, yoffset1, xx, yy)

    MeanAltitude = np.mean(DEMRasterData)
    return MeanAltitude

def shpClipRaster(InputImage, Shapefile, RasterFormat, VectorFormat, OutTileName):
    '''
    用给定的矢量裁剪指定的栅格数据
    OutTileName就是裁剪后的栅格数据
    '''

    Raster = gdal.Open(InputImage, gdal.GA_ReadOnly)
    Projection = Raster.GetProjectionRef()
    # 打开矢量数据
    VectorDriver = ogr.GetDriverByName(VectorFormat)
    VectorDataset = VectorDriver.Open(Shapefile, 0)
    layer = VectorDataset.GetLayer()
    # 获取特征要素的外边界(Extent)
    feature = layer.GetFeature(0)
    geom = feature.GetGeometryRef()
    minX, maxX, minY, maxY = geom.GetEnvelope()

    # 这个裁剪后矢量外边界(Extent)数据仍然在
    # OutTile = gdal.Warp(OutTileName, Raster, format=RasterFormat,
    #                     outputBounds=[minX, minY, maxX, maxY],
    #                     dstSRS=Projection,  dstNodata=-9999,
    #                     cutlineLayer=layer, cropToCutline=True)
    # 这个裁剪结果按照矢量形状生成
    OutTile = gdal.Warp(OutTileName, Raster, format=RasterFormat, cutlineDSName=Shapefile,
                        dstSRS=Projection, dstNodata=-9999,
                        cropToCutline=True, outputBounds=[minX, minY, maxX, maxY])
    OutTile = None
    Raster = None
    VectorDataset.Destroy()


def GetFileName(fileInpath,fileType):
    '''
    获取给定目录下给定文件类型的名称列表
    并返回给调用变量
    '''
    #自定义函数获取hdf文件名，排除其它文件类型如hdr等干扰
    fileNames = os.listdir(fileInpath)#os.listdir函数获取fileinpath下所有文件名存入filenames
    fileNameArr = []
    for fileName in fileNames:
        if os.path.splitext(fileName)[1] == fileType:
            fileNameArr.append(fileName)#将扩展名与预定义相同的文件名存入filenamearr数组
    return fileNameArr#并将filenamearr返回给调用者

def printHDFinfo(hdfName):
    '''
    获取给定hdf文件的子数据，元数据信息
    并打印
    '''
    #  gdal打开hdf数据集
    datasets = gdal.Open(hdfName)

    #  获取hdf中的子数据集
    SubDatasets = datasets.GetSubDatasets()
    #  获取子数据集的个数
    SubDatasetsNum = len(datasets.GetSubDatasets())
    #  输出各子数据集的信息
    print("子数据集一共有{0}个: ".format(SubDatasetsNum))
    for i in range(SubDatasetsNum):
        print(SubDatasets[i])

    # #  获取hdf中的元数据
    # Metadata = datasets.GetMetadata()
    # #  获取元数据的个数
    # MetadataNum = len(Metadata)
    # #  输出各子数据集的信息
    # print("元数据一共有{0}个: ".format(MetadataNum))
    # for key, value in Metadata.items():
    #     print('{key}:{value}'.format(key=key, value=value))
    #
    del datasets, SubDatasets#, Metadata



if __name__ == '__main__':
    print("Better to import this script to your code!")
