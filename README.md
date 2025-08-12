# 天水平台 - 流域生态环境监管系统

## 项目简介

天水平台是一个基于Django的流域生态环境监管系统，提供遥感影像处理、生态指数计算、环境监测数据分析等功能。

## 功能特性

### 基础功能
- 地图展示和数据加载
- 在线影像底图加载
- 标准矢量/栅格数据格式支持（KML、WFS、Shapefile、WMS、WCS）
- 动态切换底图
- 基础地图操作（缩放、平移、复位、旋转）
- 图层管理（显示/隐藏、排序、分组）
- 图形绘制工具
- 坐标定位
- 用户权限管理
- 地图视图保存为图片
- 本地文件上传支持

### 业务功能
- **遥感生态指数计算**：NDVI、NDWI、NDBI、NDSI、RSEI等
- **生态环境质量评估**：绿度、湿度、干度、热度指数
- **生态修复工程监控**
- **环境监测数据分析**
- **问卷调查和意见反馈**

## 技术栈

### 后端技术
- **Django 5.2.4** - Web框架
- **Django REST Framework** - API开发
- **PostgreSQL + PostGIS** - 空间数据库
- **Celery + Redis** - 异步任务处理
- **GeoServer** - 地理空间数据服务

### 数据处理
- **GeoPandas** - 地理数据处理
- **Rasterio** - 栅格数据处理
- **NumPy/Pandas** - 数值计算和数据分析
- **Scikit-learn** - 机器学习算法
- **Matplotlib/Seaborn** - 数据可视化

### 遥感处理
- **GDAL/OGR** - 地理空间数据抽象库
- **OpenCV** - 计算机视觉
- **Pillow** - 图像处理

## 安装部署

### 环境要求
- Python 3.8+
- PostgreSQL 12+ with PostGIS
- Redis 6+
- GDAL 3.6+

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd tianshuipy
```

2. **创建虚拟环境**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置数据库**
```bash
# 创建PostgreSQL数据库
createdb tianshuipy_db

# 启用PostGIS扩展
psql -d tianshuipy_db -c "CREATE EXTENSION postgis;"
```

5. **配置环境变量**
```bash
# 创建.env文件
cp .env.example .env
# 编辑.env文件，设置数据库连接等信息
```

6. **数据库迁移**
```bash
python manage.py makemigrations
python manage.py migrate
```

7. **创建超级用户**
```bash
python manage.py create_superuser
```

8. **启动服务**
```bash
# 启动Redis
redis-server

# 启动Celery Worker
celery -A tianshuipy worker -l info

# 启动Django开发服务器
python manage.py runserver
```

## API文档

### 用户管理API
- `POST /api/v1/users/users/login/` - 用户登录
- `POST /api/v1/users/users/logout/` - 用户登出
- `GET /api/v1/users/users/profile/` - 获取用户信息
- `PUT /api/v1/users/users/update_profile/` - 更新用户信息

### 遥感影像API
- `POST /api/v1/environment/api/remote-sensing-images/upload/` - 上传遥感影像
- `GET /api/v1/environment/api/remote-sensing-images/` - 获取遥感影像列表
- `POST /api/v1/environment/api/remote-sensing-images/{id}/calculate_indices/` - 计算生态指数
- `POST /api/v1/environment/api/remote-sensing-images/{id}/calculate_rsei/` - 计算RSEI
- `GET /api/v1/environment/api/remote-sensing-images/{id}/indices/` - 获取生态指数列表

### 生态指数API
- `GET /api/v1/environment/api/ecological-indices/` - 获取生态指数列表
- `GET /api/v1/environment/api/ecological-indices/{id}/statistics/` - 获取统计信息

### 任务管理API
- `GET /api/v1/environment/api/processing-tasks/` - 获取任务列表
- `GET /api/v1/environment/api/processing-tasks/{id}/status/` - 获取任务状态

## 生态指数计算

### 支持的指数类型
1. **NDVI** - 归一化植被指数
2. **NDWI** - 归一化水体指数
3. **NDBI** - 归一化建筑指数
4. **NDSI** - 归一化积雪指数
5. **RSEI** - 遥感生态指数（综合指数）
6. **绿度指数** - 基于Tasseled Cap变换
7. **湿度指数** - 基于Tasseled Cap变换
8. **干度指数** - 基于Tasseled Cap变换
9. **热度指数** - 基于Tasseled Cap变换

### 计算流程
1. 用户上传遥感影像
2. 系统验证文件格式和大小
3. 启动Celery异步任务
4. 计算选定的生态指数
5. 生成统计信息和可视化图片
6. 保存结果到数据库

## 项目结构

```
tianshuipy/
├── tianshuipy/          # 项目配置
│   ├── settings.py      # 项目设置
│   ├── urls.py          # 主URL配置
│   ├── celery.py        # Celery配置
│   └── wsgi.py          # WSGI配置
├── users/               # 用户管理应用
│   ├── models.py        # 用户模型
│   ├── views.py         # 用户视图
│   ├── serializers.py   # 用户序列化器
│   └── urls.py          # 用户URL配置
├── environment/         # 环境监测应用
│   ├── models.py        # 环境监测模型
│   ├── views.py         # 环境监测视图
│   ├── serializers.py   # 环境监测序列化器
│   ├── tasks.py         # Celery任务
│   ├── ecological_indices.py  # 生态指数计算
│   └── urls.py          # 环境监测URL配置
├── media/               # 媒体文件
├── static/              # 静态文件
├── logs/                # 日志文件
├── requirements.txt     # 项目依赖
└── README.md           # 项目说明
```

## 开发指南

### 添加新的生态指数
1. 在 `environment/ecological_indices.py` 中添加计算方法
2. 在 `EcologicalIndexCalculator` 类中实现计算逻辑
3. 在 `environment/tasks.py` 中添加任务处理
4. 在 `environment/models.py` 中添加指数类型选项
5. 更新API文档

### 自定义权限
1. 在 `users/models.py` 中定义权限模型
2. 在视图中使用权限装饰器
3. 在序列化器中添加权限验证

## 部署说明

### 生产环境部署
1. 使用Gunicorn作为WSGI服务器
2. 配置Nginx作为反向代理
3. 使用Supervisor管理Celery进程
4. 配置PostgreSQL连接池
5. 设置Redis持久化

### 性能优化
1. 数据库索引优化
2. 缓存策略配置
3. 静态文件CDN加速
4. 异步任务队列优化

## 许可证

本项目采用MIT许可证。

## 联系方式

如有问题或建议，请联系开发团队。 