# 前端配置指南

## 1. 后端API配置

### 基础配置
```javascript
// 后端API基础URL
const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

// API接口配置
const API_CONFIG = {
  // 用户管理
  LOGIN: `${API_BASE_URL}/users/users/login/`,
  LOGOUT: `${API_BASE_URL}/users/users/logout/`,
  PROFILE: `${API_BASE_URL}/users/users/profile/`,
  
  // 遥感影像管理
  UPLOAD_IMAGE: `${API_BASE_URL}/environment/api/remote-sensing-images/upload/`,
  GET_IMAGES: `${API_BASE_URL}/environment/api/remote-sensing-images/`,
  CALCULATE_INDICES: (id) => `${API_BASE_URL}/environment/api/remote-sensing-images/${id}/calculate_indices/`,
  GET_INDICES: (id) => `${API_BASE_URL}/environment/api/remote-sensing-images/${id}/indices/`,
  
  // 生态指数
  GET_ECOLOGICAL_INDICES: `${API_BASE_URL}/environment/api/ecological-indices/`,
  GET_INDEX_STATISTICS: (id) => `${API_BASE_URL}/environment/api/ecological-indices/${id}/statistics/`,
  
  // 任务管理
  GET_TASKS: `${API_BASE_URL}/environment/api/processing-tasks/`,
  GET_TASK_STATUS: (id) => `${API_BASE_URL}/environment/api/processing-tasks/${id}/status/`,
};
```

