"""
数据预处理模块
处理真实遥感数据的格式转换、坐标统一、数据裁剪等功能
"""

import os
import sys
import numpy as np
from pathlib import Path
import logging
import json
from datetime import datetime
import tempfile
import shutil

# 设置GDAL错误处理
try:
    from osgeo import gdal, osr
    gdal.UseExceptions()
except ImportError:
    print("GDAL未安装，请先安装GDAL")
    sys.exit(1)

logger = logging.getLogger(__name__)


class DataPreprocessor:
    """数据预处理器"""
    
    def __init__(self, output_dir="preprocessed_data"):
        """
        初始化数据预处理器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp())
        self.metadata = {}
        
    def __del__(self):
        """清理临时文件"""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")
    
    def validate_input_data(self, data_path):
        """
        验证输入数据
        
        Args:
            data_path: 数据文件路径
            
        Returns:
            dict: 验证结果
        """
        try:
            dataset = gdal.Open(str(data_path), gdal.GA_ReadOnly)
            if dataset is None:
                return {
                    'valid': False,
                    'error': f"无法打开文件: {data_path}"
                }
            
            # 获取基本信息
            width = dataset.RasterXSize
            height = dataset.RasterYSize
            band_count = dataset.RasterCount
            geotransform = dataset.GetGeoTransform()
            projection = dataset.GetProjection()
            
            # 检查坐标系统
            srs = osr.SpatialReference()
            srs.ImportFromWkt(projection)
            
            # 检查波段信息
            bands_info = []
            for i in range(1, band_count + 1):
                band = dataset.GetRasterBand(i)
                band_info = {
                    'band_number': i,
                    'description': band.GetDescription(),
                    'data_type': gdal.GetDataTypeName(band.DataType),
                    'no_data_value': band.GetNoDataValue(),
                    'scale': band.GetScale(),
                    'offset': band.GetOffset(),
                    'unit_type': band.GetUnitType()
                }
                bands_info.append(band_info)
            
            dataset = None
            
            validation_result = {
                'valid': True,
                'file_path': str(data_path),
                'width': width,
                'height': height,
                'band_count': band_count,
                'geotransform': geotransform,
                'projection': projection,
                'coordinate_system': srs.GetName(),
                'epsg_code': srs.GetAuthorityCode('PROJCS'),
                'bands_info': bands_info
            }
            
            logger.info(f"数据验证成功: {data_path}")
            logger.info(f"  尺寸: {width}x{height}, 波段数: {band_count}")
            logger.info(f"  坐标系统: {srs.GetName()}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"数据验证失败: {e}")
            return {
                'valid': False,
                'error': str(e)
            }
    
    def convert_coordinate_system(self, input_path, output_path, target_epsg=32650):
        """
        转换坐标系统
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            target_epsg: 目标EPSG代码
            
        Returns:
            bool: 转换是否成功
        """
        try:
            # 打开源数据集
            src_dataset = gdal.Open(str(input_path), gdal.GA_ReadOnly)
            if src_dataset is None:
                raise ValueError(f"无法打开源文件: {input_path}")
            
            # 获取源坐标系统
            src_projection = src_dataset.GetProjection()
            src_srs = osr.SpatialReference()
            src_srs.ImportFromWkt(src_projection)
            
            # 创建目标坐标系统
            dst_srs = osr.SpatialReference()
            dst_srs.ImportFromEPSG(target_epsg)
            
            # 检查是否需要转换
            if src_srs.IsSame(dst_srs):
                logger.info(f"坐标系统相同，无需转换: {target_epsg}")
                # 直接复制文件
                import shutil
                shutil.copy2(input_path, output_path)
                return True
            
            # 执行重投影 - 使用简化的方法
            dst_wkt = dst_srs.ExportToWkt()
            if dst_wkt is None:
                # 尝试使用EPSG代码字符串
                dst_wkt = f"EPSG:{target_epsg}"
                logger.warning(f"WKT导出失败，使用EPSG代码: {dst_wkt}")
            else:
                logger.info(f"目标坐标系统WKT: {dst_wkt[:100]}...")
            
            # 确保所有参数都是字符串类型
            output_path_str = str(output_path)
            dst_wkt_str = str(dst_wkt)
            
            # 使用简化的Warp调用
            result = gdal.Warp(
                output_path_str,
                src_dataset,
                dstSRS=dst_wkt_str,
                resampleAlg=gdal.GRA_Bilinear
            )
            if result is None:
                raise ValueError(f"gdal.Warp失败: {gdal.GetLastErrorMsg()}")
            result = None  # 释放资源
            
            src_dataset = None
            
            # 验证输出文件
            if os.path.exists(output_path):
                # 获取输出文件信息
                dst_dataset = gdal.Open(output_path, gdal.GA_ReadOnly)
                if dst_dataset:
                    width = dst_dataset.RasterXSize
                    height = dst_dataset.RasterYSize
                    dst_dataset = None
                    
                    logger.info(f"坐标系统转换完成: {input_path} -> {output_path}")
                    logger.info(f"  目标EPSG: {target_epsg}")
                    logger.info(f"  目标尺寸: {width}x{height}")
                    return True
                else:
                    logger.error("转换后的文件无法打开")
                    return False
            else:
                logger.error("转换后的文件不存在")
                return False
            
        except Exception as e:
            logger.error(f"坐标系统转换失败: {e}")
            return False
    
    def merge_bands(self, band_files, output_path, band_names=None):
        """
        合并多个单波段文件为多波段文件
        
        Args:
            band_files: 波段文件路径列表
            output_path: 输出文件路径
            band_names: 波段名称列表
            
        Returns:
            bool: 合并是否成功
        """
        try:
            if not band_files:
                raise ValueError("波段文件列表为空")
            
            # 验证所有波段文件
            first_dataset = gdal.Open(str(band_files[0]), gdal.GA_ReadOnly)
            if first_dataset is None:
                raise ValueError(f"无法打开第一个波段文件: {band_files[0]}")
            
            width = first_dataset.RasterXSize
            height = first_dataset.RasterYSize
            data_type = first_dataset.GetRasterBand(1).DataType
            geotransform = first_dataset.GetGeoTransform()
            projection = first_dataset.GetProjection()
            
            first_dataset = None
            
            # 创建输出数据集
            driver = gdal.GetDriverByName('GTiff')
            output_dataset = driver.Create(
                str(output_path),
                width,
                height,
                len(band_files),
                data_type
            )
            
            # 设置地理信息
            output_dataset.SetGeoTransform(geotransform)
            output_dataset.SetProjection(projection)
            
            # 复制波段数据
            for i, band_file in enumerate(band_files):
                band_dataset = gdal.Open(str(band_file), gdal.GA_ReadOnly)
                if band_dataset is None:
                    raise ValueError(f"无法打开波段文件: {band_file}")
                
                # 验证尺寸
                if (band_dataset.RasterXSize != width or 
                    band_dataset.RasterYSize != height):
                    raise ValueError(f"波段文件尺寸不匹配: {band_file}")
                
                # 读取波段数据
                band_data = band_dataset.GetRasterBand(1).ReadAsArray()
                
                # 写入输出数据集
                output_band = output_dataset.GetRasterBand(i + 1)
                output_band.WriteArray(band_data)
                
                # 设置波段描述
                if band_names and i < len(band_names):
                    output_band.SetDescription(band_names[i])
                else:
                    output_band.SetDescription(f"Band_{i+1}")
                
                # 复制元数据
                src_band = band_dataset.GetRasterBand(1)
                if src_band.GetNoDataValue() is not None:
                    output_band.SetNoDataValue(src_band.GetNoDataValue())
                
                # 安全地设置比例和偏移
                try:
                    scale = src_band.GetScale()
                    if scale is not None and scale != 1.0:
                        output_band.SetScale(float(scale))
                except:
                    pass
                
                try:
                    offset = src_band.GetOffset()
                    if offset is not None and offset != 0.0:
                        output_band.SetOffset(float(offset))
                except:
                    pass
                
                band_dataset = None
            
            output_dataset = None
            
            logger.info(f"波段合并完成: {output_path}")
            logger.info(f"  波段数: {len(band_files)}")
            logger.info(f"  尺寸: {width}x{height}")
            
            return True
            
        except Exception as e:
            logger.error(f"波段合并失败: {e}")
            return False
    
    def clip_to_region(self, input_path, output_path, region_bounds):
        """
        裁剪到指定区域
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            region_bounds: 区域边界 [min_x, min_y, max_x, max_y]
            
        Returns:
            bool: 裁剪是否成功
        """
        try:
            # 使用GDAL Warp进行裁剪
            gdal.Warp(
                str(output_path),
                input_path,
                outputBounds=region_bounds,
                cropToCutline=True
            )
            
            logger.info(f"区域裁剪完成: {input_path} -> {output_path}")
            logger.info(f"  裁剪区域: {region_bounds}")
            
            return True
            
        except Exception as e:
            logger.error(f"区域裁剪失败: {e}")
            return False
    
    def resample_data(self, input_path, output_path, target_resolution, resample_method='bilinear'):
        """
        重采样数据到指定分辨率
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            target_resolution: 目标分辨率（米）
            resample_method: 重采样方法
            
        Returns:
            bool: 重采样是否成功
        """
        try:
            # 映射重采样方法
            method_map = {
                'nearest': gdal.GRA_NearestNeighbour,
                'bilinear': gdal.GRA_Bilinear,
                'cubic': gdal.GRA_Cubic,
                'cubic_spline': gdal.GRA_CubicSpline,
                'lanczos': gdal.GRA_Lanczos
            }
            
            resample_alg = method_map.get(resample_method, gdal.GRA_Bilinear)
            
            # 执行重采样
            result = gdal.Warp(
                str(output_path),
                input_path,
                xRes=target_resolution,
                yRes=target_resolution,
                resampleAlg=resample_alg
            )
            if result is None:
                raise ValueError(f"重采样失败: {gdal.GetLastErrorMsg()}")
            result = None  # 释放资源
            
            logger.info(f"数据重采样完成: {input_path} -> {output_path}")
            logger.info(f"  目标分辨率: {target_resolution}米")
            logger.info(f"  重采样方法: {resample_method}")
            
            return True
            
        except Exception as e:
            logger.error(f"数据重采样失败: {e}")
            return False
    
    def process_landsat_data(self, landsat_dir, output_path, target_epsg=32650):
        """
        处理Landsat数据
        
        Args:
            landsat_dir: Landsat数据目录
            output_path: 输出文件路径
            target_epsg: 目标EPSG代码
            
        Returns:
            bool: 处理是否成功
        """
        try:
            landsat_dir = Path(landsat_dir)
            
            # 查找Landsat波段文件
            band_patterns = {
                'B2': '*_SR_B2.TIF',  # 蓝波段
                'B3': '*_SR_B3.TIF',  # 绿波段
                'B4': '*_SR_B4.TIF',  # 红波段
                'B5': '*_SR_B5.TIF',  # 近红外波段
                'B6': '*_SR_B6.TIF',  # 短波红外1
                'B7': '*_SR_B7.TIF'   # 短波红外2
            }
            
            band_files = {}
            for band_name, pattern in band_patterns.items():
                files = list(landsat_dir.glob(pattern))
                if files:
                    band_files[band_name] = str(files[0])
                else:
                    logger.warning(f"未找到{band_name}波段文件")
            
            if not band_files:
                raise ValueError("未找到任何Landsat波段文件")
            
            # 验证所有波段文件
            for band_name, file_path in band_files.items():
                validation = self.validate_input_data(file_path)
                if not validation['valid']:
                    raise ValueError(f"{band_name}波段文件验证失败: {validation['error']}")
            
            # 转换坐标系统
            converted_files = {}
            for band_name, file_path in band_files.items():
                converted_path = self.temp_dir / f"{band_name}_converted.tif"
                if self.convert_coordinate_system(file_path, converted_path, target_epsg):
                    converted_files[band_name] = str(converted_path)
                else:
                    raise ValueError(f"{band_name}波段坐标转换失败")
            
            # 合并波段
            band_order = ['B2', 'B3', 'B4', 'B5', 'B6', 'B7']
            band_paths = [converted_files[band] for band in band_order if band in converted_files]
            band_names = ['Blue', 'Green', 'Red', 'NIR', 'SWIR1', 'SWIR2']
            
            if self.merge_bands(band_paths, output_path, band_names):
                logger.info(f"Landsat数据处理完成: {output_path}")
                return True
            else:
                raise ValueError("波段合并失败")
                
        except Exception as e:
            logger.error(f"Landsat数据处理失败: {e}")
            return False
    
    def process_sentinel_data(self, sentinel_dir, output_path, target_epsg=32650):
        """
        处理Sentinel-2数据
        
        Args:
            sentinel_dir: Sentinel-2数据目录
            output_path: 输出文件路径
            target_epsg: 目标EPSG代码
            
        Returns:
            bool: 处理是否成功
        """
        try:
            sentinel_dir = Path(sentinel_dir)
            
            # 查找Sentinel-2波段文件 - 支持多种命名格式
            band_patterns = {
                'B02': ['*_B02_10m.jp2', '*_B02.jp2'],  # 蓝波段
                'B03': ['*_B03_10m.jp2', '*_B03.jp2'],  # 绿波段
                'B04': ['*_B04_10m.jp2', '*_B04.jp2'],  # 红波段
                'B08': ['*_B08_10m.jp2', '*_B08.jp2'],  # 近红外波段
                'B11': ['*_B11_20m.jp2', '*_B11.jp2'],  # 短波红外1
                'B12': ['*_B12_20m.jp2', '*_B12.jp2']   # 短波红外2
            }
            
            band_files = {}
            for band_name, patterns in band_patterns.items():
                found = False
                for pattern in patterns:
                    files = list(sentinel_dir.glob(pattern))
                    if files:
                        band_files[band_name] = str(files[0])
                        logger.info(f"找到{band_name}波段: {files[0].name}")
                        found = True
                        break
                if not found:
                    logger.warning(f"未找到{band_name}波段文件")
            
            if not band_files:
                raise ValueError("未找到任何Sentinel-2波段文件")
            
            logger.info(f"找到{len(band_files)}个波段文件")
            
            # 验证所有波段文件
            for band_name, file_path in band_files.items():
                logger.info(f"验证{band_name}波段文件...")
                validation = self.validate_input_data(file_path)
                if not validation['valid']:
                    raise ValueError(f"{band_name}波段文件验证失败: {validation['error']}")
                logger.info(f"{band_name}波段验证通过")
            
            # 转换坐标系统
            logger.info("开始坐标系统转换...")
            converted_files = {}
            for band_name, file_path in band_files.items():
                logger.info(f"转换{band_name}波段坐标系统...")
                converted_path = self.temp_dir / f"{band_name}_converted.tif"
                
                success = self.convert_coordinate_system(file_path, converted_path, target_epsg)
                if success and converted_path.exists():
                    converted_files[band_name] = str(converted_path)
                    logger.info(f"{band_name}波段坐标转换成功")
                else:
                    raise ValueError(f"{band_name}波段坐标转换失败")
            
            # 合并波段（跳过重采样，直接使用转换后的文件）
            logger.info("开始波段合并...")
            band_order = ['B02', 'B03', 'B04', 'B08', 'B11', 'B12']
            band_paths = [converted_files[band] for band in band_order if band in converted_files]
            band_names = ['Blue', 'Green', 'Red', 'NIR', 'SWIR1', 'SWIR2']
            
            logger.info(f"准备合并{len(band_paths)}个波段")
            
            success = self.merge_bands(band_paths, output_path, band_names)
            if success and Path(output_path).exists():
                logger.info(f"Sentinel-2数据处理完成: {output_path}")
                
                # 验证输出文件
                validation = self.validate_input_data(output_path)
                if validation['valid']:
                    logger.info(f"输出文件验证通过: {validation['width']}x{validation['height']}, {validation['band_count']}波段")
                    return True
                else:
                    raise ValueError(f"输出文件验证失败: {validation['error']}")
            else:
                raise ValueError("波段合并失败")
                
        except Exception as e:
            logger.error(f"Sentinel-2数据处理失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return False
    
    def process_landuse_data(self, landuse_path, output_path, target_epsg=32650):
        """
        处理土地利用数据
        
        Args:
            landuse_path: 土地利用数据路径
            output_path: 输出文件路径
            target_epsg: 目标EPSG代码
            
        Returns:
            bool: 处理是否成功
        """
        try:
            # 验证输入数据
            validation = self.validate_input_data(landuse_path)
            if not validation['valid']:
                raise ValueError(f"土地利用数据验证失败: {validation['error']}")
            
            # 转换坐标系统
            if self.convert_coordinate_system(landuse_path, output_path, target_epsg):
                logger.info(f"土地利用数据处理完成: {output_path}")
                return True
            else:
                raise ValueError("土地利用数据坐标转换失败")
                
        except Exception as e:
            logger.error(f"土地利用数据处理失败: {e}")
            return False
    
    def create_processing_report(self, output_path="processing_report.json"):
        """
        创建处理报告
        
        Args:
            output_path: 报告文件路径
        """
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'output_directory': str(self.output_dir),
                'metadata': self.metadata,
                'summary': {
                    'total_files_processed': len(self.metadata),
                    'successful_conversions': sum(1 for m in self.metadata.values() if m.get('success', False)),
                    'failed_conversions': sum(1 for m in self.metadata.values() if not m.get('success', False))
                }
            }
            
            report_path = self.output_dir / output_path
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"处理报告已生成: {report_path}")
            
        except Exception as e:
            logger.error(f"创建处理报告失败: {e}")


def main():
    """主函数 - 测试数据预处理功能"""
    import argparse
    
    parser = argparse.ArgumentParser(description='数据预处理工具')
    parser.add_argument('--input-dir', required=True, help='输入数据目录')
    parser.add_argument('--output-dir', default='preprocessed_data', help='输出目录')
    parser.add_argument('--data-type', choices=['landsat', 'sentinel', 'landuse'], required=True, help='数据类型')
    parser.add_argument('--target-epsg', type=int, default=32650, help='目标EPSG代码')
    parser.add_argument('--clip-region', nargs=4, type=float, help='裁剪区域 [min_x, min_y, max_x, max_y]')
    parser.add_argument('--resample-resolution', type=float, help='重采样分辨率（米）')
    
    args = parser.parse_args()
    
    # 创建预处理器
    preprocessor = DataPreprocessor(args.output_dir)
    
    try:
        if args.data_type == 'landsat':
            output_path = Path(args.output_dir) / "landsat_processed.tif"
            success = preprocessor.process_landsat_data(args.input_dir, output_path, args.target_epsg)
        elif args.data_type == 'sentinel':
            output_path = Path(args.output_dir) / "sentinel_processed.tif"
            success = preprocessor.process_sentinel_data(args.input_dir, output_path, args.target_epsg)
        elif args.data_type == 'landuse':
            output_path = Path(args.output_dir) / "landuse_processed.tif"
            success = preprocessor.process_landuse_data(args.input_dir, output_path, args.target_epsg)
        
        if success:
            # 可选的裁剪
            if args.clip_region:
                clipped_path = output_path.parent / f"{output_path.stem}_clipped.tif"
                preprocessor.clip_to_region(output_path, clipped_path, args.clip_region)
                output_path = clipped_path
            
            # 可选的重采样
            if args.resample_resolution:
                resampled_path = output_path.parent / f"{output_path.stem}_resampled.tif"
                preprocessor.resample_data(output_path, resampled_path, args.resample_resolution)
                output_path = resampled_path
            
            print(f"✅ 数据处理完成: {output_path}")
        else:
            print("❌ 数据处理失败")
            return 1
        
        # 生成处理报告
        preprocessor.create_processing_report()
        
        return 0
        
    except Exception as e:
        print(f"❌ 处理过程中发生错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 