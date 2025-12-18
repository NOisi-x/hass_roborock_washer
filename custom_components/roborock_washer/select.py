"""Roborock洗衣机选择实体支持模块。

本模块实现了Roborock洗衣机的各种选择型实体，允许用户通过Home Assistant界面选择不同的洗涤选项，
如洗涤模式、程序、洗涤剂类型、温度、转速、漂洗次数和烘干模式等。

这些实体与设备的协议层进行交互，将用户的选择转换为设备可以理解的指令，并能实时反映设备的当前设置。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import RoborockWasherDataUpdateCoordinator
from .entity import RoborockWasherApiEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class RoborockWasherSelectDescription(SelectEntityDescription):
    """Roborock洗衣机选择实体描述类。
    
    该类扩展了Home Assistant的SelectEntityDescription，为Roborock洗衣机的选择实体提供了额外的描述信息。
    主要用于定义每个选择实体的协议类型和选项映射关系。
    """
    # 与该选择实体关联的设备协议标识符
    data_protocol: str
    # 选项值到显示名称的映射字典
    options_map: Dict[Any, str] = field(default_factory=dict)
    # 翻译键，用于从翻译文件中获取实体名称
    translation_key: str | None = None


# 定义设备协议常量
# 洗涤模式协议标识符
MODE = "MODE"
# 洗涤程序协议标识符
PROGRAM = "PROGRAM"
# 洗涤剂类型协议标识符
DETERGENT_TYPE = "DETERGENT_TYPE"
# 温度设置协议标识符
TEMP = "TEMP"
# 脱水转速协议标识符
SPIN_LEVEL = "SPIN_LEVEL"
# 漂洗次数协议标识符
RINSE_TIMES = "RINSE_TIMES"
# 烘干模式协议标识符
DRYING_MODE = "DRYING_MODE"

# 定义洗涤模式和程序的选项映射
# 这些映射穷举了所有可能的洗涤模式和程序选项
# 根据设备日志分析，实际值以字符串格式传输
# 洗涤模式选项映射：定义设备支持的所有洗涤模式
MODE_OPTIONS: Dict[Any, str] = {
    "wash": "wash",           # 单纯洗涤模式
    "wash_and_dry": "wash_and_dry",  # 洗涤+烘干模式
    "dry": "dry",             # 单纯烘干模式
}

# 洗涤程序选项映射：定义设备支持的所有洗涤程序
PROGRAM_OPTIONS: Dict[Any, str] = {
    "standard": "standard",       # 标准洗程序
    "quick": "quick",             # 快速洗程序
    "sanitize": "sanitize",       # 除菌洗程序
    "wool": "wool",               # 羊毛洗程序
    "air_refresh": "air_refresh", # 空气洗程序
    "custom": "custom",           # 自定义程序
    "bedding": "bedding",         # 床品洗程序
    "down": "down",               # 羽绒洗程序
    "silk": "silk",               # 丝绸洗程序
    "rinse_and_spin": "rinse_and_spin",  # 漂洗+脱水程序
    "spin": "spin",               # 单脱水程序
    "down_clean": "down_clean",   # 羽绒清洁程序
    "baby_care": "baby_care",     # 婴儿洗程序
    "anti_allergen": "anti_allergen",  # 除过敏程序
    "sportswear": "sportswear",   # 运动服洗程序
    "night": "night",             # 夜间洗程序
    "new_clothes": "new_clothes", # 新衣洗程序
    "shirts": "shirts",           # 衬衫洗程序
    "synthetics": "synthetics",   # 化纤洗程序
    "underwear": "underwear",     # 内衣洗程序
    "gentle": "gentle",           # 轻柔洗程序
    "intensive": "intensive",     # 强力洗程序
    "cotton_linen": "cotton_linen",  # 棉麻洗程序
    "season": "season",           # 季节洗程序
    "warming": "warming",         # 加温洗程序
    "bra": "bra",                 # 文胸洗程序
    "panties": "panties",         # 内裤洗程序
    "boiling_wash": "boiling_wash",  # 煮沸洗程序
    "socks": "socks",             # 袜子洗程序
    "towels": "towels",           # 毛巾洗程序
    "anti_mite": "anti_mite",     # 除螨洗程序
    "exo_40_60": "exo_40_60",     # 40-60°C洗程序
    "twenty_c": "twenty_c",       # 20°C洗程序
    "t_shirts": "t_shirts",       # T恤洗程序
    "stain_removal": "stain_removal",  # 去污洗程序
}

# 洗涤剂类型选项映射：定义设备支持的所有洗涤剂类型
DETERGENT_TYPE_OPTIONS: Dict[Any, str] = {
    "empty": "empty",    # 无洗涤剂
    "low": "low",        # 少量洗涤剂
    "medium": "medium",  # 中等洗涤剂
    "high": "high",      # 大量洗涤剂
}

# 增强的选项映射类，提供更健壮的选项处理机制
# 当遇到不在预定义映射中的值时，能够自动创建合适的选项表示
class EnhancedOptionsMap:
    """增强的选项映射类，支持自动处理未知值。
    
    该类提供了一种更灵活的方式来处理设备返回的选项值，特别是当设备返回了
    不在预定义映射中的新值时，能够自动生成合适的选项表示，而不是简单地忽略或报错。
    """
    
    def __init__(self, base_map: Dict[Any, str]):
        """初始化增强选项映射实例。
        
        Args:
            base_map: 基础选项映射字典，键为设备返回的原始值，值为显示名称
        """
        # 存储基础映射关系
        self._base_map = base_map
        # 创建反向映射，便于从显示名称查找原始值
        self._reverse_map = {v: k for k, v in base_map.items()}
    
    def get_option(self, value: Any) -> str:
        """根据设备返回的原始值获取对应的显示选项名称。
        
        Args:
            value: 设备返回的原始值
            
        Returns:
            str: 对应的显示选项名称，如果未找到则返回自定义格式
        """
        # 首先尝试直接匹配原始值
        if value in self._base_map:
            return self._base_map[value]
        # 然后尝试将值转换为字符串后匹配
        if str(value) in self._base_map:
            return self._base_map[str(value)]
        # 如果都未找到，返回自定义格式表示
        return f"Custom ({value})"
    
    def get_value(self, option: str) -> Any:
        """根据显示选项名称获取对应的设备原始值。
        
        Args:
            option: 显示选项名称
            
        Returns:
            Any: 对应的设备原始值
            
        Raises:
            ValueError: 当提供的选项名称无效时抛出异常
        """
        # 首先尝试直接匹配选项名称
        if option in self._reverse_map:
            return self._reverse_map[option]
        # 尝试解析自定义值格式
        if option.startswith("Custom (") and option.endswith(")"):
            try:
                # 尝试解析为整数
                return int(option[8:-1])
            except ValueError:
                # 如果不是数字，则返回原始字符串内容
                return option[8:-1]
        # 无效选项名称
        raise ValueError(f"Invalid option: {option}")
    
    def get_all_options(self) -> List[str]:
        """获取所有可用的选项名称列表。
        
        Returns:
            List[str]: 包含所有选项名称的列表
        """
        return list(self._base_map.values())

# 温度选项映射：定义设备支持的所有温度设置选项
# 与传感器实体保持一致，只保留6种常用状态
TEMP_OPTIONS: Dict[Any, str] = {
    "normal": "normal",    # 正常温度
    "low": "low",          # 低温
    "medium": "medium",    # 中温
    "high": "high",        # 高温
    "max": "max",          # 最高温度
    "twenty_c": "20°C",    # 20摄氏度固定温度
}

# 转速选项映射：定义设备支持的所有脱水转速选项
SPIN_LEVEL_OPTIONS: Dict[Any, str] = {
    "none": "none",        # 无脱水
    "very_low": "very_low",  # 极低转速
    "low": "low",          # 低转速
    "mid": "mid",          # 中等转速
    "high": "high",        # 高转速
    "very_high": "very_high",  # 极高转速
    "max": "max",          # 最大转速
}

# 漂洗次数选项映射：定义设备支持的所有漂洗次数选项
# 与传感器实体保持一致，只保留none、min、low、mid、high、max六种状态
# 键使用ZeoRinse类中的实际整数值
RINSE_TIMES_OPTIONS: Dict[Any, str] = {
    "none": "none",  # 无漂洗
    "min": "min",    # 最少漂洗
    "low": "low",    # 少量漂洗
    "mid": "mid",    # 中等漂洗
    "high": "high",  # 大量漂洗
    "max": "max",    # 最多漂洗
}

# 烘干模式选项映射：定义设备支持的所有烘干模式选项
DRYING_MODE_OPTIONS: Dict[Any, str] = {
    "none": "none",    # 无烘干
    "quick": "quick",  # 快速烘干
    "iron": "iron",    # 熨烫烘干
    "store": "store",  # 存储烘干
}

# 创建增强的选项映射实例，用于处理各种设备选项
# 洗涤模式增强映射实例
MODE_ENHANCED_MAP = EnhancedOptionsMap(MODE_OPTIONS)
# 洗涤程序增强映射实例
PROGRAM_ENHANCED_MAP = EnhancedOptionsMap(PROGRAM_OPTIONS)
# 温度设置增强映射实例
TEMP_ENHANCED_MAP = EnhancedOptionsMap(TEMP_OPTIONS)
# 脱水转速增强映射实例
SPIN_LEVEL_ENHANCED_MAP = EnhancedOptionsMap(SPIN_LEVEL_OPTIONS)
# 漂洗次数增强映射实例
RINSE_TIMES_ENHANCED_MAP = EnhancedOptionsMap(RINSE_TIMES_OPTIONS)
# 烘干模式增强映射实例
DRYING_MODE_ENHANCED_MAP = EnhancedOptionsMap(DRYING_MODE_OPTIONS)

# 定义所有支持的选择实体类型
# 每个实体描述包含关键属性：唯一标识符、图标、关联协议和选项映射
SELECT_TYPES: tuple[RoborockWasherSelectDescription, ...] = (
    # 洗涤模式选择实体
    RoborockWasherSelectDescription(
        key="mode",                    # 实体唯一标识符
        icon="mdi:tune-vertical",      # 实体图标
        data_protocol=MODE,            # 关联的设备协议
        options_map=MODE_OPTIONS,      # 选项映射
        translation_key="mode",        # 翻译键
    ),
    # 洗涤程序选择实体
    RoborockWasherSelectDescription(
        key="program",                 # 实体唯一标识符
        icon="mdi:playlist-play",      # 实体图标
        data_protocol=PROGRAM,         # 关联的设备协议
        options_map=PROGRAM_OPTIONS,   # 选项映射
        translation_key="program",     # 翻译键
    ),
    # 洗涤剂类型选择实体
    RoborockWasherSelectDescription(
        key="detergent_type",          # 实体唯一标识符
        icon="mdi:sprinkler-variant",  # 实体图标
        data_protocol=DETERGENT_TYPE,  # 关联的设备协议
        options_map=DETERGENT_TYPE_OPTIONS,  # 选项映射
        translation_key="detergent_type",    # 翻译键
    ),
    # 温度设置选择实体
    RoborockWasherSelectDescription(
        key="temperature",             # 实体唯一标识符
        icon="mdi:thermometer",        # 实体图标
        data_protocol=TEMP,            # 关联的设备协议
        options_map=TEMP_OPTIONS,      # 选项映射
        translation_key="temperature", # 翻译键
    ),
    # 脱水转速选择实体
    RoborockWasherSelectDescription(
        key="spin_level",              # 实体唯一标识符
        icon="mdi:fast-forward",       # 实体图标
        data_protocol=SPIN_LEVEL,      # 关联的设备协议
        options_map=SPIN_LEVEL_OPTIONS,      # 选项映射
        translation_key="spin_level",        # 翻译键
    ),
    # 漂洗次数选择实体
    RoborockWasherSelectDescription(
        key="rinse_times",             # 实体唯一标识符
        icon="mdi:refresh",            # 实体图标
        data_protocol=RINSE_TIMES,     # 关联的设备协议
        options_map=RINSE_TIMES_OPTIONS,     # 选项映射
        translation_key="rinse_times",       # 翻译键
    ),
    # 烘干模式选择实体
    RoborockWasherSelectDescription(
        key="drying_mode",             # 实体唯一标识符
        icon="mdi:tumble-dryer",       # 实体图标
        data_protocol=DRYING_MODE,     # 关联的设备协议
        options_map=DRYING_MODE_OPTIONS,     # 选项映射
        translation_key="drying_mode",       # 翻译键
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """根据配置条目设置Roborock洗衣机的选择实体。
    
    该函数是Home Assistant平台加载集成时的入口点，负责为每个连接的设备创建相应的选择实体。
    
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
    entities: list[RoborockWasherSelect] = []
    # 为每个设备创建选择实体
    for device in devices:
        # 获取该设备的共享协调器
        coordinator = coordinators[device.duid]
        
        # 为每种选择实体类型创建实体实例
        for description in SELECT_TYPES:
            entities.append(RoborockWasherSelect(coordinator, description))

    # 将所有实体添加到Home Assistant
    async_add_entities(entities)