### 请求配置
```javascript
// Axios配置示例
import axios from 'axios';

// 创建axios实例
const api = axios.create({
  baseURL: 'http://127.0.0.1:8000/api/v1',
  timeout: 30000,
  withCredentials: true, // 支持跨域携带cookie
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 添加CSRF Token
    const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)?.[1];
    if (csrfToken) {
      config.headers['X-CSRFToken'] = csrfToken;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    if (error.response?.status === 401) {
      // 未登录，跳转到登录页
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

## 2. 用户认证

### 登录请求
```javascript
// 用户登录
const login = async (username, password) => {
  try {
    const response = await api.post('/users/users/login/', {
      username,
      password
    });
    
    if (response.message === '登录成功') {
      // 保存用户信息
      localStorage.setItem('user', JSON.stringify(response.user));
      return response.user;
    }
  } catch (error) {
    console.error('登录失败:', error);
    throw error;
  }
};
```

### 检查登录状态
```javascript
// 检查用户是否已登录
const checkAuth = async () => {
  try {
    const response = await api.get('/users/users/profile/');
    return response;
  } catch (error) {
    return null;
  }
};
```

## 3. 遥感影像上传

### 文件上传
```javascript
// 上传遥感影像
const uploadImage = async (file, imageData) => {
  const formData = new FormData();
  formData.append('file_path', file);
  formData.append('name', imageData.name);
  formData.append('description', imageData.description);
  formData.append('image_type', imageData.image_type);
  formData.append('acquisition_date', imageData.acquisition_date);
  formData.append('center_lat', imageData.center_lat);
  formData.append('center_lon', imageData.center_lon);
  
  try {
    const response = await api.post('/environment/api/remote-sensing-images/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response;
  } catch (error) {
    console.error('上传失败:', error);
    throw error;
  }
};
```

## 4. 生态指数计算

### 启动计算任务
```javascript
// 计算生态指数
const calculateIndices = async (imageId, indices) => {
  try {
    const response = await api.post(`/environment/api/remote-sensing-images/${imageId}/calculate_indices/`, {
      indices: indices // ['ndvi', 'ndwi', 'rsei']
    });
    
    return response.task_id; // 返回任务ID
  } catch (error) {
    console.error('启动计算失败:', error);
    throw error;
  }
};
```

### 查询任务状态
```javascript
// 查询任务进度
const getTaskStatus = async (taskId) => {
  try {
    const response = await api.get(`/environment/api/processing-tasks/${taskId}/status/`);
    return response;
  } catch (error) {
    console.error('查询任务状态失败:', error);
    throw error;
  }
};

// 轮询任务状态
const pollTaskStatus = (taskId, onProgress, onComplete, onError) => {
  const poll = async () => {
    try {
      const status = await getTaskStatus(taskId);
      
      if (status.status === 'completed') {
        onComplete(status);
      } else if (status.status === 'failed') {
        onError(status.error_message);
      } else {
        onProgress(status.progress, status.current_step);
        // 继续轮询
        setTimeout(poll, 2000);
      }
    } catch (error) {
      onError(error);
    }
  };
  
  poll();
};
```

## 5. 获取计算结果

### 获取生态指数列表
```javascript
// 获取影像的生态指数
const getImageIndices = async (imageId) => {
  try {
    const response = await api.get(`/environment/api/remote-sensing-images/${imageId}/indices/`);
    return response.data;
  } catch (error) {
    console.error('获取生态指数失败:', error);
    throw error;
  }
};
```

### 获取统计信息
```javascript
// 获取指数统计信息
const getIndexStatistics = async (indexId) => {
  try {
    const response = await api.get(`/environment/api/ecological-indices/${indexId}/statistics/`);
    return response;
  } catch (error) {
    console.error('获取统计信息失败:', error);
    throw error;
  }
};
```

## 6. 前端框架集成示例

### Vue.js 示例
```javascript
// Vue组件示例
<template>
  <div>
    <h2>遥感影像上传</h2>
    <input type="file" @change="handleFileUpload" accept=".tif,.tiff,.img,.hdf,.nc,.zip">
    <button @click="uploadImage">上传</button>
    
    <h2>生态指数计算</h2>
    <div v-for="image in images" :key="image.id">
      <span>{{ image.name }}</span>
      <button @click="calculateIndices(image.id)">计算指数</button>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { uploadImage, getImages, calculateIndices } from '@/api';

export default {
  setup() {
    const images = ref([]);
    
    const handleFileUpload = (event) => {
      // 处理文件选择
    };
    
    const upload = async () => {
      // 上传文件
    };
    
    const calculate = async (imageId) => {
      // 计算指数
    };
    
    onMounted(async () => {
      // 获取影像列表
      const response = await getImages();
      images.value = response.results;
    });
    
    return {
      images,
      handleFileUpload,
      upload,
      calculate
    };
  }
};
</script>
```

### React 示例
```javascript
// React组件示例
import React, { useState, useEffect } from 'react';
import { uploadImage, getImages, calculateIndices } from './api';

function ImageUpload() {
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(false);
  
  useEffect(() => {
    fetchImages();
  }, []);
  
  const fetchImages = async () => {
    try {
      const response = await getImages();
      setImages(response.results);
    } catch (error) {
      console.error('获取影像失败:', error);
    }
  };
  
  const handleUpload = async (file) => {
    setLoading(true);
    try {
      await uploadImage(file, {
        name: file.name,
        image_type: 'custom',
        acquisition_date: new Date().toISOString().split('T')[0],
        center_lat: 0,
        center_lon: 0
      });
      fetchImages(); // 刷新列表
    } catch (error) {
      console.error('上传失败:', error);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div>
      <h2>遥感影像管理</h2>
      <input 
        type="file" 
        onChange={(e) => handleUpload(e.target.files[0])}
        disabled={loading}
      />
      
      <div>
        {images.map(image => (
          <div key={image.id}>
            <span>{image.name}</span>
            <button onClick={() => calculateIndices(image.id, ['ndvi', 'ndwi'])}>
              计算指数
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ImageUpload;
```

## 7. 错误处理

### 统一错误处理
```javascript
// 错误处理工具
const handleApiError = (error) => {
  if (error.response) {
    // 服务器返回错误
    const { status, data } = error.response;
    
    switch (status) {
      case 400:
        return `请求参数错误: ${data.error || '未知错误'}`;
      case 401:
        return '请先登录';
      case 403:
        return '权限不足';
      case 404:
        return '资源不存在';
      case 500:
        return '服务器内部错误';
      default:
        return `请求失败: ${status}`;
    }
  } else if (error.request) {
    // 网络错误
    return '网络连接失败，请检查网络设置';
  } else {
    // 其他错误
    return `请求配置错误: ${error.message}`;
  }
};
```

## 8. 开发调试

### 开发环境配置
```javascript
// 开发环境配置
const isDevelopment = process.env.NODE_ENV === 'development';

if (isDevelopment) {
  // 开发环境下的配置
  console.log('API Base URL:', API_BASE_URL);
  
  // 添加请求日志
  api.interceptors.request.use(request => {
    console.log('API Request:', request);
    return request;
  });
  
  api.interceptors.response.use(response => {
    console.log('API Response:', response);
    return response;
  });
}
```

这样配置后，前端就可以正常与后端API进行通信了！ 