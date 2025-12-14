"""配置流程模块，用于Roborock洗衣机集成。

该模块实现了Home Assistant配置流程，允许用户通过电子邮件验证码方式登录Roborock账户，
并将洗衣机设备添加到Home Assistant中进行控制和监控。
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from roborock.exceptions import (
    RoborockAccountDoesNotExist,
    RoborockException,
    RoborockInvalidCode,
    RoborockInvalidEmail,
    RoborockTooFrequentCodeRequests,
    RoborockUrlException,
)
from roborock.web_api import RoborockApiClient

from .const import (
    CONF_BASE_URL,
    CONF_ENTRY_CODE,
    CONF_USER_DATA,
    CONF_USERNAME,
    DOMAIN,
)

# 获取配置流程的日志记录器
_LOGGER = logging.getLogger(__name__)

# 用户输入数据的验证模式
# 要求用户提供有效的邮箱地址作为用户名
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Roborock洗衣机集成的配置流程处理类。

    该类继承自Home Assistant的ConfigFlow基类，负责处理用户添加Roborock洗衣机集成时的配置流程。
    包括用户身份验证、设备发现和配置条目创建等步骤。
    """

    # 配置流程版本号，用于跟踪配置结构的变化
    VERSION = 1
    MINOR_VERSION = 0

    def __init__(self) -> None:
        """初始化配置流程实例。
        
        初始化时设置用户名和API客户端为None，这些将在配置流程的不同步骤中被赋值。
        """
        # 存储用户输入的邮箱地址
        self._username: str | None = None
        # Roborock API客户端实例，用于与Roborock服务器通信
        self._client: RoborockApiClient | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """处理配置流程的初始步骤（用户输入邮箱）。
        
        在此步骤中，用户需要提供其Roborock账户的邮箱地址。系统将向该邮箱发送验证码，
        用于后续的身份验证步骤。
        
        Args:
            user_input: 用户输入的数据字典，包含CONF_USERNAME键
            
        Returns:
            FlowResult: 配置流程的结果，可能包括表单显示或下一步骤跳转
        """
        # 存储错误信息的字典
        errors: dict[str, str] = {}
        # 如果用户已提交数据
        if user_input is not None:
            # 获取用户输入的邮箱地址
            username = user_input[CONF_USERNAME]
            self._username = username
            _LOGGER.debug("正在为Roborock洗衣机账户请求验证码")
            # 创建Roborock API客户端实例
            self._client = RoborockApiClient(self._username)
            # 请求发送验证码，并获取可能的错误信息
            errors = await self._request_code()
            # 如果没有错误，则进入验证码输入步骤
            if not errors:
                return await self.async_step_code()

        # 显示用户输入表单，包含可能的错误信息
        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def _request_code(self) -> dict:
        """向Roborock API请求发送验证码邮件。
        
        此方法调用Roborock API来请求向用户邮箱发送验证码。根据不同的异常情况，
        返回相应的错误代码，供前端显示友好的错误提示。
        
        Returns:
            dict: 错误信息字典，如果没有错误则返回空字典
        """
        # 确保API客户端已初始化
        assert self._client
        # 存储错误信息的字典
        errors: dict[str, str] = {}
        try:
            # 调用API请求发送验证码
            await self._client.request_code()
        except RoborockAccountDoesNotExist:
            # 账户不存在错误
            errors["base"] = "invalid_email"
        except RoborockUrlException:
            # URL相关错误
            errors["base"] = "unknown_url"
        except RoborockInvalidEmail:
            # 无效邮箱格式错误
            errors["base"] = "invalid_email_format"
        except RoborockTooFrequentCodeRequests:
            # 请求过于频繁错误
            errors["base"] = "too_frequent_code_requests"
        except RoborockException:
            # 其他Roborock异常
            _LOGGER.exception("意外的Roborock异常")
            errors["base"] = "unknown_roborock"
        except Exception:
            # 其他未预期异常
            _LOGGER.exception("意外异常")
            errors["base"] = "unknown"
        # 返回错误信息字典
        return errors

    async def async_step_code(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """处理验证码验证步骤。
        
        用户在此步骤中输入收到的验证码，系统将使用该验证码完成账户登录验证。
        验证成功后，将创建配置条目并完成整个配置流程。
        
        Args:
            user_input: 用户输入的数据字典，包含CONF_ENTRY_CODE键
            
        Returns:
            FlowResult: 配置流程的结果，可能包括表单显示或配置条目创建
        """
        # 存储错误信息的字典
        errors: dict[str, str] = {}
        # 确保API客户端和用户名已初始化
        assert self._client
        assert self._username
        # 如果用户已提交验证码
        if user_input is not None:
            # 获取用户输入的验证码
            code = user_input[CONF_ENTRY_CODE]
            _LOGGER.debug("正在使用邮箱提供的验证码登录Roborock洗衣机账户")
            try:
                # 使用验证码登录并获取用户数据
                user_data = await self._client.code_login(code)
            except RoborockInvalidCode:
                # 无效验证码错误
                errors["base"] = "invalid_code"
            except RoborockException:
                # Roborock相关异常
                _LOGGER.exception("意外的Roborock异常")
                errors["base"] = "unknown_roborock"
            except Exception:
                # 其他未预期异常
                _LOGGER.exception("意外异常")
                errors["base"] = "unknown"
            else:
                # 登录成功，创建配置条目
                return await self._create_entry(user_data)

        # 显示验证码输入表单，包含可能的错误信息
        return self.async_show_form(
            step_id="code", data_schema=vol.Schema({vol.Required(CONF_ENTRY_CODE): str}), errors=errors
        )

    async def _create_entry(self, user_data) -> FlowResult:
        """在登录成功后创建配置条目。
        
        此方法将成功验证的用户信息和设备数据保存到Home Assistant的配置系统中，
        使得集成可以访问和控制用户的Roborock洗衣机设备。
        
        Args:
            user_data: 成功登录后获取的用户数据对象
            
        Returns:
            FlowResult: 表示配置条目已成功创建的结果
        """
        # 确保API客户端和用户名已初始化
        assert self._client
        assert self._username
        # 创建配置条目，包含用户邮箱、用户数据和基础URL
        return self.async_create_entry(
            title=self._username,
            data={
                CONF_USERNAME: self._username,
                CONF_USER_DATA: user_data.as_dict(),
                CONF_BASE_URL: await self._client.base_url,
            },
        )