"""按钮平台模块，用于Roborock洗衣机集成。

该模块实现了Home Assistant按钮实体，允许用户通过界面控制Roborock洗衣机的各种操作，
如启动、暂停和关机等命令。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import (
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import RoborockWasherDataUpdateCoordinator
from .entity import RoborockWasherApiEntity

# 获取按钮平台的日志记录器
_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class RoborockWasherButtonDescription(ButtonEntityDescription):
    """Roborock洗衣机按钮描述类。
    
    该数据类扩展了Home Assistant的ButtonEntityDescription，添加了与Roborock洗衣机
    特定协议相关的属性，用于描述按钮的功能和行为。
    """
    # 与按钮关联的设备协议名称
    data_protocol: str
    # 按钮按下时发送给设备的值
    press_value: Any = None
    # 用于本地化显示的翻译键
    translation_key: str | None = None


# 定义洗衣机操作的协议常量
# START: 启动洗衣机
START = "START"
# PAUSE: 暂停洗衣机
PAUSE = "PAUSE"
# SHUTDOWN: 关闭洗衣机
SHUTDOWN = "SHUTDOWN"

# 支持的所有按钮配置
# 包含启动、暂停和关机三个主要控制按钮
BUTTON_TYPES: tuple[RoborockWasherButtonDescription, ...] = (
    RoborockWasherButtonDescription(
        key="start",
        icon="mdi:play",
        data_protocol=START,
        press_value=1,   #关机时这几个命令有反应但不执行，开机时会执行
        translation_key="start",
    ),
    RoborockWasherButtonDescription(
        key="pause",
        icon="mdi:pause",
        data_protocol=PAUSE,
        press_value=1,
        translation_key="pause",
    ),
    RoborockWasherButtonDescription(
        key="shutdown",
        icon="mdi:stop",
        data_protocol=SHUTDOWN,
        press_value=1,
        translation_key="shutdown",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """异步设置Roborock洗衣机按钮实体。
    
    根据配置条目为所有发现的洗衣机设备创建按钮实体。每个设备都会创建一组按钮实体，
    包括启动、暂停和关机按钮，用于控制洗衣机的基本操作。
    
    Args:
        hass: Home Assistant核心实例
        config_entry: 集成的配置条目对象
        async_add_entities: 用于向Home Assistant添加实体的回调函数
    """
    # 从hass数据存储中检索设备和协调器数据
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    devices = entry_data["devices"]
    coordinators = entry_data["coordinators"]

    # 为每个设备和每种支持的按钮类型创建按钮实体
    entities: list[RoborockWasherButton] = []
    for device in devices:
        # 每个设备都有自己的协调器用于管理API通信
        coordinator = coordinators[device.duid]
        
        # 为所有定义的按钮类型创建实体
        for description in BUTTON_TYPES:
            entities.append(RoborockWasherButton(coordinator, description))

    # 将所有创建的实体注册到Home Assistant
    async_add_entities(entities)


class RoborockWasherButton(RoborockWasherApiEntity, ButtonEntity):
    """Roborock洗衣机按钮实体的实现类。
    
    该类继承自RoborockWasherApiEntity和Home Assistant的ButtonEntity，
    实现了控制洗衣机各种操作的按钮功能，如启动、暂停和停止洗涤周期。
    """

    # 实体描述的类型提示
    entity_description: RoborockWasherButtonDescription

    def __init__(
        self,
        coordinator: RoborockWasherDataUpdateCoordinator,
        description: RoborockWasherButtonDescription,
    ) -> None:
        """初始化Roborock洗衣机按钮实体。
        
        Args:
            coordinator: 设备的数据协调器实例
            description: 包含按钮配置详情的按钮描述对象
        """
        # 初始化父类
        super().__init__(coordinator, description.data_protocol)
        
        # 保存实体描述对象
        self.entity_description = description
        
        # 生成此实体的唯一标识符
        self._attr_unique_id = f"{DOMAIN}_{coordinator.duid}_button_{description.key}"
        
        # 使用翻译键配置实体命名以支持本地化
        if description.translation_key:
            self._attr_translation_key = description.translation_key
            self._attr_has_entity_name = True
        else:
            self._attr_name = description.name

    async def async_press(self) -> None:
        """处理按钮按下事件。
        
        此方法向洗衣机发送相应的命令，并立即更新某些操作的状态信息以提供即时反馈。
        对于关键控制按钮（启动、暂停、关机），会在执行后立即刷新设备状态。
        """
        try:
            # 通过协调器向设备发送命令值
            await self.async_set_value(self.entity_description.press_value)
            
            # 对于关键控制按钮，立即刷新设备状态以在UI中提供即时反馈
            if self.entity_description.data_protocol in [START, PAUSE, SHUTDOWN]:
                _LOGGER.debug(
                    "按下%s按钮，正在请求STATE协议的即时更新", 
                    self.entity_description.data_protocol
                )
                try:
                    # 请求立即更新状态信息
                    await self.coordinator.async_query_protocol("state")
                    _LOGGER.debug(
                        "在按下%s按钮后，STATE协议已成功更新", 
                        self.entity_description.data_protocol
                    )
                except Exception as ex:
                    # 如果状态更新失败，记录日志但不中断操作
                    _LOGGER.warning(
                        "在按下%s按钮后更新STATE协议失败: %s", 
                        self.entity_description.data_protocol, 
                        ex
                    )
        except Exception as ex:
            # 记录按钮按下操作期间的任何错误
            _LOGGER.exception("按下按钮时发生错误")
            raise
    
    @property
    def available(self) -> bool:
        """获取实体是否可用。
        
        当协调器的上次更新成功时，按钮被认为是可用的，这表明与设备的通信正常工作。
        
        Returns:
            bool: 如果实体可用返回True，否则返回False
        """
        return self.coordinator.last_update_success