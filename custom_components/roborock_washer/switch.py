"""Roborock洗衣机开关实体平台模块。

本模块实现了Roborock洗衣机的开关型实体，允许用户通过Home Assistant界面控制设备的各种开关功能，
如声音设置等。这些实体与设备的协议层进行交互，将用户的开关操作转换为设备可以理解的指令，
并能实时反映设备的当前开关状态。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import RoborockWasherDataUpdateCoordinator
from .entity import RoborockWasherApiEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class RoborockWasherSwitchDescription(SwitchEntityDescription):
    """Roborock洗衣机开关实体描述类。
    
    该类扩展了Home Assistant的SwitchEntityDescription，为Roborock洗衣机的开关实体提供了额外的描述信息。
    主要用于定义每个开关实体的协议类型和开关值映射关系。
    """
    # 与该开关实体关联的设备协议标识符
    data_protocol: str
    # 开关打开时设置给设备的值
    setter_value_on: Any = True
    # 开关关闭时设置给设备的值
    setter_value_off: Any = False
    # 翻译键，用于从翻译文件中获取实体名称
    translation_key: str | None = None


# 定义设备协议常量
# 儿童锁协议标识符（当前不支持）
# CHILD_LOCK = "CHILD_LOCK"  # 不支持
# 声音设置协议标识符
SOUND_SET = "SOUND_SET"
# 洗涤剂设置协议标识符（当前不支持）
# DETERGENT_SET = "DETERGENT_SET"  # 不支持
# 柔顺剂设置协议标识符（当前不支持）
# SOFTENER_SET = "SOFTENER_SET"  # 不支持
# 灯光设置协议标识符（当前不支持）
# LIGHT_SETTING = "LIGHT_SETTING"  # 不支持

# 定义所有支持的开关实体类型
# 每个实体描述包含关键属性：唯一标识符、图标、设备类别、关联协议和开关值映射
SWITCH_TYPES: tuple[RoborockWasherSwitchDescription, ...] = (
    # 儿童锁开关实体（当前被注释掉，表示暂不支持）
    # RoborockWasherSwitchDescription(
    #     key="child_lock",              # 实体唯一标识符
    #     name=None,                     # 使用翻译文件中的名称
    #     icon="mdi:lock",               # 实体图标
    #     device_class=SwitchDeviceClass.SWITCH,  # 设备类别
    #     data_protocol=CHILD_LOCK,      # 关联的设备协议
    #     translation_key="child_lock",  # 翻译键
    #     setter_value_on=1,             # 打开时的设置值
    #     setter_value_off=0,            # 关闭时的设置值
    # ),
    
    # 声音设置开关实体（当前唯一支持的开关实体）
    RoborockWasherSwitchDescription(
        key="sound_set",               # 实体唯一标识符
        name=None,                     # 使用翻译文件中的名称
        icon="mdi:volume-high",        # 实体图标
        device_class=SwitchDeviceClass.SWITCH,  # 设备类别
        data_protocol=SOUND_SET,       # 关联的设备协议
        translation_key="sound_set",   # 翻译键
        setter_value_on=1,             # 打开时的设置值
        setter_value_off=0,            # 关闭时的设置值
    ),

    # 洗涤剂设置开关实体（当前被注释掉，表示暂不支持）
    # RoborockWasherSwitchDescription(
    #     key="detergent_set",           # 实体唯一标识符
    #     name=None,                     # 使用翻译文件中的名称
    #     icon="mdi:cup-water",          # 实体图标
    #     device_class=SwitchDeviceClass.SWITCH,  # 设备类别
    #     data_protocol=DETERGENT_SET,   # 关联的设备协议
    #     translation_key="detergent_set",  # 翻译键
    #     setter_value_on=1,             # 打开时的设置值
    #     setter_value_off=0,            # 关闭时的设置值
    # ),
    
    # 柔顺剂设置开关实体（当前被注释掉，表示暂不支持）
    # RoborockWasherSwitchDescription(
    #     key="softener_set",            # 实体唯一标识符
    #     name=None,                     # 使用翻译文件中的名称
    #     icon="mdi:cup-water",          # 实体图标
    #     device_class=SwitchDeviceClass.SWITCH,  # 设备类别
    #     data_protocol=SOFTENER_SET,    # 关联的设备协议
    #     translation_key="softener_set",  # 翻译键
    #     setter_value_on=1,             # 打开时的设置值
    #     setter_value_off=0,            # 关闭时的设置值
    # ),
    
    # 灯光设置开关实体（当前被注释掉，表示暂不支持）
    # RoborockWasherSwitchDescription(
    #     key="light_setting",           # 实体唯一标识符
    #     name=None,                     # 使用翻译文件中的名称
    #     icon="mdi:lightbulb",          # 实体图标
    #     device_class=SwitchDeviceClass.SWITCH,  # 设备类别
    #     data_protocol=LIGHT_SETTING,   # 关联的设备协议
    #     translation_key="light_setting",  # 翻译键
    #     setter_value_on=1,             # 打开时的设置值
    #     setter_value_off=0,            # 关闭时的设置值
    # ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """根据配置条目设置Roborock洗衣机的开关实体。
    
    该函数是Home Assistant平台加载集成时的入口点，负责为每个连接的设备创建相应的开关实体。
    
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
    entities: list[RoborockWasherSwitch] = []
    # 为每个设备创建开关实体
    for device in devices:
        # 获取该设备的共享协调器
        coordinator = coordinators[device.duid]
        
        # 为每种开关实体类型创建实体实例
        for description in SWITCH_TYPES:
            entities.append(RoborockWasherSwitch(coordinator, description))

    # 将所有实体添加到Home Assistant
    async_add_entities(entities)


