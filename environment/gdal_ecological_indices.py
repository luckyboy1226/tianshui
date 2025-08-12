"""
使用GDAL进行遥感生态指数计算
GDAL (Geospatial Data Abstraction Library) 是处理地理空间数据的强大库
"""

import numpy as np
from osgeo import gdal, osr
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from matplotlib.colors import LinearSegmentedColormap
import os
import tempfile
from PIL import Image
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import logging
import json

# 设置GDAL错误处理
gdal.UseExceptions()

logger = logging.getLogger(__name__)


class GDALEcologicalIndexCalculator:
    """基于GDAL的生态指数计算器"""
    
    def __init__(self, image_path):
        """
        初始化GDAL生态指数计算器
        
        Args:
            image_path: 遥感影像文件路径
        """
        self.image_path = image_path
        self.dataset = None
        self.bands = {}
        self.metadata = {}
        self.geotransform = None
        self.projection = None
        
    def load_image(self):
        """使用GDAL加载遥感影像"""
        try:
            # 打开数据集
            self.dataset = gdal.Open(self.image_path, gdal.GA_ReadOnly)
            if self.dataset is None:
                raise ValueError(f"无法打开影像文件: {self.image_path}")
            
            # 获取基本信息
            self.geotransform = self.dataset.GetGeoTransform()
            self.projection = self.dataset.GetProjection()
            
            # 获取影像尺寸
            self.width = self.dataset.RasterXSize
            self.height = self.dataset.RasterYSize
            self.band_count = self.dataset.RasterCount
            
            # 读取所有波段
            for i in range(1, self.band_count + 1):
                band = self.dataset.GetRasterBand(i)
                self.bands[i] = band.ReadAsArray().astype(np.float32)
                
                # 获取波段元数据
                self.metadata[f'band_{i}'] = {
                    'description': band.GetDescription(),
                    'no_data_value': band.GetNoDataValue(),
                    'scale': band.GetScale(),
                    'offset': band.GetOffset(),
                    'unit_type': band.GetUnitType()
                }
            
            logger.info(f"成功加载影像: {self.image_path}")
            logger.info(f"影像尺寸: {self.width} x {self.height}, 波段数: {self.band_count}")
            return True
            
        except Exception as e:
            logger.error(f"加载影像失败: {e}")
            return False
    
    def get_band_info(self):
        """获取波段信息"""
        info = {
            'width': self.width,
            'height': self.height,
            'band_count': self.band_count,
            'geotransform': self.geotransform,
            'projection': self.projection,
            'bands': {}
        }
        
        for band_num, band_data in self.bands.items():
            info['bands'][band_num] = {
                'shape': band_data.shape,
                'dtype': str(band_data.dtype),
                'min': float(np.nanmin(band_data)),
                'max': float(np.nanmax(band_data)),
                'mean': float(np.nanmean(band_data)),
                'std': float(np.nanstd(band_data)),
                'metadata': self.metadata.get(f'band_{band_num}', {})
            }
        
        return info
    
    def calculate_ndvi(self, red_band=3, nir_band=4):
        """
        计算NDVI（归一化植被指数）
        
        Args:
            red_band: 红波段编号
            nir_band: 近红外波段编号
        """
        try:
            if red_band not in self.bands or nir_band not in self.bands:
                raise ValueError(f"波段 {red_band} 或 {nir_band} 不存在")
            
            red = self.bands[red_band]
            nir = self.bands[nir_band]
            
            # 处理无效值
            red_valid = np.isfinite(red)
            nir_valid = np.isfinite(nir)
            valid_mask = red_valid & nir_valid
            
            # 初始化结果数组
            ndvi = np.full(red.shape, np.nan, dtype=np.float32)
            
            # 计算NDVI
            denominator = nir + red
            valid_denominator = denominator[valid_mask]
            
            # 避免除零错误
            valid_denominator[valid_denominator == 0] = 1e-10
            
            ndvi[valid_mask] = (nir[valid_mask] - red[valid_mask]) / valid_denominator
            
            # 限制值范围
            ndvi = np.clip(ndvi, -1, 1)
            
            logger.info("NDVI计算完成")
            return ndvi
            
        except Exception as e:
            logger.error(f"计算NDVI失败: {e}")
            return None
    
    def calculate_ndwi(self, green_band=2, nir_band=4):
        """
        计算NDWI（归一化水体指数）
        
        Args:
            green_band: 绿波段编号
            nir_band: 近红外波段编号
        """
        try:
            if green_band not in self.bands or nir_band not in self.bands:
                raise ValueError(f"波段 {green_band} 或 {nir_band} 不存在")
            
            green = self.bands[green_band]
            nir = self.bands[nir_band]
            
            # 处理无效值
            green_valid = np.isfinite(green)
            nir_valid = np.isfinite(nir)
            valid_mask = green_valid & nir_valid
            
            # 初始化结果数组
            ndwi = np.full(green.shape, np.nan, dtype=np.float32)
            
            # 计算NDWI
            denominator = green + nir
            valid_denominator = denominator[valid_mask]
            
            # 避免除零错误
            valid_denominator[valid_denominator == 0] = 1e-10
            
            ndwi[valid_mask] = (green[valid_mask] - nir[valid_mask]) / valid_denominator
            
            # 限制值范围
            ndwi = np.clip(ndwi, -1, 1)
            
            logger.info("NDWI计算完成")
            return ndwi
            
        except Exception as e:
            logger.error(f"计算NDWI失败: {e}")
            return None
    
    def calculate_ndbi(self, nir_band=4, swir_band=5):
        """
        计算NDBI（归一化建筑指数）
        
        Args:
            nir_band: 近红外波段编号
            swir_band: 短波红外波段编号
        """
        try:
            if nir_band not in self.bands or swir_band not in self.bands:
                raise ValueError(f"波段 {nir_band} 或 {swir_band} 不存在")
            
            nir = self.bands[nir_band]
            swir = self.bands[swir_band]
            
            # 处理无效值
            nir_valid = np.isfinite(nir)
            swir_valid = np.isfinite(swir)
            valid_mask = nir_valid & swir_valid
            
            # 初始化结果数组
            ndbi = np.full(nir.shape, np.nan, dtype=np.float32)
            
            # 计算NDBI
            denominator = nir + swir
            valid_denominator = denominator[valid_mask]
            
            # 避免除零错误
            valid_denominator[valid_denominator == 0] = 1e-10
            
            ndbi[valid_mask] = (swir[valid_mask] - nir[valid_mask]) / valid_denominator
            
            # 限制值范围
            ndbi = np.clip(ndbi, -1, 1)
            
            logger.info("NDBI计算完成")
            return ndbi
            
        except Exception as e:
            logger.error(f"计算NDBI失败: {e}")
            return None
    
    def calculate_ndsi(self, green_band=2, swir_band=5):
        """
        计算NDSI（归一化积雪指数）
        
        Args:
            green_band: 绿波段编号
            swir_band: 短波红外波段编号
        """
        try:
            if green_band not in self.bands or swir_band not in self.bands:
                raise ValueError(f"波段 {green_band} 或 {swir_band} 不存在")
            
            green = self.bands[green_band]
            swir = self.bands[swir_band]
            
            # 处理无效值
            green_valid = np.isfinite(green)
            swir_valid = np.isfinite(swir)
            valid_mask = green_valid & swir_valid
            
            # 初始化结果数组
            ndsi = np.full(green.shape, np.nan, dtype=np.float32)
            
            # 计算NDSI
            denominator = green + swir
            valid_denominator = denominator[valid_mask]
            
            # 避免除零错误
            valid_denominator[valid_denominator == 0] = 1e-10
            
            ndsi[valid_mask] = (green[valid_mask] - swir[valid_mask]) / valid_denominator
            
            # 限制值范围
            ndsi = np.clip(ndsi, -1, 1)
            
            logger.info("NDSI计算完成")
            return ndsi
            
        except Exception as e:
            logger.error(f"计算NDSI失败: {e}")
            return None
    
    def calculate_tasseled_cap(self):
        """
        计算缨帽变换（Tasseled Cap Transformation）
        用于提取绿度、亮度、湿度等特征
        """
        try:
            # Landsat 8 缨帽变换系数
            # 假设波段顺序：Blue, Green, Red, NIR, SWIR1, SWIR2
            tc_coefficients = {
                'brightness': [0.3029, 0.2786, 0.4733, 0.5599, 0.5080, 0.1872],
                'greenness': [-0.2941, -0.2430, -0.5424, 0.7276, 0.0713, -0.1608],
                'wetness': [0.1511, 0.1973, 0.3283, 0.3407, -0.7117, -0.4559],
                'fourth': [-0.8239, 0.0849, 0.4396, -0.0580, 0.2013, -0.2773],
                'fifth': [-0.3294, 0.0557, 0.1056, 0.1855, -0.4349, 0.8085],
                'sixth': [0.1079, -0.9023, 0.4119, 0.0575, -0.0259, 0.0252]
            }
            
            # 准备波段数据
            band_data = []
            for i in range(1, min(7, self.band_count + 1)):  # 最多6个波段
                band_data.append(self.bands[i].flatten())
            
            band_matrix = np.column_stack(band_data)
            
            # 计算缨帽变换
            tc_results = {}
            for component, coefficients in tc_coefficients.items():
                if len(coefficients) <= len(band_data):
                    # 只使用可用的波段
                    coef_array = np.array(coefficients[:len(band_data)])
                    tc_value = np.dot(band_matrix, coef_array)
                    tc_results[component] = tc_value.reshape(self.height, self.width)
            
            logger.info("缨帽变换计算完成")
            return tc_results
            
        except Exception as e:
            logger.error(f"计算缨帽变换失败: {e}")
            return None
    
    def calculate_rsei(self):
        """
        计算RSEI（遥感生态指数）
        基于主成分分析的综合生态指数
        """
        try:
            # 计算四个基础指数
            tc_results = self.calculate_tasseled_cap()
            if tc_results is None:
                raise ValueError("无法计算缨帽变换")
            
            # 提取四个分量
            greenness = tc_results.get('greenness', None)
            wetness = tc_results.get('wetness', None)
            brightness = tc_results.get('brightness', None)  # 作为干度指数
            fourth = tc_results.get('fourth', None)  # 作为热度指数
            
            if any(x is None for x in [greenness, wetness, brightness, fourth]):
                raise ValueError("无法获取所有缨帽变换分量")
            
            # 准备数据矩阵
            valid_mask = np.isfinite(greenness) & np.isfinite(wetness) & \
                        np.isfinite(brightness) & np.isfinite(fourth)
            
            data_matrix = np.column_stack([
                greenness[valid_mask],
                wetness[valid_mask],
                brightness[valid_mask],
                fourth[valid_mask]
            ])
            
            # 标准化
            scaler = StandardScaler()
            data_scaled = scaler.fit_transform(data_matrix)
            
            # 主成分分析
            pca = PCA(n_components=4)
            pca_result = pca.fit_transform(data_scaled)
            
            # 第一主成分作为RSEI
            pc1 = pca_result[:, 0]
            
            # 重构RSEI图像
            rsei = np.full(greenness.shape, np.nan, dtype=np.float32)
            rsei[valid_mask] = pc1
            
            # 标准化到[0, 1]范围
            rsei_valid = rsei[valid_mask]
            rsei[valid_mask] = (rsei_valid - np.min(rsei_valid)) / (np.max(rsei_valid) - np.min(rsei_valid))
            
            # 计算权重
            weights = pca.components_[0]
            
            logger.info("RSEI计算完成")
            return {
                'rsei': rsei,
                'greenness': greenness,
                'wetness': wetness,
                'dryness': -brightness,  # 干度指数为亮度的负值
                'heat': fourth,
                'weights': weights,
                'explained_variance': pca.explained_variance_ratio_
            }
            
        except Exception as e:
            logger.error(f"计算RSEI失败: {e}")
            return None
    
    def calculate_statistics(self, index_data):
        """
        计算指数统计信息
        
        Args:
            index_data: 指数数据数组
        """
        try:
            if index_data is None:
                return None
            
            # 移除无效值
            valid_data = index_data[np.isfinite(index_data)]
            
            if len(valid_data) == 0:
                return None
            
            stats = {
                'min': float(np.min(valid_data)),
                'max': float(np.max(valid_data)),
                'mean': float(np.mean(valid_data)),
                'std': float(np.std(valid_data)),
                'median': float(np.median(valid_data)),
                'percentile_25': float(np.percentile(valid_data, 25)),
                'percentile_75': float(np.percentile(valid_data, 75)),
                'valid_pixels': int(len(valid_data)),
                'total_pixels': int(index_data.size),
                'valid_ratio': float(len(valid_data) / index_data.size)
            }
            
            # 分类统计（适用于NDVI等指数）
            if stats['min'] >= -1 and stats['max'] <= 1:
                # 五级分类
                thresholds = [-1, -0.2, 0, 0.2, 0.4, 1]
                labels = ['很差', '差', '中等', '良好', '优秀']
                
                for i, (threshold, label) in enumerate(zip(thresholds[:-1], labels)):
                    mask = (valid_data >= threshold) & (valid_data < thresholds[i+1])
                    stats[f'{label}_pixels'] = int(np.sum(mask))
                    stats[f'{label}_ratio'] = float(np.sum(mask) / len(valid_data))
            
            return stats
            
        except Exception as e:
            logger.error(f"计算统计信息失败: {e}")
            return None
    
    def save_result(self, index_data, output_path, index_name="index"):
        """
        保存计算结果为GeoTIFF文件
        
        Args:
            index_data: 指数数据数组
            output_path: 输出文件路径
            index_name: 指数名称
        """
        try:
            if index_data is None:
                raise ValueError("指数数据为空")
            
            # 创建输出目录
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 创建GeoTIFF文件
            driver = gdal.GetDriverByName('GTiff')
            out_dataset = driver.Create(
                output_path,
                self.width,
                self.height,
                1,  # 单波段
                gdal.GDT_Float32
            )
            
            if out_dataset is None:
                raise ValueError("无法创建输出文件")
            
            # 设置地理变换参数
            out_dataset.SetGeoTransform(self.geotransform)
            out_dataset.SetProjection(self.projection)
            
            # 写入数据
            out_band = out_dataset.GetRasterBand(1)
            out_band.WriteArray(index_data)
            
            # 设置元数据
            out_band.SetDescription(f"{index_name} Index")
            out_band.SetNoDataValue(np.nan)
            
            # 计算统计信息
            valid_data = index_data[np.isfinite(index_data)]
            if len(valid_data) > 0:
                out_band.SetStatistics(
                    float(np.min(valid_data)),
                    float(np.max(valid_data)),
                    float(np.mean(valid_data)),
                    float(np.std(valid_data))
                )
            
            # 刷新缓存
            out_band.FlushCache()
            out_dataset.FlushCache()
            
            # 关闭文件
            out_dataset = None
            
            logger.info(f"结果已保存到: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存结果失败: {e}")
            return False
    
    def create_visualization(self, index_data, index_name, output_path, colormap='RdYlGn'):
        """
        创建可视化图片
        
        Args:
            index_data: 指数数据数组
            index_name: 指数名称
            output_path: 输出图片路径
            colormap: 颜色映射
        """
        try:
            if index_data is None:
                raise ValueError("指数数据为空")
            
            # 创建输出目录
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 准备数据
            valid_data = index_data[np.isfinite(index_data)]
            if len(valid_data) == 0:
                raise ValueError("没有有效数据")
            
            # 创建图形
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
            
            # 主图：指数分布
            im1 = ax1.imshow(index_data, cmap=colormap, vmin=np.min(valid_data), vmax=np.max(valid_data))
            ax1.set_title(f'{index_name} 分布图')
            ax1.axis('off')
            
            # 添加颜色条
            cbar1 = plt.colorbar(im1, ax=ax1, shrink=0.8)
            cbar1.set_label(f'{index_name} 值')
            
            # 子图：直方图
            ax2.hist(valid_data, bins=50, alpha=0.7, color='skyblue', edgecolor='black')
            ax2.set_title(f'{index_name} 值分布直方图')
            ax2.set_xlabel(f'{index_name} 值')
            ax2.set_ylabel('像素数量')
            ax2.grid(True, alpha=0.3)
            
            # 添加统计信息
            stats_text = f"""
            统计信息:
            最小值: {np.min(valid_data):.4f}
            最大值: {np.max(valid_data):.4f}
            平均值: {np.mean(valid_data):.4f}
            标准差: {np.std(valid_data):.4f}
            有效像素: {len(valid_data):,}
            """
            ax2.text(0.02, 0.98, stats_text, transform=ax2.transAxes, 
                    verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"可视化图片已保存到: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"创建可视化失败: {e}")
            return False
    
    def close(self):
        """关闭数据集"""
        if self.dataset is not None:
            self.dataset = None
            logger.info("数据集已关闭")


def calculate_all_indices(image_path, output_dir):
    """
    计算所有生态指数的便捷函数
    
    Args:
        image_path: 输入影像路径
        output_dir: 输出目录
    """
    try:
        # 创建计算器
        calculator = GDALEcologicalIndexCalculator(image_path)
        
        # 加载影像
        if not calculator.load_image():
            raise ValueError("无法加载影像")
        
        # 获取波段信息
        band_info = calculator.get_band_info()
        logger.info(f"波段信息: {json.dumps(band_info, indent=2, default=str)}")
        
        # 计算各种指数
        indices = {}
        results = {}
        
        # NDVI
        ndvi = calculator.calculate_ndvi()
        if ndvi is not None:
            indices['NDVI'] = ndvi
            results['NDVI'] = calculator.calculate_statistics(ndvi)
            
            # 保存结果
            ndvi_path = os.path.join(output_dir, 'ndvi.tif')
            calculator.save_result(ndvi, ndvi_path, 'NDVI')
            
            # 创建可视化
            vis_path = os.path.join(output_dir, 'ndvi_visualization.png')
            calculator.create_visualization(ndvi, 'NDVI', vis_path, 'RdYlGn')
        
        # NDWI
        ndwi = calculator.calculate_ndwi()
        if ndwi is not None:
            indices['NDWI'] = ndwi
            results['NDWI'] = calculator.calculate_statistics(ndwi)
            
            ndwi_path = os.path.join(output_dir, 'ndwi.tif')
            calculator.save_result(ndwi, ndwi_path, 'NDWI')
            
            vis_path = os.path.join(output_dir, 'ndwi_visualization.png')
            calculator.create_visualization(ndwi, 'NDWI', vis_path, 'Blues')
        
        # NDBI
        ndbi = calculator.calculate_ndbi()
        if ndbi is not None:
            indices['NDBI'] = ndbi
            results['NDBI'] = calculator.calculate_statistics(ndbi)
            
            ndbi_path = os.path.join(output_dir, 'ndbi.tif')
            calculator.save_result(ndbi, ndbi_path, 'NDBI')
            
            vis_path = os.path.join(output_dir, 'ndbi_visualization.png')
            calculator.create_visualization(ndbi, 'NDBI', vis_path, 'Reds')
        
        # NDSI
        ndsi = calculator.calculate_ndsi()
        if ndsi is not None:
            indices['NDSI'] = ndsi
            results['NDSI'] = calculator.calculate_statistics(ndsi)
            
            ndsi_path = os.path.join(output_dir, 'ndsi.tif')
            calculator.save_result(ndsi, ndsi_path, 'NDSI')
            
            vis_path = os.path.join(output_dir, 'ndsi_visualization.png')
            calculator.create_visualization(ndsi, 'NDSI', vis_path, 'Blues')
        
        # RSEI
        rsei_result = calculator.calculate_rsei()
        if rsei_result is not None:
            indices['RSEI'] = rsei_result['rsei']
            results['RSEI'] = calculator.calculate_statistics(rsei_result['rsei'])
            
            # 保存RSEI结果
            rsei_path = os.path.join(output_dir, 'rsei.tif')
            calculator.save_result(rsei_result['rsei'], rsei_path, 'RSEI')
            
            vis_path = os.path.join(output_dir, 'rsei_visualization.png')
            calculator.create_visualization(rsei_result['rsei'], 'RSEI', vis_path, 'RdYlGn')
            
            # 保存分量
            for component in ['greenness', 'wetness', 'dryness', 'heat']:
                if component in rsei_result:
                    comp_data = rsei_result[component]
                    comp_path = os.path.join(output_dir, f'rsei_{component}.tif')
                    calculator.save_result(comp_data, comp_path, f'RSEI_{component.upper()}')
        
        # 保存统计结果
        stats_path = os.path.join(output_dir, 'statistics.json')
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        # 关闭计算器
        calculator.close()
        
        logger.info(f"所有指数计算完成，结果保存在: {output_dir}")
        return results
        
    except Exception as e:
        logger.error(f"计算所有指数失败: {e}")
        return None


if __name__ == "__main__":
    # 测试代码
    import sys
    
    if len(sys.argv) != 3:
        print("用法: python gdal_ecological_indices.py <input_image> <output_dir>")
        sys.exit(1)
    
    input_image = sys.argv[1]
    output_dir = sys.argv[2]
    
    # 设置日志
    logging.basicConfig(level=logging.INFO)
    
    # 计算所有指数
    results = calculate_all_indices(input_image, output_dir)
    
    if results:
        print("计算完成！")
        for index_name, stats in results.items():
            print(f"\n{index_name}:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
    else:
        print("计算失败！") 