from rest_framework import serializers
from .models import (
    RemoteSensingImage, 
    EcologicalIndex, 
    RSEIResult, 
    ProcessingTask
)
from users.serializers import UserSerializer


class RemoteSensingImageSerializer(serializers.ModelSerializer):
    """遥感影像序列化器"""
    uploaded_by = UserSerializer(read_only=True)
    file_size_mb = serializers.SerializerMethodField()
    processing_status_display = serializers.CharField(source='get_processing_status_display', read_only=True)
    
    class Meta:
        model = RemoteSensingImage
        fields = [
            'id', 'name', 'description', 'image_type', 'file_path', 'thumbnail',
            'center_lat', 'center_lon', 'acquisition_date', 'processing_date',
            'resolution', 'bands_count', 'file_size', 'file_size_mb',
            'is_processed', 'processing_status', 'processing_status_display',
            'uploaded_by'
        ]
        read_only_fields = ['id', 'processing_date', 'file_size', 'uploaded_by']
    
    def get_file_size_mb(self, obj):
        """获取文件大小（MB）"""
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return None


class EcologicalIndexSerializer(serializers.ModelSerializer):
    """生态指数序列化器"""
    remote_sensing_image = RemoteSensingImageSerializer(read_only=True)
    index_type_display = serializers.CharField(source='get_index_type_display', read_only=True)
    
    class Meta:
        model = EcologicalIndex
        fields = [
            'id', 'remote_sensing_image', 'index_type', 'index_type_display',
            'result_file', 'visualization_file', 'min_value', 'max_value',
            'mean_value', 'std_value', 'excellent_area', 'good_area',
            'moderate_area', 'poor_area', 'bad_area', 'processing_time',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RSEIResultSerializer(serializers.ModelSerializer):
    """RSEI结果序列化器"""
    remote_sensing_image = RemoteSensingImageSerializer(read_only=True)
    greenness = EcologicalIndexSerializer(read_only=True)
    wetness = EcologicalIndexSerializer(read_only=True)
    dryness = EcologicalIndexSerializer(read_only=True)
    heat = EcologicalIndexSerializer(read_only=True)
    rsei_result = EcologicalIndexSerializer(read_only=True)
    
    class Meta:
        model = RSEIResult
        fields = [
            'id', 'remote_sensing_image', 'greenness', 'wetness', 'dryness', 'heat',
            'rsei_result', 'pc1_variance', 'pc2_variance', 'pc3_variance', 'pc4_variance',
            'greenness_weight', 'wetness_weight', 'dryness_weight', 'heat_weight',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ProcessingTaskSerializer(serializers.ModelSerializer):
    """处理任务序列化器"""
    remote_sensing_image = RemoteSensingImageSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ProcessingTask
        fields = [
            'id', 'remote_sensing_image', 'task_type', 'status', 'status_display',
            'celery_task_id', 'progress', 'current_step', 'error_message',
            'created_at', 'started_at', 'completed_at'
        ]
        read_only_fields = ['id', 'created_at', 'started_at', 'completed_at']


class RemoteSensingImageUploadSerializer(serializers.ModelSerializer):
    """遥感影像上传序列化器"""
    class Meta:
        model = RemoteSensingImage
        fields = ['name', 'description', 'image_type', 'file_path', 'acquisition_date', 'center_lat', 'center_lon']
    
    def validate_file_path(self, value):
        """验证文件格式"""
        allowed_extensions = ['.tif', '.tiff', '.img', '.hdf', '.nc', '.zip']
        file_extension = value.name.lower()
        
        if not any(file_extension.endswith(ext) for ext in allowed_extensions):
            raise serializers.ValidationError(
                f"不支持的文件格式。支持的格式: {', '.join(allowed_extensions)}"
            )
        
        # 检查文件大小（50MB限制）
        if value.size > 50 * 1024 * 1024:
            raise serializers.ValidationError("文件大小不能超过50MB")
        
        return value


class EcologicalIndexCalculationSerializer(serializers.Serializer):
    """生态指数计算请求序列化器"""
    remote_sensing_image_id = serializers.UUIDField()
    indices = serializers.ListField(
        child=serializers.ChoiceField(choices=EcologicalIndex.INDEX_TYPE_CHOICES),
        min_length=1
    )
    
    def validate_remote_sensing_image_id(self, value):
        """验证遥感影像是否存在"""
        try:
            RemoteSensingImage.objects.get(id=value)
        except RemoteSensingImage.DoesNotExist:
            raise serializers.ValidationError("指定的遥感影像不存在")
        return value


class RSEICalculationSerializer(serializers.Serializer):
    """RSEI计算请求序列化器"""
    remote_sensing_image_id = serializers.UUIDField()
    
    def validate_remote_sensing_image_id(self, value):
        """验证遥感影像是否存在"""
        try:
            RemoteSensingImage.objects.get(id=value)
        except RemoteSensingImage.DoesNotExist:
            raise serializers.ValidationError("指定的遥感影像不存在")
        return value


class EcologicalIndexStatisticsSerializer(serializers.Serializer):
    """生态指数统计信息序列化器"""
    index_type = serializers.CharField()
    total_area = serializers.FloatField()
    excellent_percentage = serializers.FloatField()
    good_percentage = serializers.FloatField()
    moderate_percentage = serializers.FloatField()
    poor_percentage = serializers.FloatField()
    bad_percentage = serializers.FloatField()
    mean_value = serializers.FloatField()
    std_value = serializers.FloatField() 