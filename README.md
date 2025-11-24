# openglcts-mini

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**openglcts-mini** 是一个 OpenGL ES 2.0 一致性测试套件的最小化移植版本，基于 [VK-GL-CTS](https://github.com/KhronosGroup/VK-GL-CTS)（Khronos Vulkan/OpenGL 一致性测试套件）。

本项目旨在提供一个轻量级、易于集成的 OpenGL ES 2.0 测试框架，而无需完整编译庞大的 VK-GL-CTS 项目。

## ✨ 特性

- **最小化依赖**: 仅需要 EGL、OpenGL ES 2.0、zlib 和 libpng
- **轻量级集成**: 无需编译整个 VK-GL-CTS，仅包含必要的 GLES2 测试模块
- **标准兼容**: 基于 Khronos 官方的一致性测试套件
- **灵活测试**: 支持单个测试用例或完整测试套件执行
- **多平台支持**: 支持 Linux 和其他 POSIX 系统

## 📋 系统要求

### 构建依赖

- CMake 3.20 或更高版本
- C++17 兼容的编译器 (GCC 7+, Clang 5+)
- C99 兼容的编译器
- pkg-config

### 运行时依赖

- EGL 库
- OpenGL ES 2.0 库 (GLESv2)
- zlib
- libpng

### Ubuntu/Debian 安装依赖

```bash
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    cmake \
    pkg-config \
    libegl1-mesa-dev \
    libgles2-mesa-dev \
    zlib1g-dev \
    libpng-dev
```

### Fedora/RHEL 安装依赖

```bash
sudo dnf install -y \
    gcc gcc-c++ \
    cmake \
    pkgconfig \
    mesa-libEGL-devel \
    mesa-libGLES-devel \
    zlib-devel \
    libpng-devel
```

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/FASTSHIFT/openglcts-mini.git
cd openglcts-mini
```

### 2. 初始化 VK-GL-CTS 子模块

```bash
git submodule update --init --recursive VK-GL-CTS
```

### 3. 构建项目

```bash
mkdir build
cd build
cmake ..
make -j$(nproc)
```

构建完成后，可执行文件将位于 `build/bin/openglcts`。

### 4. 运行测试

```bash
# 全集测试（Surface为FBO，分辨率为256x256）
./bin/openglcts --deqp-archive-dir="../VK-GL-CTS/data" --deqp-surface-type=fbo --deqp-surface-width=256 --deqp-surface-height=256

# 生成测试用例列表
./bin/openglcts --deqp-runmode=xml-caselist --deqp-log-file=cases.xml
```

## 📖 使用指南

### 命令行参数

openglcts 支持以下常用命令行参数：

| 参数 | 说明 | 示例 |
|------|------|------|
| `--deqp-case=<pattern>` | 指定要运行的测试用例（支持通配符） | `--deqp-case=dEQP-GLES2.info.*` |
| `--deqp-log-file=<file>` | 指定输出日志文件 | `--deqp-log-file=result.xml` |
| `--deqp-runmode=xml-caselist` | 生成测试用例列表 | `--deqp-runmode=xml-caselist` |
| `--deqp-quiet` | 静默模式，减少控制台输出 | `--deqp-quiet` |
| `--deqp-archive-dir=<dir>` | 指定数据文件目录 | `--deqp-archive-dir=./data` |

### 测试用例示例

```bash
# 1. 信息查询测试
./bin/openglcts --deqp-case=dEQP-GLES2.info.*

# 2. 能力测试
./bin/openglcts --deqp-case=dEQP-GLES2.capability.*

# 3. 功能测试 - 颜色清除
./bin/openglcts --deqp-case=dEQP-GLES2.functional.color_clear.*

# 4. 功能测试 - 深度测试
./bin/openglcts --deqp-case=dEQP-GLES2.functional.depth.*

# 5. 功能测试 - 着色器
./bin/openglcts --deqp-case=dEQP-GLES2.functional.shaders.*
```

### 查看测试结果

测试结果以 XML 格式保存。每个测试用例的结果包括：

- **Pass**: 测试通过
- **Fail**: 测试失败
- **QualityWarning**: 质量警告
- **CompatibilityWarning**: 兼容性警告
- **NotSupported**: 不支持
- **ResourceError**: 资源错误
- **InternalError**: 内部错误

## 🏗️ 项目结构

```
openglcts-mini/
├── CMakeLists.txt          # 主 CMake 构建文件
├── cts_gles2.cmake         # GLES2 测试套件集成配置
├── main.cpp                # 测试套件入口点
├── LICENSE                 # MIT 许可证
├── README.md               # 本文件
├── vkNullDriver.hpp        # Vulkan null 驱动头文件
├── vkPlatform.hpp          # Vulkan 平台头文件
└── VK-GL-CTS/              # VK-GL-CTS 子模块
    ├── framework/          # 测试框架
    ├── modules/            # 测试模块
    │   └── gles2/         # GLES2 测试
    ├── data/              # 测试数据文件
    └── external/          # 外部依赖
```

## 🔧 CMake 选项

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `ENABLE_DEBUG` | `ON` | 启用调试构建 |
| `BUILD_CTS_GLES2` | `ON` | 构建 GLES2 测试套件 |

使用示例：

```bash
# Release 构建
cmake -DENABLE_DEBUG=OFF ..

# 仅构建主程序，不构建 CTS 模块
cmake -DBUILD_CTS_GLES2=OFF ..
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📝 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

**注意**: VK-GL-CTS 本身采用 Apache 2.0 许可证。使用本项目时，请同时遵守两个许可证的要求。

## 🙏 致谢

- [Khronos Group](https://www.khronos.org/) - VK-GL-CTS 项目
- [VK-GL-CTS](https://github.com/KhronosGroup/VK-GL-CTS) - 上游测试套件

## 📚 相关资源

- [OpenGL ES 2.0 规范](https://www.khronos.org/registry/OpenGL/specs/es/2.0/es_full_spec_2.0.pdf)
- [VK-GL-CTS 文档](https://github.com/KhronosGroup/VK-GL-CTS/blob/main/README.md)
- [EGL 规范](https://www.khronos.org/registry/EGL/)

## ❓ 常见问题

### Q: 为什么需要这个项目？

A: 完整的 VK-GL-CTS 项目非常庞大，包含 Vulkan、OpenGL、OpenGL ES 等多个 API 的测试。本项目提取了 OpenGL ES 2.0 部分，使其更易于集成和使用。

### Q: 如何添加自定义测试？

A: 可以参考 `VK-GL-CTS/modules/gles2/` 目录下的现有测试，按照相同的模式添加新的测试用例。

### Q: 测试失败怎么办？

A: 首先检查日志文件了解失败原因。测试失败可能是由于：
- 驱动程序不完全符合 OpenGL ES 2.0 规范
- 硬件不支持某些特性
- 环境配置问题

### Q: 支持其他 OpenGL ES 版本吗？

A: 当前版本专注于 OpenGL ES 2.0。如果需要其他版本，可以参考本项目的模式进行扩展。

## 📧 联系方式

- 作者: VIFEX
- 项目地址: https://github.com/FASTSHIFT/openglcts-mini
- Issue 跟踪: https://github.com/FASTSHIFT/openglcts-mini/issues

---

⭐ 如果这个项目对你有帮助，请给它一个 Star！
