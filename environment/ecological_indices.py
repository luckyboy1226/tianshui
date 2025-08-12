import numpy as np
import rasterio
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
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

logger = logging.getLogger(__name__)


class EcologicalIndexCalculator:
    """生态指数计算器"""
    
    def __init__(self, image_path):
        """
        初始化计算器
        
        Args:
            image_path: 遥感影像文件路径
        """
        self.image_path = image_path
        self.dataset = None
        self.bands = None
        self.metadata = None
        
    def load_image(self):
        """加载遥感影像"""
        try:
            self.dataset = rasterio.open(self.image_path)
            self.bands = self.dataset.read()
            self.metadata = self.dataset.meta
            logger.info(f"成功加载影像: {self.image_path}")
            return True
        except Exception as e:
            logger.error(f"加载影像失败: {e}")
            return False
    
    def calculate_ndvi(self):
        """计算NDVI（归一化植被指数）"""
        try:
            # 假设红波段和近红外波段分别为第3和第4波段
            red_band = self.bands[2].astype(float)  # 红波段
            nir_band = self.bands[3].astype(float)  # 近红外波段
            
            # 避免除零错误
            denominator = nir_band + red_band
            denominator[denominator == 0] = 1e-10
            
            ndvi = (nir_band - red_band) / denominator
            
            # 限制值范围在[-1, 1]
            ndvi = np.clip(ndvi, -1, 1)
            
            return ndvi
        except Exception as e:
            logger.error(f"计算NDVI失败: {e}")
            return None
    
    def calculate_ndwi(self):
        """计算NDWI（归一化水体指数）"""
        try:
            # 假设绿波段和近红外波段分别为第2和第4波段
            green_band = self.bands[1].astype(float)  # 绿波段
            nir_band = self.bands[3].astype(float)  # 近红外波段
            
            denominator = green_band + nir_band
            denominator[denominator == 0] = 1e-10
            
            ndwi = (green_band - nir_band) / denominator
            ndwi = np.clip(ndwi, -1, 1)
            
            return ndwi
        except Exception as e:
            logger.error(f"计算NDWI失败: {e}")
            return None
    
    def calculate_ndbi(self):
        """计算NDBI（归一化建筑指数）"""
        try:
            # 假设近红外波段和中红外波段分别为第4和第5波段
            nir_band = self.bands[3].astype(float)  # 近红外波段
            swir_band = self.bands[4].astype(float)  # 中红外波段
            
            denominator = nir_band + swir_band
            denominator[denominator == 0] = 1e-10
            
            ndbi = (swir_band - nir_band) / denominator
            ndbi = np.clip(ndbi, -1, 1)
            
            return ndbi
        except Exception as e:
            logger.error(f"计算NDBI失败: {e}")
            return None
    
    def calculate_ndsi(self):
        """计算NDSI（归一化积雪指数）"""
        try:
            # 假设绿波段和中红外波段分别为第2和第5波段
            green_band = self.bands[1].astype(float)  # 绿波段
            swir_band = self.bands[4].astype(float)  # 中红外波段
            
            denominator = green_band + swir_band
            denominator[denominator == 0] = 1e-10
            
            ndsi = (green_band - swir_band) / denominator
            ndsi = np.clip(ndsi, -1, 1)
            
            return ndsi
        except Exception as e:
            logger.error(f"计算NDSI失败: {e}")
            return None
    
    def calculate_wetness(self):
        """计算湿度指数（基于Tasseled Cap变换）"""
        try:
            # Tasseled Cap变换系数（Landsat 8）
            # 这些系数需要根据具体的传感器调整
            coefficients = {
                'blue': 0.1511,
                'green': 0.1973,
                'red': 0.3283,
                'nir': 0.3407,
                'swir1': -0.7117,
                'swir2': -0.4559
            }
            
            wetness = (
                coefficients['blue'] * self.bands[0] +
                coefficients['green'] * self.bands[1] +
                coefficients['red'] * self.bands[2] +
                coefficients['nir'] * self.bands[3] +
                coefficients['swir1'] * self.bands[4] +
                coefficients['swir2'] * self.bands[5]
            )
            
            return wetness
        except Exception as e:
            logger.error(f"计算湿度指数失败: {e}")
            return None
    
    def calculate_dryness(self):
        """计算干度指数（基于Tasseled Cap变换）"""
        try:
            # Tasseled Cap变换系数（Landsat 8）
            coefficients = {
                'blue': -0.2936,
                'green': -0.2434,
                'red': -0.5424,
                'nir': 0.7276,
                'swir1': 0.0713,
                'swir2': -0.1608
            }
            
            dryness = (
                coefficients['blue'] * self.bands[0] +
                coefficients['green'] * self.bands[1] +
                coefficients['red'] * self.bands[2] +
                coefficients['nir'] * self.bands[3] +
                coefficients['swir1'] * self.bands[4] +
                coefficients['swir2'] * self.bands[5]
            )
            
            return dryness
        except Exception as e:
            logger.error(f"计算干度指数失败: {e}")
            return None
    
    def calculate_heat(self):
        """计算热度指数（基于Tasseled Cap变换）"""
        try:
            # Tasseled Cap变换系数（Landsat 8）
            coefficients = {
                'blue': 0.0315,
                'green': 0.2021,
                'red': 0.3102,
                'nir': 0.1594,
                'swir1': -0.6806,
                'swir2': -0.6109
            }
            
            heat = (
                coefficients['blue'] * self.bands[0] +
                coefficients['green'] * self.bands[1] +
                coefficients['red'] * self.bands[2] +
                coefficients['nir'] * self.bands[3] +
                coefficients['swir1'] * self.bands[4] +
                coefficients['swir2'] * self.bands[5]
            )
            
            return heat
        except Exception as e:
            logger.error(f"计算热度指数失败: {e}")
            return None
    
    def calculate_greenness(self):
        """计算绿度指数（基于Tasseled Cap变换）"""
        try:
            # Tasseled Cap变换系数（Landsat 8）
            coefficients = {
                'blue': -0.2941,
                'green': -0.2430,
                'red': -0.5424,
                'nir': 0.7276,
                'swir1': 0.0713,
                'swir2': -0.1608
            }
            
            greenness = (
                coefficients['blue'] * self.bands[0] +
                coefficients['green'] * self.bands[1] +
                coefficients['red'] * self.bands[2] +
                coefficients['nir'] * self.bands[3] +
                coefficients['swir1'] * self.bands[4] +
                coefficients['swir2'] * self.bands[5]
            )
            
            return greenness
        except Exception as e:
            logger.error(f"计算绿度指数失败: {e}")
            return None
    
    def calculate_rsei(self):
        """计算RSEI（遥感生态指数）"""
        try:
            # 计算各分量指数
            greenness = self.calculate_greenness()
            wetness = self.calculate_wetness()
            dryness = self.calculate_dryness()
            heat = self.calculate_heat()
            
            if greenness is None or wetness is None or dryness is None or heat is None:
                return None
            
            # 标准化处理
            scaler = StandardScaler()
            indices = np.stack([greenness.flatten(), wetness.flatten(), 
                              dryness.flatten(), heat.flatten()], axis=1)
            
            # 去除无效值
            valid_mask = ~np.isnan(indices).any(axis=1)
            indices_valid = indices[valid_mask]
            
            if len(indices_valid) == 0:
                return None
            
            # 标准化
            indices_scaled = scaler.fit_transform(indices_valid)
            
            # 主成分分析
            pca = PCA(n_components=4)
            pca_result = pca.fit_transform(indices_scaled)
            
            # 第一主成分作为RSEI
            pc1 = pca_result[:, 0]
            
            # 重建完整图像
            rsei = np.full(indices.shape[0], np.nan)
            rsei[valid_mask] = pc1
            
            # 重塑为原始形状
            rsei = rsei.reshape(greenness.shape)
            
            # 归一化到[0, 1]
            rsei = (rsei - np.nanmin(rsei)) / (np.nanmax(rsei) - np.nanmin(rsei))
            
            return {
                'rsei': rsei,
                'greenness': greenness,
                'wetness': wetness,
                'dryness': dryness,
                'heat': heat,
                'pca_variance': pca.explained_variance_ratio_,
                'pca_components': pca.components_
            }
        except Exception as e:
            logger.error(f"计算RSEI失败: {e}")
            return None
    
    def calculate_statistics(self, index_data):
        """计算指数统计信息"""
        if index_data is None:
            return None
        
        # 去除无效值
        valid_data = index_data[~np.isnan(index_data)]
        
        if len(valid_data) == 0:
            return None
        
        stats = {
            'min_value': float(np.nanmin(valid_data)),
            'max_value': float(np.nanmax(valid_data)),
            'mean_value': float(np.nanmean(valid_data)),
            'std_value': float(np.nanstd(valid_data)),
        }
        
        # 分类统计（基于标准差）
        mean_val = stats['mean_value']
        std_val = stats['std_value']
        
        # 定义分类阈值
        thresholds = {
            'excellent': mean_val + 1.5 * std_val,
            'good': mean_val + 0.5 * std_val,
            'moderate': mean_val - 0.5 * std_val,
            'poor': mean_val - 1.5 * std_val,
        }
        
        # 计算各等级像素数量
        pixel_size = 30  # 假设30米分辨率
        area_per_pixel = pixel_size * pixel_size / 1000000  # km²
        
        excellent_pixels = np.sum(valid_data >= thresholds['excellent'])
        good_pixels = np.sum((valid_data >= thresholds['good']) & (valid_data < thresholds['excellent']))
        moderate_pixels = np.sum((valid_data >= thresholds['moderate']) & (valid_data < thresholds['good']))
        poor_pixels = np.sum((valid_data >= thresholds['poor']) & (valid_data < thresholds['moderate']))
        bad_pixels = np.sum(valid_data < thresholds['poor'])
        
        stats.update({
            'excellent_area': float(excellent_pixels * area_per_pixel),
            'good_area': float(good_pixels * area_per_pixel),
            'moderate_area': float(moderate_pixels * area_per_pixel),
            'poor_area': float(poor_pixels * area_per_pixel),
            'bad_area': float(bad_pixels * area_per_pixel),
        })
        
        return stats
    
    def create_visualization(self, index_data, index_name, output_path):
        """创建可视化图片"""
        try:
            if index_data is None:
                return False
            
            # 创建自定义颜色映射
            colors_list = ['#8B0000', '#FF0000', '#FFA500', '#FFFF00', '#00FF00', '#006400']
            n_bins = 256
            cmap = LinearSegmentedColormap.from_list('custom', colors_list, N=n_bins)
            
            # 创建图形
            fig, ax = plt.subplots(figsize=(12, 8))
            
            # 绘制指数图
            im = ax.imshow(index_data, cmap=cmap, aspect='auto')
            
            # 添加颜色条
            cbar = plt.colorbar(im, ax=ax, shrink=0.8)
            cbar.set_label(f'{index_name} 值', fontsize=12)
            
            # 设置标题和标签
            ax.set_title(f'{index_name} 分布图', fontsize=16, fontweight='bold')
            ax.set_xlabel('像素列', fontsize=12)
            ax.set_ylabel('像素行', fontsize=12)
            
            # 去除坐标轴刻度
            ax.set_xticks([])
            ax.set_yticks([])
            
            # 保存图片
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return True
        except Exception as e:
            logger.error(f"创建可视化失败: {e}")
            return False
    
    def save_result(self, index_data, output_path):
        """保存计算结果为GeoTIFF文件"""
        try:
            if index_data is None:
                return False
            
            # 创建输出元数据
            output_meta = self.metadata.copy()
            output_meta.update({
                'count': 1,
                'dtype': 'float32',
                'nodata': np.nan
            })
            
            # 保存文件
            with rasterio.open(output_path, 'w', **output_meta) as dst:
                dst.write(index_data.astype('float32'), 1)
            
            return True
        except Exception as e:
            logger.error(f"保存结果失败: {e}")
            return False
    
    def close(self):
        """关闭数据集"""
        if self.dataset:
            self.dataset.close() 