# Roborock Washer 集成 - Home Assistant

非码农，不懂代码，所有代码采用生成式API生成，依赖python-roborock库中的A01协议，感谢大佬的逆向工程。
Roborock的homeassistant官方集成只能显示洗衣机的4个传感器，此集成为补充，参考roboraock app添加了中文翻译。
目前START，PAUSE，STOP按钮在洗衣机待机时有反应但无对应运行响应，手动打开洗衣机后可以正常操作，这个目前靠个人能力解决不了，希望有大佬能帮忙解决。

## 安装方法

### 方法一：手动安装

1. 从 [发布页面](https://github.com/NOisi-x/hass-roborock-washer/releases) 下载最新版本
2. 将 `roborock_washer` 文件夹解压到您的 `custom_components` 目录
3. 重启 Home Assistant

### 方法二：HACS 安装（推荐）

1. 在 Home Assistant 中打开 HACS
2. 进入集成页面
3. 点击右上角的三个点并选择 "自定义存储库"
4. 添加 `https://github.com/NOisi-x/hass-roborock-washer` 作为自定义存储库
5. 选择 "集成" 作为类别
6. 点击 "添加"
7. 搜索 "Roborock Washer" 并安装
8. 重启 Home Assistant

## 配置步骤

1. 进入 设置 > 设备与服务
2. 点击 "添加集成"
3. 搜索 "Roborock Washer"
4. 输入您的 Roborock 账户邮箱地址
5. 点击 "提交" 以通过电子邮件接收验证码
6. 输入收到的验证码

集成将自动发现并添加与您账户关联的所有支持的 Roborock 洗衣机。每个洗衣机将显示为一个独立的设备，包含所有可用实体。

## 实体列表

所有支持的特性都具有一个传感器实体。因为洗衣机的操作依赖云端控制，操作可能执行延迟或不成功，传感器可以用来检查状态是否更新成功。

### 传感器
- `sensor.roborock_washer_status`: 当前状态（待机、洗涤中、完成等），每分钟更新
- `sensor.roborock_washer_washing_left`: 剩余洗涤时间（分钟），每分钟更新
- `sensor.roborock_washer_error`: 错误信息（一般为none），每6小时更新
- `sensor.roborock_washer_times_after_clean`: 上次筒自洁后已运行次数，每6小时更新
- `sensor.roborock_washer_detergent_empty`: 洗涤剂余量低（False/True），每6小时更新
- `sensor.roborock_washer_mode`: 当前洗涤模式，每6小时更新
- `sensor.roborock_washer_program`: 当前洗涤程序，每6小时更新
- `sensor.roborock_washer_temp`: 当前洗涤温度，每6小时更新
- `sensor.roborock_washer_rinse_times`: 漂洗次数，每6小时更新
- `sensor.roborock_washer_spin_level`: 当前转速挡位，每6小时更新
- `sensor.roborock_washer_drying_mode`: 当前烘干模式，每6小时更新
- `sensor.roborock_washer_detergent_type`: 洗涤剂智能投放挡位，每6小时更新
- `sensor.roborock_washer_countdown`: 倒计时定时器（分钟），每分钟更新
- `switch.roborock_washer_sound_set`: 洗衣机提示音，每6小时更新

### 开关
- `switch.roborock_washer_sound_set`: 开关洗衣机提示音，操作后会立刻请求更新自身和对应传感器状态

### 按钮
- `button.roborock_washer_start`: 启动，仅在洗衣机开机下可以操作成功
- `button.roborock_washer_pause`: 暂停，仅在洗衣机开机下可以操作成功
- `button.roborock_washer_stop`: 停止，仅在洗衣机开机下可以操作成功

### 选择实体
- `select.roborock_washer_mode`: 选择洗涤模式，操作后会立刻请求更新自身和对应传感器状态
- `select.roborock_washer_program`: 选择洗涤程序，包含所有程序，对不同设备有些选项可能无效，操作后会立刻请求更新自身和对应传感器状态
- `select.roborock_washer_temp`: 设置洗涤温度挡位，包含所有温度挡位，对不同设备有些选项可能无效，操作后会立刻请求更新自身和对应传感器状态
- `select.roborock_washer_rinse_times`: 选择漂洗次数，包含所有漂洗挡位，对不同设备有些选项可能无效，操作后会立刻请求更新自身和对应传感器状态
- `select.roborock_washer_spin_level`: 设置转速挡位，包含所有转速挡位，对不同设备有些选项可能无效，操作后会立刻请求更新自身和对应传感器状态
- `select.roborock_washer_drying_mode`: 选择烘干模式，包含所有烘干模式，对不同设备有些选项可能无效，操作后会立刻请求更新自身和对应传感器状态
- `select.roborock_washer_detergent_type`: 选择智能投放挡位，包含所有智能投放挡位，对不同设备有些选项可能无效，操作后会立刻请求更新自身和对应传感器状态


## 致谢

- 此集成使用 [python-roborock](https://github.com/Python-roborock/python-roborock) 库实现核心设备通信
- 灵感来自官方 [Home Assistant Roborock 集成](https://github.com/home-assistant/core/tree/dev/homeassistant/components/roborock)

## 许可证

MIT 许可证