class RoborockWasherSelect(RoborockWasherApiEntity, SelectEntity):
    """Roborock洗衣机选择实体的实现类。
    
    该类继承自RoborockWasherApiEntity和Home Assistant的SelectEntity，
    实现了与Roborock洗衣机设备交互的选择型实体功能。
    """

    # 实体描述对象，包含该实体的所有配置信息
    entity_description: RoborockWasherSelectDescription

    def __init__(
        self,
        coordinator: RoborockWasherDataUpdateCoordinator,
        description: RoborockWasherSelectDescription,
    ) -> None:
        """初始化Roborock洗衣机选择实体。
        
        Args:
            coordinator: 设备数据更新协调器实例
            description: 实体描述对象，定义实体的配置信息
        """
        # 调用父类初始化方法，传入协调器和关联的协议
        protocol = description.data_protocol if description.data_protocol else description.key
        super().__init__(coordinator, protocol)
        # 保存实体描述对象
        self.entity_description = description
        # 设置实体的唯一标识符
        protocol_name = description.data_protocol.lower() if description.data_protocol else description.key
        self._attr_unique_id = f"{coordinator.model}_{protocol_name}"
        # 根据是否有翻译键设置实体名称
        if description.translation_key:
            self._attr_translation_key = description.translation_key
            self._attr_has_entity_name = True
        else:
            self._attr_name = description.name
        
        # 设置可用选项列表
        self._attr_options = list(description.options_map.values())

    @property
    def current_option(self) -> Optional[str]:
        """获取当前选中的选项。
        
        返回与设备当前状态对应的选择项名称。如果设备未设置相应状态或发生错误，则返回None。
        
        Returns:
            Optional[str]: 当前选中的选项名称，如果无有效选项则返回None
        """
        # 操作模式没有当前状态，所以始终返回None
        if self.entity_description.key == "operation":
            return None
        
        # 从设备获取当前状态值
        value = self.get_state()
        _LOGGER.debug("Current option - entity key: %s, raw value: %s", self.entity_description.key, value)
        # 如果值为空或未设置，返回None
        if value is None or value == "not set":
            return None
        
        # 对于所有需要映射的select实体，需要将值映射到选项名称
        if self.entity_description.key in ["mode", "program", "detergent_type", "temperature", "spin_level", "rinse_times", "drying_mode"]:
            # 查找值在options_map中的对应选项名称
            options_map = self.entity_description.options_map
            if value in options_map:
                mapped_value = options_map[value]
                _LOGGER.debug("Mapped value for %s: %s -> %s", self.entity_description.key, value, mapped_value)
                return mapped_value
            # 如果值不在映射中，尝试转换为字符串后查找
            str_value = str(value)
            if str_value in options_map:
                mapped_value = options_map[str_value]
                _LOGGER.debug("Mapped string value for %s: %s -> %s", self.entity_description.key, str_value, mapped_value)
                return mapped_value
            # 如果仍然找不到，返回None
            _LOGGER.debug("No mapping found for %s value: %s", self.entity_description.key, value)
            return None
        
        # 对于其他实体，返回协议定义的原始字符串值
        return str(value)

    async def async_select_option(self, option: str) -> None:
        """异步选择指定选项。
        
        当用户在Home Assistant界面上选择一个选项时，此方法会被调用。
        它将用户选择的选项转换为设备可理解的值，并发送给设备。
        
        Args:
            option: 用户选择的选项名称
            
        Raises:
            Exception: 当设置选项过程中发生错误时抛出异常
        """
        try:
            # 直接使用用户选择的选项作为值字符串
            # 导入并使用相应的枚举将字符串转换为整数值
            if self.entity_description.key == "mode":
                from roborock.data.zeo.zeo_code_mappings import ZeoMode
                # 确保option存在于ZeoMode中，否则使用默认值
                if option in ZeoMode.__members__:
                    value = ZeoMode[option].value
                else:
                    _LOGGER.error(f"Invalid mode option: {option}, using default mode")
                    value = ZeoMode.wash.value
            elif self.entity_description.key == "program":
                from roborock.data.zeo.zeo_code_mappings import ZeoProgram
                # 确保option存在于ZeoProgram中，否则使用默认值
                if option in ZeoProgram.__members__:
                    value = ZeoProgram[option].value
                else:
                    _LOGGER.error(f"Invalid program option: {option}, using default program")
                    value = ZeoProgram.standard.value
            elif self.entity_description.key == "temperature":
                from roborock.data.zeo.zeo_code_mappings import ZeoTemperature
                # 确保option存在于ZeoTemperature中，否则使用默认值
                if option in ZeoTemperature.__members__:
                    value = ZeoTemperature[option].value
                else:
                    _LOGGER.error(f"Invalid temperature option: {option}, using default temperature")
                    value = ZeoTemperature.normal.value
            elif self.entity_description.key == "spin_level":
                from roborock.data.zeo.zeo_code_mappings import ZeoSpin
                # 确保option存在于ZeoSpin中，否则使用默认值
                if option in ZeoSpin.__members__:
                    value = ZeoSpin[option].value
                else:
                    _LOGGER.error(f"Invalid spin level option: {option}, using default spin level")
                    value = ZeoSpin.mid.value
            elif self.entity_description.key == "rinse_times":
                from roborock.data.zeo.zeo_code_mappings import ZeoRinse
                # 确保option存在于ZeoRinse中，否则使用默认值
                if option in ZeoRinse.__members__:
                    value = ZeoRinse[option].value
                else:
                    _LOGGER.error(f"Invalid rinse times option: {option}, using default rinse times")
                    value = ZeoRinse.mid.value
            elif self.entity_description.key == "drying_mode":
                from roborock.data.zeo.zeo_code_mappings import ZeoDryingMode
                # 确保option存在于ZeoDryingMode中，否则使用默认值
                if option in ZeoDryingMode.__members__:
                    value = ZeoDryingMode[option].value
                else:
                    _LOGGER.error(f"Invalid drying mode option: {option}, using default drying mode")
                    value = ZeoDryingMode.none.value
            else:
                _LOGGER.error(f"Invalid select entity key: {self.entity_description.key}")
                return
            
            # 异步设置转换后的值到设备
            await self.async_set_value(value)
        except Exception as ex:
            _LOGGER.exception(f"Error setting option {option} for {self.entity_description.key}")
            raise

    async def async_set_value(self, value: Any) -> None:
        """异步设置实体协议值并立即刷新状态。
        
        此方法首先调用父类方法将值设置到设备，然后请求立即刷新相关协议的状态，
        并强制更新实体在Home Assistant中的状态显示。
        
        Args:
            value: 要设置的值
            
        Raises:
            Exception: 当设置值过程中发生错误时抛出异常
        """
        try:
            # 调用父类的async_set_value方法将值设置到设备
            await super().async_set_value(value)
            
            # 对于所有选择实体，请求立即刷新此特定协议的状态
            protocol_name = self.entity_description.data_protocol.lower() if self.entity_description.data_protocol else self.entity_description.key
            _LOGGER.debug("Requesting immediate update for %s protocol", protocol_name)
            await self.coordinator.async_query_protocol(protocol_name)
            
            # 强制更新实体状态
            self.async_write_ha_state()
            _LOGGER.debug("Updated %s select state", self.entity_description.key)
        except Exception as ex:
            _LOGGER.exception("Error setting value for %s", self.entity_description.key)
