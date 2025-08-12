from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import logging

from .models import (
    RemoteSensingImage, 
    EcologicalIndex, 
    RSEIResult, 
    ProcessingTask
)
from .serializers import (
    RemoteSensingImageSerializer,
    EcologicalIndexSerializer,
    RSEIResultSerializer,
    ProcessingTaskSerializer,
    RemoteSensingImageUploadSerializer,
    EcologicalIndexCalculationSerializer,
    RSEICalculationSerializer
)
from .tasks import calculate_ecological_indices, calculate_rsei_only

logger = logging.getLogger(__name__)


class RemoteSensingImageViewSet(viewsets.ModelViewSet):
    """遥感影像视图集"""
    queryset = RemoteSensingImage.objects.all()
    serializer_class = RemoteSensingImageSerializer
    parser_classes = (MultiPartParser, FormParser)
    
    def get_queryset(self):
        """根据用户权限过滤查询集"""
        user = self.request.user
        if user.is_superuser or user.role == 'admin':
            return RemoteSensingImage.objects.all()
        else:
            return RemoteSensingImage.objects.filter(uploaded_by=user)
    
    def perform_create(self, serializer):
        """创建时设置上传用户"""
        serializer.save(uploaded_by=self.request.user)
    
    @action(detail=False, methods=['post'])
    def upload(self, request):
        """上传遥感影像"""
        try:
            serializer = RemoteSensingImageUploadSerializer(data=request.data)
            if serializer.is_valid():
                # 获取文件信息
                file_obj = request.FILES.get('file_path')
                if not file_obj:
                    return Response(
                        {'error': '请选择要上传的文件'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # 保存文件
                file_path = default_storage.save(
                    f'remote_sensing/{file_obj.name}', 
                    ContentFile(file_obj.read())
                )
                
                # 创建遥感影像记录
                with transaction.atomic():
                    remote_sensing_image = RemoteSensingImage.objects.create(
                        name=serializer.validated_data['name'],
                        description=serializer.validated_data.get('description', ''),
                        image_type=serializer.validated_data['image_type'],
                        file_path=file_path,
                        acquisition_date=serializer.validated_data['acquisition_date'],
                        center_lat=serializer.validated_data['center_lat'],
                        center_lon=serializer.validated_data['center_lon'],
                        uploaded_by=request.user,
                        file_size=file_obj.size
                    )
                
                # 返回创建的数据
                result_serializer = RemoteSensingImageSerializer(remote_sensing_image)
                return Response(
                    {
                        'message': '遥感影像上传成功',
                        'data': result_serializer.data
                    },
                    status=status.HTTP_201_CREATED
                )
            else:
                return Response(
                    {'error': '数据验证失败', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            logger.error(f"上传遥感影像失败: {e}")
            return Response(
                {'error': '上传失败', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def calculate_indices(self, request, pk=None):
        """计算生态指数"""
        try:
            remote_sensing_image = self.get_object()
            
            serializer = EcologicalIndexCalculationSerializer(data=request.data)
            if serializer.is_valid():
                indices_list = serializer.validated_data['indices']
                
                # 启动异步任务
                task = calculate_ecological_indices.delay(
                    str(remote_sensing_image.id), 
                    indices_list
                )
                
                return Response({
                    'message': '生态指数计算任务已启动',
                    'task_id': task.id,
                    'indices': indices_list
                }, status=status.HTTP_202_ACCEPTED)
            else:
                return Response(
                    {'error': '参数验证失败', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            logger.error(f"启动生态指数计算失败: {e}")
            return Response(
                {'error': '启动计算失败', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def calculate_rsei(self, request, pk=None):
        """计算RSEI"""
        try:
            remote_sensing_image = self.get_object()
            
            serializer = RSEICalculationSerializer(data=request.data)
            if serializer.is_valid():
                # 启动异步任务
                task = calculate_rsei_only.delay(str(remote_sensing_image.id))
                
                return Response({
                    'message': 'RSEI计算任务已启动',
                    'task_id': task.id
                }, status=status.HTTP_202_ACCEPTED)
            else:
                return Response(
                    {'error': '参数验证失败', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            logger.error(f"启动RSEI计算失败: {e}")
            return Response(
                {'error': '启动计算失败', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def indices(self, request, pk=None):
        """获取遥感影像的所有生态指数"""
        try:
            remote_sensing_image = self.get_object()
            indices = EcologicalIndex.objects.filter(remote_sensing_image=remote_sensing_image)
            serializer = EcologicalIndexSerializer(indices, many=True)
            
            return Response({
                'data': serializer.data,
                'count': indices.count()
            })
        except Exception as e:
            logger.error(f"获取生态指数失败: {e}")
            return Response(
                {'error': '获取失败', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def rsei_result(self, request, pk=None):
        """获取RSEI结果"""
        try:
            remote_sensing_image = self.get_object()
            rsei_result = RSEIResult.objects.filter(remote_sensing_image=remote_sensing_image).first()
            
            if rsei_result:
                serializer = RSEIResultSerializer(rsei_result)
                return Response(serializer.data)
            else:
                return Response(
                    {'message': '暂无RSEI结果'},
                    status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            logger.error(f"获取RSEI结果失败: {e}")
            return Response(
                {'error': '获取失败', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EcologicalIndexViewSet(viewsets.ReadOnlyModelViewSet):
    """生态指数视图集"""
    queryset = EcologicalIndex.objects.all()
    serializer_class = EcologicalIndexSerializer
    
    def get_queryset(self):
        """根据用户权限过滤查询集"""
        user = self.request.user
        if user.is_superuser or user.role == 'admin':
            return EcologicalIndex.objects.all()
        else:
            return EcologicalIndex.objects.filter(remote_sensing_image__uploaded_by=user)
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """获取生态指数统计信息"""
        try:
            ecological_index = self.get_object()
            
            # 计算统计信息
            stats = {
                'index_type': ecological_index.index_type,
                'index_type_display': ecological_index.get_index_type_display(),
                'total_area': sum([
                    ecological_index.excellent_area or 0,
                    ecological_index.good_area or 0,
                    ecological_index.moderate_area or 0,
                    ecological_index.poor_area or 0,
                    ecological_index.bad_area or 0
                ]),
                'excellent_percentage': 0,
                'good_percentage': 0,
                'moderate_percentage': 0,
                'poor_percentage': 0,
                'bad_percentage': 0,
                'mean_value': ecological_index.mean_value,
                'std_value': ecological_index.std_value,
            }
            
            # 计算百分比
            total_area = stats['total_area']
            if total_area > 0:
                stats['excellent_percentage'] = (ecological_index.excellent_area or 0) / total_area * 100
                stats['good_percentage'] = (ecological_index.good_area or 0) / total_area * 100
                stats['moderate_percentage'] = (ecological_index.moderate_area or 0) / total_area * 100
                stats['poor_percentage'] = (ecological_index.poor_area or 0) / total_area * 100
                stats['bad_percentage'] = (ecological_index.bad_area or 0) / total_area * 100
            
            return Response(stats)
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return Response(
                {'error': '获取统计信息失败', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RSEIResultViewSet(viewsets.ReadOnlyModelViewSet):
    """RSEI结果视图集"""
    queryset = RSEIResult.objects.all()
    serializer_class = RSEIResultSerializer
    
    def get_queryset(self):
        """根据用户权限过滤查询集"""
        user = self.request.user
        if user.is_superuser or user.role == 'admin':
            return RSEIResult.objects.all()
        else:
            return RSEIResult.objects.filter(remote_sensing_image__uploaded_by=user)


class ProcessingTaskViewSet(viewsets.ReadOnlyModelViewSet):
    """处理任务视图集"""
    queryset = ProcessingTask.objects.all()
    serializer_class = ProcessingTaskSerializer
    
    def get_queryset(self):
        """根据用户权限过滤查询集"""
        user = self.request.user
        if user.is_superuser or user.role == 'admin':
            return ProcessingTask.objects.all()
        else:
            return ProcessingTask.objects.filter(remote_sensing_image__uploaded_by=user)
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """获取任务状态"""
        try:
            task = self.get_object()
            
            # 如果是Celery任务，获取实时状态
            if task.celery_task_id:
                from celery.result import AsyncResult
                celery_result = AsyncResult(task.celery_task_id)
                
                return Response({
                    'task_id': task.id,
                    'celery_task_id': task.celery_task_id,
                    'status': task.status,
                    'celery_status': celery_result.status,
                    'progress': task.progress,
                    'current_step': task.current_step,
                    'error_message': task.error_message,
                    'created_at': task.created_at,
                    'started_at': task.started_at,
                    'completed_at': task.completed_at,
                })
            else:
                return Response({
                    'task_id': task.id,
                    'status': task.status,
                    'progress': task.progress,
                    'current_step': task.current_step,
                    'error_message': task.error_message,
                    'created_at': task.created_at,
                    'started_at': task.started_at,
                    'completed_at': task.completed_at,
                })
        except Exception as e:
            logger.error(f"获取任务状态失败: {e}")
            return Response(
                {'error': '获取状态失败', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 