"""Roborock洗衣机集成主模块。

本模块是Roborock洗衣机集成的核心入口点，负责处理配置条目的设置和卸载。
它初始化设备管理器，过滤洗衣机设备，并为每个设备创建数据更新协调器。
同时负责加载所有支持的平台（传感器、开关、按钮、选择器等）。
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from roborock.devices.device_manager import create_device_manager, UserParams, UserData
from roborock.exceptions import RoborockException, RoborockInvalidCredentials

from .const import CONF_COUNTRY_CODE, CONF_USER_DATA, CONF_BASE_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)

# 定义支持的平台列表
# 这些平台对应不同的实体类型，将在集成加载时被初始化
PLATFORMS: list[str] = ["sensor", "switch", "button", "select"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """异步设置Roborock洗衣机配置条目。
    
    这是Home Assistant集成的主要入口点。当用户添加集成或Home Assistant启动时调用此函数。
    它负责初始化设备管理器，发现洗衣机设备，并为每个设备创建数据更新协调器。
    
    Args:
        hass: Home Assistant核心实例
        entry: 配置条目对象，包含用户的配置信息
        
    Returns:
        bool: 如果成功设置返回True，否则抛出异常
        
    Raises:
        ConfigEntryAuthFailed: 当认证凭据无效时抛出
        ConfigEntryNotReady: 当无法获取设备数据时抛出
    """
    # 从配置条目中提取用户名和用户数据
    username = entry.data[CONF_USERNAME]
    user_data = UserData.from_dict(entry.data[CONF_USER_DATA])

    try:
        # 创建用户参数对象
        user_params = UserParams(
            username=username,
            user_data=user_data,
            base_url=entry.data[CONF_BASE_URL],
        )
        
        # 创建设备管理器实例
        device_manager = await create_device_manager(
            user_params,
            session=async_get_clientsession(hass)
        )
        
        # 获取所有设备列表
        devices = await device_manager.get_devices()

        # 过滤设备，仅包含洗衣机设备
        washer_devices = []
        device_duids = set()
        
        for device in devices:
            # 检查设备是否具有zeo特性，这表明它可能是一台洗衣机
            if hasattr(device, 'zeo') and device.zeo is not None:
                # 设备具有zeo特性，很可能是一台洗衣机
                if device.duid not in device_duids:
                    device_duids.add(device.duid)
                    washer_devices.append(device)
                    _LOGGER.info("添加洗衣机设备: %s (duid: %s)", device.name, device.duid)
                else:
                    _LOGGER.warning("发现重复设备，跳过: %s (duid: %s)", device.name, device.duid)
        
        _LOGGER.info("过滤后找到 %d 台洗衣机设备", len(washer_devices))

        # 为每个洗衣机设备创建一个数据更新协调器实例
        coordinators = {}
        from .coordinator import RoborockWasherDataUpdateCoordinator
        from .zeo_protocol import ZeoProtocol
        for device in washer_devices:
            # 创建Zeo协议实例
            zeo_protocol = ZeoProtocol(device)
            # 创建数据更新协调器
            coordinator = RoborockWasherDataUpdateCoordinator(hass, entry, device, zeo_protocol)
            coordinators[device.duid] = coordinator
        
        # 在hass数据中存储设备管理器和设备信息
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][entry.entry_id] = {
            "device_manager": device_manager,
            "devices": washer_devices,
            "coordinators": coordinators,
        }

        # 设置各个平台（传感器、开关、按钮、选择器等）
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        return True
    except RoborockInvalidCredentials as err:
        # 认证凭据无效时抛出配置条目认证失败异常
        raise ConfigEntryAuthFailed("无效的认证凭据") from err
    except RoborockException as err:
        # Roborock相关异常处理
        _LOGGER.debug("获取Roborock洗衣机数据失败: %s", err)
        raise ConfigEntryNotReady("获取Roborock洗衣机数据失败") from err
    except Exception as ex:
        # 其他异常处理
        _LOGGER.exception("设置Roborock洗衣机时发生错误")
        raise ConfigEntryNotReady from ex


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """异步卸载配置条目。
    
    当用户删除集成或Home Assistant关闭时调用此函数。
    它负责卸载所有已加载的平台并清理相关的数据。
    
    Args:
        hass: Home Assistant核心实例
        entry: 要卸载的配置条目对象
        
    Returns:
        bool: 如果成功卸载返回True，否则返回False
    """
    # 卸载所有平台
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # 从hass数据中移除该配置条目的信息
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok