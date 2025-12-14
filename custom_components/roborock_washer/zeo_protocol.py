"""Roborock洗衣机集成的Zeo协议实现模块。

本模块实现了与Roborock洗衣机设备通信的Zeo协议接口。
它提供了查询设备状态和设置设备值的功能，是设备与Home Assistant之间通信的桥梁。
"""

import json
import logging
from typing import Any

from roborock.roborock_message import RoborockZeoProtocol

_LOGGER = logging.getLogger(__name__)


class ZeoProtocol:
    """Roborock洗衣机Zeo协议的实现类。
    
    该类封装了与Roborock洗衣机设备通信的Zeo协议方法，
    提供了查询多个协议值和设置单个协议值的接口。
    """

    def __init__(self, device) -> None:
        """初始化Zeo协议处理器。
        
        Args:
            device: Roborock设备实例，必须支持Zeo协议
        """
        # 保存设备实例引用
        self._device = device

    async def query_values(self, protocols: list[RoborockZeoProtocol]) -> dict[RoborockZeoProtocol, Any]:
        """异步查询设备指定协议的值。
        
        向设备发送查询请求，获取指定协议的当前状态值。
        如果设备不支持Zeo协议，则记录警告日志并返回空字典。
        
        Args:
            protocols: 要查询的协议列表
            
        Returns:
            dict[RoborockZeoProtocol, Any]: 协议与其对应值的映射字典，
                                           如果查询失败则返回空字典
        """
        # 检查设备是否支持Zeo协议
        if not hasattr(self._device, 'zeo') or self._device.zeo is None:
            _LOGGER.warning("设备不支持Zeo协议")
            return {}
        
        try:
            # 执行实际的查询操作
            result = await self._device.zeo.query_values(protocols)
            _LOGGER.debug("Zeo协议查询结果，协议列表 %s: %s", protocols, result)
            return result
        except Exception as e:
            # 处理查询过程中的异常
            _LOGGER.error("查询Zeo值失败: %s", e)
            return {}

    async def set_value(self, protocol: RoborockZeoProtocol, value: Any) -> dict[RoborockZeoProtocol, Any]:
        """异步设置设备指定协议的值。
        
        向设备发送设置命令，将指定协议的值设置为给定值。
        如果设备不支持Zeo协议，则记录警告日志并返回空字典。
        
        Args:
            protocol: 要设置的协议
            value: 要设置的值
            
        Returns:
            dict[RoborockZeoProtocol, Any]: 设置操作的结果，
                                           如果设置失败则返回空字典
        """
        # 检查设备是否支持Zeo协议
        if not hasattr(self._device, 'zeo') or self._device.zeo is None:
            _LOGGER.warning("设备不支持Zeo协议")
            return {}
        
        try:
            # 执行实际的设置操作
            return await self._device.zeo.set_value(protocol, value)
        except Exception as e:
            # 处理设置过程中的异常
            _LOGGER.error("设置Zeo值失败: %s", e)
            return {}