from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """用户模型"""
    ROLE_CHOICES = [
        ('admin', '管理员'),
        ('user', '普通用户'),
        ('expert', '专家'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user', verbose_name='用户角色')
    phone = models.CharField(max_length=11, blank=True, null=True, verbose_name='手机号')
    organization = models.CharField(max_length=100, blank=True, null=True, verbose_name='所属机构')
    department = models.CharField(max_length=100, blank=True, null=True, verbose_name='部门')
    position = models.CharField(max_length=50, blank=True, null=True, verbose_name='职位')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='头像')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'
        db_table = 'users'
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class UserPermission(models.Model):
    """用户权限模型"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    module = models.CharField(max_length=50, verbose_name='模块')
    permission = models.CharField(max_length=50, verbose_name='权限')
    granted = models.BooleanField(default=True, verbose_name='是否授权')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '用户权限'
        verbose_name_plural = '用户权限'
        db_table = 'user_permissions'
        unique_together = ['user', 'module', 'permission']
    
    def __str__(self):
        return f"{self.user.username} - {self.module}.{self.permission}"


class UserSession(models.Model):
    """用户会话模型"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    session_key = models.CharField(max_length=40, verbose_name='会话键')
    ip_address = models.GenericIPAddressField(verbose_name='IP地址')
    user_agent = models.TextField(verbose_name='用户代理')
    login_time = models.DateTimeField(auto_now_add=True, verbose_name='登录时间')
    logout_time = models.DateTimeField(blank=True, null=True, verbose_name='登出时间')
    is_active = models.BooleanField(default=True, verbose_name='是否活跃')
    
    class Meta:
        verbose_name = '用户会话'
        verbose_name_plural = '用户会话'
        db_table = 'user_sessions'
    
    def __str__(self):
        return f"{self.user.username} - {self.login_time}" 