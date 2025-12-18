"""Roborock洗衣机传感器平台模块。

本模块实现了Roborock洗衣机的传感器实体，用于显示设备的各种状态信息。
这些传感器通过Zeo协议与设备通信，实时获取并展示设备的工作状态、倒计时、温度等关键信息。
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfTime,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import RoborockWasherDataUpdateCoordinator
from .entity import RoborockWasherApiEntity

_LOGGER = logging.getLogger(__name__)

# 定义Zeo协议值作为字符串，使用小写以匹配coordinator中的存储格式
# 设备基本状态协议
STATE = "state"              # 设备当前状态
COUNTDOWN = "countdown"      # 倒计时时间（分钟）
WASHING_LEFT = "washing_left"  # 剩余洗涤时间（分钟）
ERROR = "error"              # 错误状态
# DOORLOCK_STATE = "doorlock_state"  # 门锁状态（不支持）
TEMP = "temp"                # 温度
SPIN_LEVEL = "spin_level"    # 脱水等级
# CHILD_LOCK = "child_lock"    # 儿童锁（不支持）
SOUND_SET = "sound_set"      # 声音设置
# DETERGENT_SET = "detergent_set"  # 洗涤剂设置（不支持）
# SOFTENER_SET = "softener_set"    # 柔顺剂设置（不支持）
# LIGHT_SETTING = "light_setting"  # 灯光设置（不支持）
DETERGENT_TYPE = "detergent_type"      # 洗涤剂类型
# SOFTENER_TYPE = "softener_type"      # 柔顺剂类型（不支持）
TIMES_AFTER_CLEAN = "times_after_clean"  # 清洁后使用次数
DETERGENT_EMPTY = "detergent_empty"    # 洗涤剂空状态
# SOFTENER_EMPTY = "softener_empty"    # 柔顺剂空状态（不支持）
# CUSTOM_PARAM_GET = "custom_param_get"  # 自定义参数获取（不支持）
DRYING_MODE = "drying_mode"            # 烘干模式
RINSE_TIMES = "rinse_times"            # 漂洗次数
START = "start"              # 启动
PAUSE = "pause"              # 暂停
SHUTDOWN = "shutdown"        # 关机
MODE = "mode"                # 模式
PROGRAM = "program"          # 程序
# CUSTOM_PARAM_SAVE = "custom_param_save"  # 自定义参数保存（不支持）
# DEFAULT_SETTING = "default_setting"      # 默认设置（不支持）

# 定义所有支持的传感器实体描述
# 每个传感器描述包含关键属性：唯一标识符、图标、单位、设备类别、状态类别和翻译键
SENSOR_DESCRIPTIONS: list[SensorEntityDescription] = [
    # 设备状态传感器
    SensorEntityDescription(
        key=STATE,                           # 传感器唯一标识符
        icon="mdi:washing-machine",          # 传感器图标
        translation_key="state",             # 翻译键
    ),
    
    # 倒计时传感器
    SensorEntityDescription(
        key=COUNTDOWN,                       # 传感器唯一标识符
        icon="mdi:timer-outline",            # 传感器图标
        native_unit_of_measurement=UnitOfTime.MINUTES,  # 单位：分钟
        translation_key="countdown",         # 翻译键
    ),
    
    # 剩余洗涤时间传感器
    SensorEntityDescription(
        key=WASHING_LEFT,                    # 传感器唯一标识符
        icon="mdi:progress-clock",           # 传感器图标
        native_unit_of_measurement=UnitOfTime.MINUTES,  # 单位：分钟
        translation_key="washing_left",      # 翻译键
    ),
    
    # 错误状态传感器
    SensorEntityDescription(
        key=ERROR,                           # 传感器唯一标识符
        icon="mdi:alert-circle",             # 传感器图标
        translation_key="error",             # 翻译键
    ),
    
    # 清洁后使用次数传感器
    SensorEntityDescription(
        key=TIMES_AFTER_CLEAN,               # 传感器唯一标识符
        icon="mdi:counter",                  # 传感器图标
        state_class=SensorStateClass.MEASUREMENT,  # 测量状态类别
        translation_key="times_after_clean", # 翻译键
    ),
    
    # 洗涤剂空状态传感器
    SensorEntityDescription(
        key=DETERGENT_EMPTY,                 # 传感器唯一标识符
        icon="mdi:alert",                    # 传感器图标
        translation_key="detergent_empty",   # 翻译键
    ),
    
    # 烘干模式传感器
    SensorEntityDescription(
        key=DRYING_MODE,                     # 传感器唯一标识符
        icon="mdi:tumble-dryer",             # 传感器图标
        translation_key="drying_mode",       # 翻译键
    ),
    
    # 声音设置传感器
    SensorEntityDescription(
        key=SOUND_SET,                       # 传感器唯一标识符
        icon="mdi:volume-high",              # 传感器图标
        translation_key="sound_set",         # 翻译键
    ),
    
    # 温度传感器
    SensorEntityDescription(
        key=TEMP,                            # 传感器唯一标识符
        icon="mdi:thermometer",              # 传感器图标
        translation_key="temp",              # 翻译键
    ),
    
    # 脱水等级传感器
    SensorEntityDescription(
        key=SPIN_LEVEL,                      # 传感器唯一标识符
        icon="mdi:rotate-left",              # 传感器图标
        translation_key="spin_level",        # 翻译键
    ),
    
    # 洗涤剂类型传感器
    SensorEntityDescription(
        key=DETERGENT_TYPE,                  # 传感器唯一标识符
        icon="mdi:bottle-tonic-outline",     # 传感器图标
        translation_key="detergent_type",    # 翻译键
    ),
    
    # 漂洗次数传感器
    SensorEntityDescription(
        key=RINSE_TIMES,                     # 传感器唯一标识符
        icon="mdi:water-outline",            # 传感器图标
        translation_key="rinse_times",       # 翻译键
    ),
    
    # 模式传感器
    SensorEntityDescription(
        key=MODE,                            # 传感器唯一标识符
        icon="mdi:tune",                     # 传感器图标
        translation_key="mode",              # 翻译键
    ),
    
    # 程序传感器
    SensorEntityDescription(
        key=PROGRAM,                         # 传感器唯一标识符
        icon="mdi:playlist-play",            # 传感器图标
        translation_key="program",           # 翻译键
    ),
]

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """根据配置条目设置Roborock洗衣机的传感器实体。
    
    该函数是Home Assistant平台加载集成时的入口点，负责为每个连接的设备创建相应的传感器实体。
    
    Args:
        hass: Home Assistant核心实例
        config_entry: 配置条目对象，包含集成的配置信息
        async_add_entities: 异步添加实体的回调函数
    """
    # 从HA数据中获取设备和协调器信息
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    devices = entry_data["devices"]
    coordinators = entry_data["coordinators"]

    # 创建实体列表
    entities: list[RoborockWasherSensor] = []
    # 为每个设备创建传感器实体
    for device in devices:
        # 获取该设备的共享协调器
        coordinator = coordinators[device.duid]
        
        # 为每种传感器实体描述创建实体实例
        for description in SENSOR_DESCRIPTIONS:
            entities.append(RoborockWasherSensor(coordinator, description))

    # 将所有实体添加到Home Assistant
    async_add_entities(entities)
    _LOGGER.info("已添加 %d 个Roborock洗衣机传感器", len(entities))


class RoborockWasherSensor(RoborockWasherApiEntity, SensorEntity):
    """Roborock洗衣机传感器实体的实现类。
    
    该类继承自RoborockWasherApiEntity和Home Assistant的SensorEntity，
    实现了与Roborock洗衣机设备交互的传感器实体功能，用于显示设备的各种状态信息。
    """

    def __init__(self, coordinator: RoborockWasherDataUpdateCoordinator, description: SensorEntityDescription) -> None:
        """初始化Roborock洗衣机传感器实体。
        
        Args:
            coordinator: 设备数据更新协调器实例
            description: 传感器实体描述对象，定义传感器的配置信息
        """
        # 调用父类初始化方法，传入协调器和关联的协议
        super().__init__(coordinator, description.key)
        # 保存实体描述对象
        self.entity_description = description
        # 设置实体的唯一标识符
        self._attr_unique_id = f"{coordinator.model}_{description.key}"
    
    @property
    def native_value(self) -> Optional[Any]:
        """获取传感器的原生值。
        
        返回传感器的当前状态值。对于具有测量单位的传感器，当值为None或"not set"时返回None，
        以确保数值型传感器不会返回字符串值。
        
        Returns:
            Optional[Any]: 传感器的当前值，如果无法获取则返回None
        """
        # 获取传感器状态值
        value = self.get_state()
        # 对于具有测量单位的传感器，如果值为None则返回None
        # 这确保了数值型传感器不会返回字符串值
        if value is None or value == "not set":
            return None
        # 如果值为空字典也返回None
        if isinstance(value, dict) and not value:
            return None
        # 返回实际值
        return value
    
    @property
    def available(self) -> bool:
        """检查传感器实体是否可用。
        
        传感器的可用性基于协调器的最后更新状态。如果协调器最后一次更新成功，
        则认为传感器是可用的；否则传感器将显示为不可用状态。
        
        Returns:
            bool: 如果传感器可用返回True，否则返回False
        """
        return self.coordinator.last_update_success