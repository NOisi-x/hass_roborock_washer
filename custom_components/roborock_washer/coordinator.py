"""Roborock Washer Coordinator.

负责管理与Roborock洗衣机设备的数据通信和状态同步。
该协调器处理设备数据的获取、缓存和更新，并根据不同的协议类型采用不同的更新策略。
"""
from __future__ import annotations

from datetime import timedelta, datetime
import logging
from typing import Any, Dict

from roborock.exceptions import RoborockException
from roborock.roborock_message import RoborockZeoProtocol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    UPDATE_INTERVAL_FREQUENT,
    UPDATE_INTERVAL_INFREQUENT
)

_LOGGER = logging.getLogger(__name__)



class RoborockWasherDataUpdateCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Roborock洗衣机数据更新协调器类。

    负责从API获取Roborock洗衣机数据，管理数据缓存，并根据协议类型采用不同的更新频率策略。
    协调器还处理设备命令发送和特定协议查询。
    """

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, device, api
    ) -> None:
        """初始化协调器。

        Args:
            hass: Home Assistant实例
            entry: 配置条目
            device: 设备对象
            api: 设备API接口
        """
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL_FREQUENT,  # 默认使用频繁更新间隔
            config_entry=entry,
        )
        # 设备对象引用
        self._device = device
        # Zeo API接口用于与设备通信
        self.zeo_api = api
        # 存储当前设备数据
        self.data = {}
        # 获取设备型号
        self._model = device.product.model if hasattr(device, 'product') else getattr(device, 'model', 'Unknown')
        # 设备信息，用于在Home Assistant中注册设备
        self.device_info = DeviceInfo(
            identifiers={((DOMAIN, device.duid))},
            name=device.name,
            manufacturer="Roborock",
            model=self._model,
            sw_version=getattr(device.device_info, 'fw_ver', getattr(device, 'firmware_version', 'Unknown')),
        )
        # 设备唯一标识符
        self._duid = device.duid
        # 上次设备状态缓存
        self._last_state = None
        
        # 定义不同更新频率的协议组
        # 频繁更新协议（每分钟更新一次）
        self.frequent_protocols = [
            RoborockZeoProtocol.STATE,          # 设备状态
            RoborockZeoProtocol.WASHING_LEFT,   # 剩余洗涤时间
            # RoborockZeoProtocol.DOORLOCK_STATE,  # 不支持
            RoborockZeoProtocol.COUNTDOWN       # 倒计时
        ]
        
        # 不频繁更新协议（每6小时更新一次）
        self.infrequent_protocols = [
            RoborockZeoProtocol.ERROR,              # 错误信息
            # RoborockZeoProtocol.CUSTOM_PARAM_GET,  # 不支持
            RoborockZeoProtocol.TIMES_AFTER_CLEAN,  # 清洁后次数
            RoborockZeoProtocol.DETERGENT_EMPTY,    # 洗涤剂空状态
            # RoborockZeoProtocol.SOFTENER_EMPTY  # 不支持
        ]
        
        # 手动操作协议（仅通过按钮触发更新）
        self.manual_protocols = [
            RoborockZeoProtocol.START,          # 启动
            RoborockZeoProtocol.PAUSE,          # 暂停
            RoborockZeoProtocol.SHUTDOWN,       # 关机
            RoborockZeoProtocol.MODE,           # 模式
            RoborockZeoProtocol.PROGRAM,        # 程序
            # RoborockZeoProtocol.CHILD_LOCK,  # 不支持
            RoborockZeoProtocol.TEMP,           # 温度
            RoborockZeoProtocol.RINSE_TIMES,    # 漂洗次数
            RoborockZeoProtocol.SPIN_LEVEL,     # 脱水转速
            RoborockZeoProtocol.DRYING_MODE,    # 烘干模式
            # RoborockZeoProtocol.DETERGENT_SET,  # 不支持
            # RoborockZeoProtocol.SOFTENER_SET,  # 不支持
            RoborockZeoProtocol.DETERGENT_TYPE, # 洗涤剂类型
            # RoborockZeoProtocol.SOFTENER_TYPE,  # 不支持
            # RoborockZeoProtocol.CUSTOM_PARAM_SAVE,  # 不支持
            RoborockZeoProtocol.SOUND_SET,      # 声音设置
            # RoborockZeoProtocol.DEFAULT_SETTING,  # 不支持
            # RoborockZeoProtocol.LIGHT_SETTING  # 不支持
        ]
        
        # 初始加载时需要更新的所有协议
        self.all_protocols = self.frequent_protocols + self.infrequent_protocols + self.manual_protocols
        
        # 状态缓存和上次更新时间戳
        self._state_cache: Dict[str, Any] = {}  # 缓存各协议的状态值
        self._last_update_times: Dict[str, datetime] = {}  # 记录每个协议的最后更新时间
        
        # 初始加载状态标志
        self._initial_load_complete = False  # 初始加载是否完成
        self._initial_load_started = False   # 初始加载是否已开始

    @property
    def device(self):
        """Return the device."""
        return self._device

    @property
    def duid(self):
        """Return the device unique ID."""
        return self._duid

    @property
    def model(self):
        """Return the device model."""
        return self._model

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from Roborock API."""
        _LOGGER.debug("Starting async update data for device %s", self._duid)
        _LOGGER.debug("Current cache: %s", self._state_cache)
        
        try:
            all_results = {}
            current_time = datetime.now()
            
            # On initial load, update all protocols one by one
            if not self._initial_load_complete:
                # Mark initial load as started
                if not self._initial_load_started:
                    self._initial_load_started = True
                    _LOGGER.info("Starting initial load for device %s", self._duid)
                
                _LOGGER.info("Performing initial load: updating all protocols one by one")
                
                # Process all protocols individually during initial load, except START, PAUSE, SHUTDOWN which only support set_value
                for protocol in self.all_protocols:
                    if protocol in [RoborockZeoProtocol.START, RoborockZeoProtocol.PAUSE, RoborockZeoProtocol.SHUTDOWN]:
                        _LOGGER.debug("Initial load: Skipping protocol %s which only supports set_value", protocol.name.lower())
                        continue
                    protocol_str = protocol.name.lower() if hasattr(protocol, 'name') else str(protocol).lower()
                    _LOGGER.debug("Initial load: Processing protocol %s", protocol_str)
                    
                    try:
                        result = await self.zeo_api.query_values([protocol])
                        _LOGGER.debug("Initial load: Raw query result for protocol %s: %s", protocol_str, result)
                        _LOGGER.debug("Initial load: Raw query type for protocol %s: %s", protocol_str, type(result))
                        
                        # Process the result
                        if isinstance(result, dict) and protocol in result:
                            protocol_result = result[protocol]
                        elif isinstance(result, list) and len(result) == 1:
                            protocol_result = result[0]
                        else:
                            protocol_result = result
                        _LOGGER.debug("Initial load: Processed result for protocol %s: %s (type: %s)", protocol_str, protocol_result, type(protocol_result))
                        
                        # Convert boolean-like protocol values to actual booleans
                        boolean_protocols = [
                            # RoborockZeoProtocol.DOORLOCK_STATE,  # 不支持
                            # RoborockZeoProtocol.LIGHT_SETTING,  # 不支持
                            RoborockZeoProtocol.SOUND_SET,
                            # RoborockZeoProtocol.CHILD_LOCK,  # 不支持
                            # RoborockZeoProtocol.DETERGENT_SET,  # 不支持
                            # RoborockZeoProtocol.SOFTENER_SET  # 不支持
                        ]
                        
                        if protocol in boolean_protocols and protocol_result is not None:
                            protocol_result = bool(int(protocol_result)) if isinstance(protocol_result, str) else bool(protocol_result)
                        
                        all_results[protocol_str] = protocol_result
                        self._last_update_times[protocol_str] = current_time
                        _LOGGER.info("Initial load: Updated protocol %s with value: %s", protocol_str, protocol_result)
                    except Exception as err:
                        _LOGGER.error("Initial load: Error querying protocol %s: %s", protocol_str, err)
                        continue
                
                self._initial_load_complete = True
                _LOGGER.info("Initial load completed successfully")
            else:
                # Normal update: process protocols based on their update intervals
                
                # Process frequent protocols (every 60 seconds)
                _LOGGER.debug("Processing frequent protocols")
                for protocol in self.frequent_protocols:
                    protocol_str = protocol.name.lower() if hasattr(protocol, 'name') else str(protocol).lower()
                    last_update = self._last_update_times.get(protocol_str)
                    
                    if not last_update or (current_time - last_update) >= UPDATE_INTERVAL_FREQUENT:
                        try:
                            result = await self.zeo_api.query_values([protocol])
                            _LOGGER.debug("Frequent protocol: Raw query result for %s: %s", protocol_str, result)
                            _LOGGER.debug("Frequent protocol: Raw query type for %s: %s", protocol_str, type(result))
                            
                            # Process the result
                            if isinstance(result, dict) and protocol in result:
                                protocol_result = result[protocol]
                            elif isinstance(result, list) and len(result) == 1:
                                protocol_result = result[0]
                            else:
                                protocol_result = result
                            _LOGGER.debug("Frequent protocol: Processed result for %s: %s (type: %s)", protocol_str, protocol_result, type(protocol_result))
                            
                            # Convert boolean-like protocol values to actual booleans
                            boolean_protocols = [
                                # RoborockZeoProtocol.DOORLOCK_STATE,  # 不支持
                            ]
                            
                            if protocol in boolean_protocols and protocol_result is not None:
                                protocol_result = bool(int(protocol_result)) if isinstance(protocol_result, str) else bool(protocol_result)
                            
                            all_results[protocol_str] = protocol_result
                            self._last_update_times[protocol_str] = current_time
                            _LOGGER.info("Updated frequent protocol %s with value: %s", protocol_str, protocol_result)
                        except Exception as err:
                            _LOGGER.error("Error querying frequent protocol %s: %s", protocol_str, err)
                            continue
                    else:
                        _LOGGER.debug("Skipping frequent protocol %s, last updated %s ago", 
                                     protocol_str, current_time - last_update)
                
                # Process infrequent protocols (every 6 hours)
                _LOGGER.debug("Processing infrequent protocols")
                for protocol in self.infrequent_protocols:
                    protocol_str = protocol.name.lower() if hasattr(protocol, 'name') else str(protocol).lower()
                    last_update = self._last_update_times.get(protocol_str)
                    
                    if not last_update or (current_time - last_update) >= UPDATE_INTERVAL_INFREQUENT:
                        try:
                            result = await self.zeo_api.query_values([protocol])
                            _LOGGER.debug("Infrequent protocol: Raw query result for %s: %s", protocol_str, result)
                            _LOGGER.debug("Infrequent protocol: Raw query type for %s: %s", protocol_str, type(result))
                            
                            # Process the result
                            if isinstance(result, dict) and protocol in result:
                                protocol_result = result[protocol]
                            elif isinstance(result, list) and len(result) == 1:
                                protocol_result = result[0]
                            else:
                                protocol_result = result
                            _LOGGER.debug("Infrequent protocol: Processed result for %s: %s (type: %s)", protocol_str, protocol_result, type(protocol_result))
                            
                            all_results[protocol_str] = protocol_result
                            self._last_update_times[protocol_str] = current_time
                            _LOGGER.info("Updated infrequent protocol %s with value: %s", protocol_str, protocol_result)
                        except Exception as err:
                            _LOGGER.error("Error querying infrequent protocol %s: %s", protocol_str, err)
                            continue
                    else:
                        _LOGGER.debug("Skipping infrequent protocol %s, last updated %s ago", 
                                     protocol_str, current_time - last_update)
                
                # Manual protocols are only updated when the button is pressed, so skip them here
                _LOGGER.debug("Skipping manual protocols (updated only via button)")
            
            # Update cache
            _LOGGER.debug("Final results before cache update: %s", all_results)
            if all_results:
                _LOGGER.debug("Updating cache with %d new results", len(all_results))
                self._state_cache.update(all_results)
                _LOGGER.debug("Cache after update: %s", self._state_cache)
            else:
                _LOGGER.debug("No results from any query, keeping existing cache")
            
            return all_results or self._state_cache
        except Exception as err:
            _LOGGER.exception("Unexpected error updating Roborock Washer data")
            # Return cached data on failure to avoid entities showing unknown
            return self._state_cache

    def get_cached_value(self, protocol: str) -> Any:
        """Get cached value for a protocol."""
        # 统一转换为小写，以匹配缓存中的键名格式
        protocol_key = protocol.lower()
        value = self._state_cache.get(protocol_key)
        _LOGGER.debug("Getting cached value for protocol %s (key: %s): %s", protocol, protocol_key, value)
        return value
    
    async def async_send_command(self, protocol: str, value: Any = None) -> None:
        """Send a command to the device."""
        try:
            protocol_enum = getattr(RoborockZeoProtocol, protocol, None)
            if protocol_enum is None:
                raise ValueError(f"Unknown protocol: {protocol}")
            
            # 操作命令也需要传递值，即使是None
            await self.zeo_api.set_value(protocol_enum, value)
            # 强制更新数据
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to send command %s: %s", protocol, err)
            raise
    

    
    async def async_query_protocol(self, protocol_name: str) -> Any:
        """Query a specific protocol and update cache."""
        _LOGGER.info("Querying specific protocol: %s", protocol_name)
        
        try:
            # Find the protocol enum
            protocol_enum = getattr(RoborockZeoProtocol, protocol_name.upper(), None)
            if protocol_enum is None:
                raise ValueError(f"Unknown protocol: {protocol_name}")
            
            # Query the protocol
            result = await self.zeo_api.query_values([protocol_enum])
            _LOGGER.debug("Raw query result for protocol %s: %s", protocol_name, result)
            
            # Process the result
            if isinstance(result, dict) and protocol_enum in result:
                protocol_result = result[protocol_enum]
            elif isinstance(result, list) and len(result) == 1:
                protocol_result = result[0]
            else:
                protocol_result = result
            
            _LOGGER.debug("Processed result for protocol %s: %s (type: %s)", protocol_name, protocol_result, type(protocol_result))
            
            # Convert boolean-like protocol values to actual booleans for specific protocols
            boolean_protocols = [
                "sound_set",
            ]
            
            if protocol_name in boolean_protocols and protocol_result is not None:
                protocol_result = bool(int(protocol_result)) if isinstance(protocol_result, str) else bool(protocol_result)
            
            # Update cache
            self._state_cache[protocol_name] = protocol_result
            self._last_update_times[protocol_name] = datetime.now()
            _LOGGER.info("Updated cache for protocol %s with value: %s", protocol_name, protocol_result)
            
            # Update coordinator data and notify listeners
            self.data[protocol_name] = protocol_result
            self.async_update_listeners()
            
            return protocol_result
        except Exception as err:
            _LOGGER.error("Error querying protocol %s: %s", protocol_name, err)
            raise
