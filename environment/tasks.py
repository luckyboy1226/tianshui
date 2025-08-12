import os
import time
import logging
from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from .models import (
    RemoteSensingImage, 
    EcologicalIndex, 
    RSEIResult, 
    ProcessingTask
)
from .ecological_indices import EcologicalIndexCalculator

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def calculate_ecological_indices(self, image_id, indices_list):
    """
    计算生态指数的Celery任务
    
    Args:
        image_id: 遥感影像ID
        indices_list: 要计算的指数列表
    """
    try:
        # 获取遥感影像
        image = RemoteSensingImage.objects.get(id=image_id)
        
        # 创建处理任务记录
        task = ProcessingTask.objects.create(
            remote_sensing_image=image,
            task_type='ecological_index_calculation',
            status='processing',
            celery_task_id=self.request.id
        )
        
        # 更新任务进度
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': len(indices_list), 'status': '开始处理...'}
        )
        
        # 初始化计算器
        calculator = EcologicalIndexCalculator(image.file_path.path)
        if not calculator.load_image():
            raise Exception("无法加载遥感影像")
        
        # 创建输出目录
        output_dir = os.path.join(settings.MEDIA_ROOT, 'ecological_indices', str(image_id))
        os.makedirs(output_dir, exist_ok=True)
        
        # 计算各指数
        calculated_indices = {}
        
        for i, index_type in enumerate(indices_list):
            try:
                # 更新进度
                progress = int((i / len(indices_list)) * 100)
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'current': i + 1, 
                        'total': len(indices_list), 
                        'status': f'正在计算 {index_type}...'
                    }
                )
                
                # 计算指数
                if index_type == 'ndvi':
                    index_data = calculator.calculate_ndvi()
                elif index_type == 'ndwi':
                    index_data = calculator.calculate_ndwi()
                elif index_type == 'ndbi':
                    index_data = calculator.calculate_ndbi()
                elif index_type == 'ndsi':
                    index_data = calculator.calculate_ndsi()
                elif index_type == 'wetness':
                    index_data = calculator.calculate_wetness()
                elif index_type == 'dryness':
                    index_data = calculator.calculate_dryness()
                elif index_type == 'heat':
                    index_data = calculator.calculate_heat()
                elif index_type == 'greenness':
                    index_data = calculator.calculate_greenness()
                else:
                    logger.warning(f"不支持的指数类型: {index_type}")
                    continue
                
                if index_data is None:
                    logger.warning(f"计算 {index_type} 失败")
                    continue
                
                # 计算统计信息
                stats = calculator.calculate_statistics(index_data)
                
                # 保存结果文件
                result_filename = f"{index_type}_result.tif"
                result_path = os.path.join(output_dir, result_filename)
                calculator.save_result(index_data, result_path)
                
                # 创建可视化
                viz_filename = f"{index_type}_visualization.png"
                viz_path = os.path.join(output_dir, viz_filename)
                calculator.create_visualization(index_data, index_type.upper(), viz_path)
                
                # 保存到数据库
                ecological_index = EcologicalIndex.objects.create(
                    remote_sensing_image=image,
                    index_type=index_type,
                    result_file=f'ecological_indices/{image_id}/{result_filename}',
                    visualization_file=f'ecological_indices/{image_id}/{viz_filename}',
                    min_value=stats['min_value'] if stats else None,
                    max_value=stats['max_value'] if stats else None,
                    mean_value=stats['mean_value'] if stats else None,
                    std_value=stats['std_value'] if stats else None,
                    excellent_area=stats['excellent_area'] if stats else None,
                    good_area=stats['good_area'] if stats else None,
                    moderate_area=stats['moderate_area'] if stats else None,
                    poor_area=stats['poor_area'] if stats else None,
                    bad_area=stats['bad_area'] if stats else None,
                )
                
                calculated_indices[index_type] = ecological_index
                logger.info(f"成功计算 {index_type}")
                
            except Exception as e:
                logger.error(f"计算 {index_type} 时出错: {e}")
                continue
        
        # 如果计算了RSEI所需的四个分量，则计算RSEI
        rsei_components = ['greenness', 'wetness', 'dryness', 'heat']
        if all(comp in calculated_indices for comp in rsei_components):
            try:
                self.update_state(
                    state='PROGRESS',
                    meta={'current': len(indices_list), 'total': len(indices_list) + 1, 'status': '正在计算RSEI...'}
                )
                
                rsei_result = calculator.calculate_rsei()
                if rsei_result:
                    # 保存RSEI结果
                    rsei_filename = "rsei_result.tif"
                    rsei_path = os.path.join(output_dir, rsei_filename)
                    calculator.save_result(rsei_result['rsei'], rsei_path)
                    
                    # 创建RSEI可视化
                    rsei_viz_filename = "rsei_visualization.png"
                    rsei_viz_path = os.path.join(output_dir, rsei_viz_filename)
                    calculator.create_visualization(rsei_result['rsei'], 'RSEI', rsei_viz_path)
                    
                    # 计算RSEI统计信息
                    rsei_stats = calculator.calculate_statistics(rsei_result['rsei'])
                    
                    # 保存RSEI指数
                    rsei_index = EcologicalIndex.objects.create(
                        remote_sensing_image=image,
                        index_type='rsei',
                        result_file=f'ecological_indices/{image_id}/{rsei_filename}',
                        visualization_file=f'ecological_indices/{image_id}/{rsei_viz_filename}',
                        min_value=rsei_stats['min_value'] if rsei_stats else None,
                        max_value=rsei_stats['max_value'] if rsei_stats else None,
                        mean_value=rsei_stats['mean_value'] if rsei_stats else None,
                        std_value=rsei_stats['std_value'] if rsei_stats else None,
                        excellent_area=rsei_stats['excellent_area'] if rsei_stats else None,
                        good_area=rsei_stats['good_area'] if rsei_stats else None,
                        moderate_area=rsei_stats['moderate_area'] if rsei_stats else None,
                        poor_area=rsei_stats['poor_area'] if rsei_stats else None,
                        bad_area=rsei_stats['bad_area'] if rsei_stats else None,
                    )
                    
                    # 创建RSEI结果记录
                    RSEIResult.objects.create(
                        remote_sensing_image=image,
                        greenness=calculated_indices['greenness'],
                        wetness=calculated_indices['wetness'],
                        dryness=calculated_indices['dryness'],
                        heat=calculated_indices['heat'],
                        rsei_result=rsei_index,
                        pc1_variance=rsei_result['pca_variance'][0],
                        pc2_variance=rsei_result['pca_variance'][1],
                        pc3_variance=rsei_result['pca_variance'][2],
                        pc4_variance=rsei_result['pca_variance'][3],
                        greenness_weight=rsei_result['pca_components'][0][0],
                        wetness_weight=rsei_result['pca_components'][0][1],
                        dryness_weight=rsei_result['pca_components'][0][2],
                        heat_weight=rsei_result['pca_components'][0][3],
                    )
                    
                    logger.info("成功计算RSEI")
                
            except Exception as e:
                logger.error(f"计算RSEI时出错: {e}")
        
        # 更新遥感影像状态
        image.is_processed = True
        image.processing_status = 'completed'
        image.save()
        
        # 更新任务状态
        task.status = 'completed'
        task.progress = 100
        task.current_step = '处理完成'
        task.completed_at = time.time()
        task.save()
        
        calculator.close()
        
        return {
            'status': 'success',
            'message': f'成功计算 {len(calculated_indices)} 个生态指数',
            'calculated_indices': list(calculated_indices.keys())
        }
        
    except Exception as e:
        logger.error(f"生态指数计算任务失败: {e}")
        
        # 更新任务状态
        if 'task' in locals():
            task.status = 'failed'
            task.error_message = str(e)
            task.save()
        
        # 更新遥感影像状态
        if 'image' in locals():
            image.processing_status = 'failed'
            image.save()
        
        raise e


@shared_task(bind=True)
def calculate_rsei_only(self, image_id):
    """
    仅计算RSEI的Celery任务
    
    Args:
        image_id: 遥感影像ID
    """
    try:
        # 获取遥感影像
        image = RemoteSensingImage.objects.get(id=image_id)
        
        # 创建处理任务记录
        task = ProcessingTask.objects.create(
            remote_sensing_image=image,
            task_type='rsei_calculation',
            status='processing',
            celery_task_id=self.request.id
        )
        
        # 初始化计算器
        calculator = EcologicalIndexCalculator(image.file_path.path)
        if not calculator.load_image():
            raise Exception("无法加载遥感影像")
        
        # 创建输出目录
        output_dir = os.path.join(settings.MEDIA_ROOT, 'ecological_indices', str(image_id))
        os.makedirs(output_dir, exist_ok=True)
        
        # 计算RSEI
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': 1, 'status': '正在计算RSEI...'}
        )
        
        rsei_result = calculator.calculate_rsei()
        if not rsei_result:
            raise Exception("RSEI计算失败")
        
        # 保存RSEI结果
        rsei_filename = "rsei_result.tif"
        rsei_path = os.path.join(output_dir, rsei_filename)
        calculator.save_result(rsei_result['rsei'], rsei_path)
        
        # 创建RSEI可视化
        rsei_viz_filename = "rsei_visualization.png"
        rsei_viz_path = os.path.join(output_dir, rsei_viz_filename)
        calculator.create_visualization(rsei_result['rsei'], 'RSEI', rsei_viz_path)
        
        # 计算RSEI统计信息
        rsei_stats = calculator.calculate_statistics(rsei_result['rsei'])
        
        # 保存RSEI指数
        rsei_index = EcologicalIndex.objects.create(
            remote_sensing_image=image,
            index_type='rsei',
            result_file=f'ecological_indices/{image_id}/{rsei_filename}',
            visualization_file=f'ecological_indices/{image_id}/{rsei_viz_filename}',
            min_value=rsei_stats['min_value'] if rsei_stats else None,
            max_value=rsei_stats['max_value'] if rsei_stats else None,
            mean_value=rsei_stats['mean_value'] if rsei_stats else None,
            std_value=rsei_stats['std_value'] if rsei_stats else None,
            excellent_area=rsei_stats['excellent_area'] if rsei_stats else None,
            good_area=rsei_stats['good_area'] if rsei_stats else None,
            moderate_area=rsei_stats['moderate_area'] if rsei_stats else None,
            poor_area=rsei_stats['poor_area'] if rsei_stats else None,
            bad_area=rsei_stats['bad_area'] if rsei_stats else None,
        )
        
        # 更新任务状态
        task.status = 'completed'
        task.progress = 100
        task.current_step = 'RSEI计算完成'
        task.completed_at = time.time()
        task.save()
        
        calculator.close()
        
        return {
            'status': 'success',
            'message': 'RSEI计算完成',
            'rsei_id': str(rsei_index.id)
        }
        
    except Exception as e:
        logger.error(f"RSEI计算任务失败: {e}")
        
        # 更新任务状态
        if 'task' in locals():
            task.status = 'failed'
            task.error_message = str(e)
            task.save()
        
        raise e


@shared_task
def cleanup_temp_files():
    """清理临时文件的任务"""
    try:
        # 清理超过24小时的临时文件
        import shutil
        from datetime import datetime, timedelta
        
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
        if os.path.exists(temp_dir):
            current_time = datetime.now()
            for item in os.listdir(temp_dir):
                item_path = os.path.join(temp_dir, item)
                if os.path.isfile(item_path):
                    file_time = datetime.fromtimestamp(os.path.getctime(item_path))
                    if current_time - file_time > timedelta(hours=24):
                        os.remove(item_path)
                        logger.info(f"删除临时文件: {item_path}")
                elif os.path.isdir(item_path):
                    dir_time = datetime.fromtimestamp(os.path.getctime(item_path))
                    if current_time - dir_time > timedelta(hours=24):
                        shutil.rmtree(item_path)
                        logger.info(f"删除临时目录: {item_path}")
        
        return {'status': 'success', 'message': '临时文件清理完成'}
        
    except Exception as e:
        logger.error(f"清理临时文件失败: {e}")
        return {'status': 'error', 'message': str(e)} 