class RoborockWasherSwitch(RoborockWasherApiEntity, SwitchEntity):
    """Roborock洗衣机开关实体的实现类。
    
    该类继承自RoborockWasherApiEntity和Home Assistant的SwitchEntity，
    实现了与Roborock洗衣机设备交互的开关型实体功能。
    """

    # 实体描述对象，包含该实体的所有配置信息
    entity_description: RoborockWasherSwitchDescription

    def __init__(
        self,
        coordinator: RoborockWasherDataUpdateCoordinator,
        description: RoborockWasherSwitchDescription,
    ) -> None:
        """初始化Roborock洗衣机开关实体。
        
        Args:
            coordinator: 设备数据更新协调器实例
            description: 实体描述对象，定义实体的配置信息
        """
        # 调用父类初始化方法，传入协调器和关联的协议
        super().__init__(coordinator, description.data_protocol)
        # 保存实体描述对象
        self.entity_description = description
        # 设置实体的唯一标识符
        self._attr_unique_id = f"{DOMAIN}_{coordinator.duid}_switch_{description.key}"
        # 根据是否有翻译键设置实体名称
        if description.translation_key:
            self._attr_translation_key = description.translation_key
            self._attr_has_entity_name = True
        else:
            self._attr_name = description.name
        # 从缓存获取初始状态
        self._attr_is_on = bool(self.get_state())

    async def async_update(self) -> None:
        """异步更新开关实体的状态。
        
        此方法由Home Assistant在每次更新周期调用，用于同步设备的实际状态到Home Assistant界面。
        它通过调用get_state方法来获取最新的设备状态，并更新实体的内部状态变量。
        """
        # 使用get_state方法更新状态，利用缓存机制提高性能
        self._attr_is_on = bool(self.get_state())

    @property
    def is_on(self) -> bool | None:
        """获取开关的当前状态。
        
        返回开关是开启(true)还是关闭(false)的状态。该属性直接从缓存中获取最新状态，
        避免频繁查询设备造成的性能问题。
        
        Returns:
            bool | None: 如果成功获取状态则返回布尔值，否则返回None
        """
        # 直接使用get_state方法获取最新状态
        return bool(self.get_state())
    
    @property
    def available(self) -> bool:
        """检查实体是否可用。
        
        实体的可用性基于协调器的最后更新状态。如果协调器最后一次更新成功，
        则认为实体是可用的；否则实体将显示为不可用状态。
        
        Returns:
            bool: 如果实体可用返回True，否则返回False
        """
        return self.coordinator.last_update_success

    async def async_turn_on(self, **kwargs) -> None:
        """异步打开开关。
        
        当用户在Home Assistant界面上点击打开开关时，此方法会被调用。
        它会向设备发送打开命令，并处理可能发生的异常情况。
        
        Args:
            **kwargs: 其他可能传递的参数（未使用）
            
        Raises:
            Exception: 当打开开关过程中发生错误时抛出异常
        """
        try:
            _LOGGER.debug("正在打开开关 %s，使用协议 %s", self.name, self.entity_description.data_protocol)
            await self.async_set_value(self.entity_description.setter_value_on)
            # 注意：状态将在async_set_value方法中更新
            _LOGGER.debug("成功打开开关 %s", self.name)
        except Exception as ex:
            _LOGGER.exception("打开开关 %s 时发生错误: %s", self.name, ex)

    async def async_turn_off(self, **kwargs) -> None:
        """异步关闭开关。
        
        当用户在Home Assistant界面上点击关闭开关时，此方法会被调用。
        它会向设备发送关闭命令，并立即更新本地状态，然后处理可能发生的异常情况。
        
        Args:
            **kwargs: 其他可能传递的参数（未使用）
            
        Raises:
            Exception: 当关闭开关过程中发生错误时抛出异常
        """
        try:
            _LOGGER.debug("正在关闭开关 %s，使用协议 %s", self.name, self.entity_description.data_protocol)
            await self.async_set_value(self.entity_description.setter_value_off)
            # 立即更新本地状态为关闭
            self._attr_is_on = False
            _LOGGER.debug("成功关闭开关 %s", self.name)
        except Exception as ex:
            _LOGGER.exception("关闭开关 %s 时发生错误: %s", self.name, ex)

    async def async_set_value(self, value: Any) -> None:
        """异步设置实体协议对应的值。
        
        这是一个通用的方法，用于向设备发送特定值的命令。它不仅会执行实际的设备控制，
        还会处理特殊的逻辑，例如对声音设置协议的即时刷新需求。
        
        Args:
            value: 要设置给设备的值
            
        Raises:
            Exception: 当设置值过程中发生错误时抛出异常
        """
        try:
            # 调用父类方法执行实际的设备控制
            await super().async_set_value(value)
            # 立即更新本地状态
            self._attr_is_on = value == self.entity_description.setter_value_on
            
            # 如果这是声音设置协议，请求立即刷新该特定协议的状态
            if self.entity_description.data_protocol == SOUND_SET:
                _LOGGER.debug("请求立即更新声音设置协议")
                await self.coordinator.async_query_protocol(self.entity_description.data_protocol.lower())
                # 获取最新的值
                new_value = self.get_state()
                self._attr_is_on = bool(new_value) == bool(self.entity_description.setter_value_on)
                _LOGGER.debug("已更新声音设置开关状态为: %s", self._attr_is_on)
            
            # 通知Home Assistant状态发生变化
            self.async_write_ha_state()
        except Exception as ex:
            _LOGGER.exception("设置值时发生错误")