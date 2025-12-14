"""Roborock洗衣机集成的基础实体模块。

本模块定义了Roborock洗衣机集成中所有实体类型的基类，提供了与设备通信和数据同步的核心功能。
包括基础实体类和API实体类，为具体的功能实体（如传感器、开关等）提供通用的实现。
"""

from __future__ import annotations

import logging
from typing import Any

from roborock.roborock_message import RoborockZeoProtocol

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RoborockWasherDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class RoborockWasherEntity(CoordinatorEntity[RoborockWasherDataUpdateCoordinator]):
    """Roborock洗衣机实体的基类。
    
    这个基类继承自Home Assistant的CoordinatorEntity，为所有Roborock洗衣机实体提供通用功能。
    它主要处理设备信息和协调器的初始化，确保所有子类实体都能正确地与设备关联。
    """

    # 实体具有名称属性，允许使用翻译键
    _attr_has_entity_name = True
    # 实体不需要轮询，由协调器统一管理数据更新
    _attr_should_poll = False

    def __init__(self, coordinator: RoborockWasherDataUpdateCoordinator) -> None:
        """初始化Roborock洗衣机实体。
        
        Args:
            coordinator: 设备数据更新协调器实例，负责管理设备数据的获取和更新
        """
        # 调用父类初始化方法
        super().__init__(coordinator)
        # 保存设备实例引用
        self._device = coordinator.device
        # 保存协调器实例引用
        self._coordinator = coordinator

    @property
    def device_info(self) -> DeviceInfo:
        """获取设备信息。
        
        返回与该实体关联的设备信息，包括设备标识符、制造商、型号等，
        用于在Home Assistant中正确识别和分组设备。
        
        Returns:
            DeviceInfo: 包含设备详细信息的对象
        """
        return self._coordinator.device_info


class RoborockWasherApiEntity(RoborockWasherEntity):
    """使用API的Roborock洗衣机实体基类。
    
    这个基类扩展了RoborockWasherEntity，专门用于需要与设备API交互的实体。
    它提供了获取设备状态和设置设备值的通用方法，处理协议转换和数据类型转换。
    """

    def __init__(self, coordinator: RoborockWasherDataUpdateCoordinator, protocol: str) -> None:
        """初始化Roborock洗衣机API实体。
        
        Args:
            coordinator: 设备数据更新协调器实例
            protocol: 与该实体关联的设备协议标识符
        """
        # 调用父类初始化方法
        super().__init__(coordinator)
        # 保存协议标识符
        self._protocol = protocol

    def get_state(self) -> Any:
        """获取实体协议的当前状态。
        
        该方法优先使用协调器的缓存机制来获取状态值，以提高性能并减少设备查询次数。
        如果缓存不可用，则回退到直接从协调器数据中获取。
        
        Returns:
            Any: 协议定义的原始值，可能是字符串、数字或其他类型
        """
        # 协议名称统一转换为小写，以匹配缓存中的键名格式
        protocol_key = self._protocol.lower()
        
        # 优先使用协调器的缓存机制
        if hasattr(self.coordinator, 'get_cached_value'):
            value = self.coordinator.get_cached_value(protocol_key)
            _LOGGER.debug("从缓存中获取协议 %s 的状态: %s", protocol_key, value)
        # 回退到直接从data获取
        else:
            value = self.coordinator.data.get(protocol_key)
            _LOGGER.debug("从数据中获取协议 %s 的状态: %s", protocol_key, value)
        
        # 返回协议定义的原始字符串值，不进行额外转换
        _LOGGER.debug("返回协议 %s 的原始值: %s", self._protocol, value)
        return value

    async def async_set_value(self, value: Any) -> None:
        """异步设置实体协议的值。
        
        向设备发送指定值的命令，处理必要的数据类型转换，并在设置完成后强制刷新数据。
        对于某些协议，需要将布尔值或字符串值转换为设备期望的整数值。
        
        Args:
            value: 要设置给设备的值，可以是多种数据类型
            
        Raises:
            ValueError: 当协议未知或值转换失败时抛出异常
            Exception: 当设置值过程中发生其他错误时抛出异常
        """
        try:
            _LOGGER.debug("正在为协议 %s 设置值: %s", self._protocol, value)
            # 使用官方依赖库中的RoborockZeoProtocol获取协议枚举
            protocol_enum = getattr(RoborockZeoProtocol, self._protocol, None)
            if protocol_enum is None:
                raise ValueError(f"未知协议: {self._protocol}")
            
            # 将布尔值或字符串值转换为整数值，因为设备可能需要整数值而不是布尔值或字符串
            protocol_key = self._protocol.lower()
            # 定义需要整数值的协议列表
            integer_protocols = ["sound_set", "start", "pause", "shutdown"]  # "light_setting", "child_lock", "detergent_set", "softener_set" 不支持
            
            if protocol_key in integer_protocols:
                if isinstance(value, bool):
                    # 将布尔值转换为整数
                    value = 1 if value else 0
                    _LOGGER.debug("为协议 %s 将布尔值转换为整数: %s", protocol_key, value)
                elif isinstance(value, str):
                    # 将字符串值转换为整数
                    try:
                        value = int(value)
                        _LOGGER.debug("为协议 %s 将字符串值转换为整数: %s", protocol_key, value)
                    except ValueError:
                        _LOGGER.error("为协议 %s 转换字符串值到整数失败: %s", protocol_key, value)
                        raise
            
            _LOGGER.debug("找到协议枚举: %s，值为 %s", protocol_enum, protocol_enum.value)
            # 执行实际的设备控制命令
            result = await self._coordinator.zeo_api.set_value(protocol_enum, value)
            _LOGGER.debug("设置值的结果: %s", result)
            # 强制更新数据以反映设备状态变化
            await self._coordinator.async_request_refresh()
            _LOGGER.debug("设置值后刷新了数据")
        except Exception as err:
            _LOGGER.error("为 %s 设置值失败: %s", self._protocol, err)
            raise