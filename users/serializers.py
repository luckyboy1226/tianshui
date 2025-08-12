from rest_framework import serializers
from .models import User, UserPermission, UserSession


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'role', 'role_display',
            'phone', 'organization', 'department', 'position', 'avatar',
            'is_active', 'date_joined', 'last_login'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']


class UserCreateSerializer(serializers.ModelSerializer):
    """用户创建序列化器"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm', 'first_name', 'last_name',
            'role', 'phone', 'organization', 'department', 'position'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("密码确认不匹配")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """用户更新序列化器"""
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'organization',
            'department', 'position', 'avatar'
        ]


class UserPermissionSerializer(serializers.ModelSerializer):
    """用户权限序列化器"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserPermission
        fields = ['id', 'user', 'module', 'permission', 'granted', 'created_at']
        read_only_fields = ['id', 'created_at']


class UserSessionSerializer(serializers.ModelSerializer):
    """用户会话序列化器"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserSession
        fields = [
            'id', 'user', 'session_key', 'ip_address', 'user_agent',
            'login_time', 'logout_time', 'is_active'
        ]
        read_only_fields = ['id', 'login_time'] 