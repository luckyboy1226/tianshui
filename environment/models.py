from django.db import models
from users.models import User
import uuid


class RemoteSensingImage(models.Model):
    """遥感影像数据模型"""
    IMAGE_TYPE_CHOICES = [
        ('landsat8', 'Landsat 8'),
        ('landsat9', 'Landsat 9'),
        ('sentinel2', 'Sentinel-2'),
        ('custom', '自定义'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name='影像名称')
    description = models.TextField(blank=True, null=True, verbose_name='描述')
    image_type = models.CharField(max_length=20, choices=IMAGE_TYPE_CHOICES, verbose_name='影像类型')
    file_path = models.FileField(upload_to='remote_sensing/', verbose_name='影像文件')
    thumbnail = models.ImageField(upload_to='thumbnails/', blank=True, null=True, verbose_name='缩略图')
    
    # 地理信息（简化版本，不使用GIS字段）
    center_lat = models.FloatField(verbose_name='中心纬度')
    center_lon = models.FloatField(verbose_name='中心经度')
    
    # 时间信息
    acquisition_date = models.DateField(verbose_name='获取日期')
    processing_date = models.DateTimeField(auto_now_add=True, verbose_name='处理时间')
    
    # 元数据
    resolution = models.FloatField(blank=True, null=True, verbose_name='分辨率(米)')
    bands_count = models.IntegerField(blank=True, null=True, verbose_name='波段数')
    file_size = models.BigIntegerField(blank=True, null=True, verbose_name='文件大小(字节)')
    
    # 状态
    is_processed = models.BooleanField(default=False, verbose_name='是否已处理')
    processing_status = models.CharField(max_length=20, default='pending', verbose_name='处理状态')
    
    # 用户信息
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='上传用户')
    
    class Meta:
        verbose_name = '遥感影像'
        verbose_name_plural = '遥感影像'
        db_table = 'remote_sensing_images'
        ordering = ['-acquisition_date']
    
    def __str__(self):
        return f"{self.name} ({self.acquisition_date})"


class EcologicalIndex(models.Model):
    """生态指数模型"""
    INDEX_TYPE_CHOICES = [
        ('ndvi', 'NDVI - 归一化植被指数'),
        ('ndwi', 'NDWI - 归一化水体指数'),
        ('ndbi', 'NDBI - 归一化建筑指数'),
        ('ndsi', 'NDSI - 归一化积雪指数'),
        ('rsei', 'RSEI - 遥感生态指数'),
        ('wetness', '湿度指数'),
        ('dryness', '干度指数'),
        ('heat', '热度指数'),
        ('greenness', '绿度指数'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    remote_sensing_image = models.ForeignKey(RemoteSensingImage, on_delete=models.CASCADE, verbose_name='遥感影像')
    index_type = models.CharField(max_length=20, choices=INDEX_TYPE_CHOICES, verbose_name='指数类型')
    
    # 计算结果
    result_file = models.FileField(upload_to='ecological_indices/', verbose_name='结果文件')
    visualization_file = models.ImageField(upload_to='visualizations/', verbose_name='可视化图片')
    
    # 统计信息
    min_value = models.FloatField(blank=True, null=True, verbose_name='最小值')
    max_value = models.FloatField(blank=True, null=True, verbose_name='最大值')
    mean_value = models.FloatField(blank=True, null=True, verbose_name='平均值')
    std_value = models.FloatField(blank=True, null=True, verbose_name='标准差')
    
    # 分类统计
    excellent_area = models.FloatField(blank=True, null=True, verbose_name='优秀面积(km²)')
    good_area = models.FloatField(blank=True, null=True, verbose_name='良好面积(km²)')
    moderate_area = models.FloatField(blank=True, null=True, verbose_name='中等面积(km²)')
    poor_area = models.FloatField(blank=True, null=True, verbose_name='较差面积(km²)')
    bad_area = models.FloatField(blank=True, null=True, verbose_name='差面积(km²)')
    
    # 处理信息
    processing_time = models.FloatField(blank=True, null=True, verbose_name='处理时间(秒)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '生态指数'
        verbose_name_plural = '生态指数'
        db_table = 'ecological_indices'
        unique_together = ['remote_sensing_image', 'index_type']
    
    def __str__(self):
        return f"{self.remote_sensing_image.name} - {self.get_index_type_display()}"


class RSEIResult(models.Model):
    """RSEI综合生态指数结果模型"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    remote_sensing_image = models.ForeignKey(RemoteSensingImage, on_delete=models.CASCADE, verbose_name='遥感影像')
    
    # RSEI各分量
    greenness = models.ForeignKey(EcologicalIndex, on_delete=models.CASCADE, related_name='rsei_greenness', verbose_name='绿度指数')
    wetness = models.ForeignKey(EcologicalIndex, on_delete=models.CASCADE, related_name='rsei_wetness', verbose_name='湿度指数')
    dryness = models.ForeignKey(EcologicalIndex, on_delete=models.CASCADE, related_name='rsei_dryness', verbose_name='干度指数')
    heat = models.ForeignKey(EcologicalIndex, on_delete=models.CASCADE, related_name='rsei_heat', verbose_name='热度指数')
    
    # RSEI结果
    rsei_result = models.ForeignKey(EcologicalIndex, on_delete=models.CASCADE, related_name='rsei_final', verbose_name='RSEI结果')
    
    # 主成分分析结果
    pc1_variance = models.FloatField(verbose_name='第一主成分方差贡献率')
    pc2_variance = models.FloatField(verbose_name='第二主成分方差贡献率')
    pc3_variance = models.FloatField(verbose_name='第三主成分方差贡献率')
    pc4_variance = models.FloatField(verbose_name='第四主成分方差贡献率')
    
    # 权重
    greenness_weight = models.FloatField(verbose_name='绿度权重')
    wetness_weight = models.FloatField(verbose_name='湿度权重')
    dryness_weight = models.FloatField(verbose_name='干度权重')
    heat_weight = models.FloatField(verbose_name='热度权重')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = 'RSEI结果'
        verbose_name_plural = 'RSEI结果'
        db_table = 'rsei_results'
    
    def __str__(self):
        return f"RSEI - {self.remote_sensing_image.name}"


class ProcessingTask(models.Model):
    """处理任务模型"""
    TASK_STATUS_CHOICES = [
        ('pending', '等待中'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('cancelled', '已取消'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    remote_sensing_image = models.ForeignKey(RemoteSensingImage, on_delete=models.CASCADE, verbose_name='遥感影像')
    task_type = models.CharField(max_length=50, verbose_name='任务类型')
    status = models.CharField(max_length=20, choices=TASK_STATUS_CHOICES, default='pending', verbose_name='任务状态')
    
    # 进度信息
    progress = models.IntegerField(default=0, verbose_name='进度百分比')
    current_step = models.CharField(max_length=100, blank=True, null=True, verbose_name='当前步骤')
    
    # 错误信息
    error_message = models.TextField(blank=True, null=True, verbose_name='错误信息')
    
    # 时间信息
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    started_at = models.DateTimeField(blank=True, null=True, verbose_name='开始时间')
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name='完成时间')
    
    class Meta:
        verbose_name = '处理任务'
        verbose_name_plural = '处理任务'
        db_table = 'processing_tasks'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.task_type} - {self.remote_sensing_image.name} ({self.get_status_display()})" 