# EasyRPG Player libretro 核心完整构建文档

## 概述

本文档记录 EasyRPG Player libretro 核心的完整交叉编译过程，包括所有依赖、遇到的问题及解决方案。

- **目标平台**: aarch64 Linux (RK3326, ArkOS)
- **主机平台**: x86_64 Linux
- **工具链**: GCC 9.2 ARM aarch64
- **EasyRPG Player 版本**: 0.8.1.1 (0-8-1-stable 分支)
- **最终版本号**: 0.8.1.1-arkos4clone@lcdyk

## 目录结构

```
~/Player/
├── cores-aarch64/                    # 最终输出目录
│   ├── easyrpg_libretro.so           # 核心 (6.4MB)
│   ├── liblcf.so.0                   # RPG Maker 解析
│   ├── libicu*.so.66.*               # ICU Unicode 支持
│   ├── libfmt.so.12.2.0              # 格式化库
│   ├── libinih.so.0                  # INI 解析
│   ├── libpixman-1.so.0.38.4         # 像素操作
│   ├── libpng16.so.16.37.0           # PNG 支持
│   ├── libmpg123.so.0.49.4           # MP3 音频
│   ├── libspeexdsp.so.1.2.1          # 音频重采样
│   ├── libogg.so.0.8.6               # OGG 容器
│   ├── libvorbis.so.0.4.9            # OGG Vorbis 音频
│   ├── libvorbisenc.so.2.0.12        # Vorbis 编码器
│   ├── libvorbisfile.so.3.3.8        # Vorbis 文件
│   ├── libopus.so.0.11.1             # Opus 音频
│   ├── libopusfile.so.0.12           # Opus 文件
│   ├── libsndfile.so.1.0.37          # WAV 音频增强
│   ├── libWildMidi.so.2.2.0          # MIDI GUS
│   └── libxmp.so.4.7.1              # Tracker 音乐
├── build-libretro-aarch64/           # 构建目录
├── CMakeLists.txt                    # 已修改
└── src/platform/libretro/ui.cpp      # 已修改
```

## 工具链配置

### 工具链文件

`~/cross-aarch64.cmake` (所有依赖共用):

```cmake
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR aarch64)

set(TOOLCHAIN_PREFIX /opt/toolchains/gcc-arm-9.2-2019.12-x86_64-aarch64-none-linux-gnu/bin/aarch64-none-linux-gnu-)

set(CMAKE_C_COMPILER ${TOOLCHAIN_PREFIX}gcc)
set(CMAKE_CXX_COMPILER ${TOOLCHAIN_PREFIX}g++)
set(CMAKE_AR ${TOOLCHAIN_PREFIX}ar)
set(CMAKE_RANLIB ${TOOLCHAIN_PREFIX}ranlib)
set(CMAKE_STRIP ${TOOLCHAIN_PREFIX}strip)

set(CMAKE_SYSROOT /opt/sysroot)

set(CMAKE_FIND_ROOT_PATH /opt/sysroot)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

set(CMAKE_EXE_LINKER_FLAGS "-L/opt/sysroot/usr/lib/aarch64-linux-gnu -B/opt/sysroot/usr/lib/aarch64-linux-gnu")
set(CMAKE_SHARED_LINKER_FLAGS "-L/opt/sysroot/usr/lib/aarch64-linux-gnu -B/opt/sysroot/usr/lib/aarch64-linux-gnu")
```

### 关键编译参数

| 参数 | 作用 |
|------|------|
| `--sysroot=/opt/sysroot` | 指定目标系统根目录 |
| `-B/opt/sysroot/usr/lib/aarch64-linux-gnu` | 指定 crt1.o 等 C 运行时文件路径 |
| `CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER` | 不在 sysroot 中查找程序 |
| `CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY` | 只在 sysroot 中查找库 |

## Sysroot 准备

### 1. 创建 multiarch 符号链接

sysroot 中的头文件采用 multiarch 目录结构，编译器期望标准路径：

```bash
sudo ln -sf /opt/sysroot/usr/include/aarch64-linux-gnu/bits /opt/sysroot/usr/include/bits
sudo ln -sf /opt/sysroot/usr/include/aarch64-linux-gnu/sys  /opt/sysroot/usr/include/sys
sudo ln -sf /opt/sysroot/usr/include/aarch64-linux-gnu/gnu  /opt/sysroot/usr/include/gnu
sudo ln -sf /opt/sysroot/usr/include/aarch64-linux-gnu/asm  /opt/sysroot/usr/include/asm
```

**问题**: 编译时找不到 `bits/libc-header-start.h`

### 2. 复制缺失的头文件

sysroot 缺少部分头文件，需要从主机或工具链复制：

```bash
# PNG 头文件
sudo cp /usr/include/png.h /opt/sysroot/usr/include/
sudo cp /usr/include/pngconf.h /opt/sysroot/usr/include/
sudo cp /usr/include/libpng16/pnglibconf.h /opt/sysroot/usr/include/

# zlib 头文件
sudo cp /usr/include/zlib.h /opt/sysroot/usr/include/
sudo cp /usr/include/zconf.h /opt/sysroot/usr/include/

# pixman 头文件 (从工具链复制)
sudo cp /opt/toolchains/gcc-arm-9.2-2019.12-x86_64-aarch64-none-linux-gnu/aarch64-none-linux-gnu/libc/usr/include/pixman.h /opt/sysroot/usr/include/

# inih 头文件
git clone https://github.com/benhoyt/inih.git /tmp/inih
sudo cp /tmp/inih/ini.h /opt/sysroot/usr/include/
```

### 3. 创建库符号链接

```bash
sudo ln -sf libpixman-1.so.0 /opt/sysroot/usr/lib/aarch64-linux-gnu/libpixman-1.so
sudo ln -sf libinih.so.0 /opt/sysroot/usr/lib/aarch64-linux-gnu/libinih.so
```

## 依赖编译

### 依赖列表

| 库 | 版本 | 用途 | 编译方式 |
|---|------|------|---------|
| ICU | 66.1 | Unicode 文本处理 | autotools (交叉编译) |
| liblcf | 0.8.1 | RPG Maker 数据解析 | cmake |
| fmt | 12.2 | 文本格式化 | cmake |
| inih | - | INI 文件解析 | 使用 sysroot |
| pixman | 0.38 | 像素操作 | 使用 sysroot |
| libpng | 1.6 | PNG 支持 | 使用 sysroot |
| libspeexdsp | 1.2.1 | 音频重采样 | cmake |
| mpg123 | 1.49.4 | MP3 音频 | autotools |
| libogg | 1.3.6 | OGG 容器 | cmake |
| libvorbis | 1.3.7 | OGG Vorbis 音频 | cmake |
| opus | 1.5.2 | Opus 音频 | cmake |
| opusfile | 0.12 | Opus 文件 | cmake |
| libsndfile | 1.2.2 | WAV 音频增强 | cmake |
| WildMidi | 0.5.0 | MIDI GUS | cmake |
| libxmp | 4.7.1 | Tracker 音乐 | cmake |
| fluidsynth | - | MIDI SoundFont | 跳过 (需要 GLib2) |
| harfbuzz | - | 文本整形 | 跳过 (需要 GLib2) |

### 1. ICU 66.1

**问题**: sysroot 的 ICU 库与交叉编译器 C++ ABI 不兼容

**解决方案**: 从源码编译 ICU

```bash
# 克隆
git clone --depth 1 --branch release-66-1 https://github.com/unicode-org/icu.git icu66

# 编译主机版本 (交叉编译需要)
cd icu66/icu4c
mkdir -p build-host && cd build-host
../source/configure --disable-tests --disable-samples
make -j$(nproc)

# 创建交叉编译脚本
cat > cross-compile-aarch64.sh << 'EOF'
#!/bin/bash
set -e
ICU_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$ICU_DIR/build-aarch64"

export CC=/opt/toolchains/gcc-arm-9.2-2019.12-x86_64-aarch64-none-linux-gnu/bin/aarch64-none-linux-gnu-gcc
export CXX=/opt/toolchains/gcc-arm-9.2-2019.12-x86_64-aarch64-none-linux-gnu/bin/aarch64-none-linux-gnu-g++
export CFLAGS="--sysroot=/opt/sysroot -O2 -B/opt/sysroot/usr/lib/aarch64-linux-gnu"
export CXXFLAGS="--sysroot=/opt/sysroot -O2 -B/opt/sysroot/usr/lib/aarch64-linux-gnu"
export LDFLAGS="--sysroot=/opt/sysroot -L/opt/sysroot/usr/lib/aarch64-linux-gnu -B/opt/sysroot/usr/lib/aarch64-linux-gnu"

mkdir -p "$BUILD_DIR" && cd "$BUILD_DIR"

"$ICU_DIR/source/configure" \
    --host=aarch64-linux-gnu \
    --prefix=/usr \
    --enable-shared \
    --disable-static \
    --with-cross-build="$ICU_DIR/build-host" \
    --disable-tests \
    --disable-samples \
    --disable-dyload

make -j$(nproc)
sudo make DESTDIR=/opt/sysroot install
EOF
chmod +x cross-compile-aarch64.sh
./cross-compile-aarch64.sh
```

**关键点**:
- 必须先编译主机版本
- `--with-cross-build` 指向主机版本
- 使用 `DESTDIR=/opt/sysroot` 安装

### 2. liblcf

```bash
git clone --recursive https://github.com/EasyRPG/liblcf

cd liblcf
cmake -B build-aarch64 \
    -DCMAKE_TOOLCHAIN_FILE=/home/lcdyk/cross-aarch64.cmake \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=ON \
    -DCMAKE_INSTALL_PREFIX=/usr \
    -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
    -DLIBLCF_WITH_INI=ON \
    -DLIBLCF_WITH_ICU=ON

make -C build-aarch64 -j$(nproc)
sudo make -C build-aarch64 DESTDIR=/opt/sysroot install
```

**问题**: 
- `Could NOT find inih` → 需要创建 `libinih.so` 符号链接
- ICU ABI 不兼容 → 需要先编译 ICU

### 3. fmt

```bash
git clone https://github.com/fmtlib/fmt.git

cd fmt
cmake -B build-aarch64 \
    -DCMAKE_TOOLCHAIN_FILE=/home/lcdyk/cross-aarch64.cmake \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=ON \
    -DFMT_TEST=OFF \
    -DFMT_DOC=OFF \
    -DCMAKE_INSTALL_PREFIX=/usr

make -C build-aarch64 -j$(nproc)
sudo make -C build-aarch64 DESTDIR=/opt/sysroot install
```

### 4. libspeexdsp

```bash
git clone https://github.com/xiph/speexdsp.git

cd speexdsp
cmake -B build-aarch64 \
    -DCMAKE_TOOLCHAIN_FILE=/home/lcdyk/cross-aarch64.cmake \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=ON \
    -DCMAKE_INSTALL_PREFIX=/usr \
    -DTESTS=OFF

make -C build-aarch64 -j$(nproc)
sudo make -C build-aarch64 DESTDIR=/opt/sysroot install
```

**问题**: 原始仓库是 autotools 构建，需要创建 CMakeLists.txt

### 5. mpg123

```bash
git clone https://github.com/madebr/mpg123.git

cd mpg123
export CC=/opt/toolchains/gcc-arm-9.2-2019.12-x86_64-aarch64-none-linux-gnu/bin/aarch64-none-linux-gnu-gcc
export CFLAGS="--sysroot=/opt/sysroot -O2"
export LDFLAGS="--sysroot=/opt/sysroot -L/opt/sysroot/usr/lib/aarch64-linux-gnu -B/opt/sysroot/usr/lib/aarch64-linux-gnu"

./configure --host=aarch64-linux-gnu --prefix=/usr --enable-shared --disable-static
make -j$(nproc)
sudo make DESTDIR=/opt/sysroot install
```

**问题**: 需要 `fmt123.h` 头文件

### 6. libogg

```bash
git clone https://github.com/xiph/ogg.git

cd ogg
cmake -B build-aarch64 \
    -DCMAKE_TOOLCHAIN_FILE=/home/lcdyk/cross-aarch64.cmake \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=ON \
    -DCMAKE_INSTALL_PREFIX=/usr \
    -DBUILD_TESTING=OFF

make -C build-aarch64 -j$(nproc)
sudo make -C build-aarch64 DESTDIR=/opt/sysroot install
```

**问题**: cmake 配置文件路径不正确，需要手动创建符号链接

### 7. libvorbis

```bash
git clone https://github.com/xiph/vorbis.git

cd vorbis
cmake -B build-aarch64 \
    -DCMAKE_TOOLCHAIN_FILE=/home/lcdyk/cross-aarch64.cmake \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=ON \
    -DCMAKE_INSTALL_PREFIX=/usr \
    -DBUILD_TESTING=OFF

make -C build-aarch64 -j$(nproc)
sudo make -C build-aarch64 DESTDIR=/opt/sysroot install
```

**问题**: 库版本号不匹配，需要手动创建符号链接

### 8. opus

```bash
git clone https://github.com/xiph/opus.git

cd opus
cmake -B build-aarch64 \
    -DCMAKE_TOOLCHAIN_FILE=/home/lcdyk/cross-aarch64.cmake \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=ON \
    -DCMAKE_INSTALL_PREFIX=/usr \
    -DOPUS_BUILD_TESTING=OFF \
    -DOPUS_BUILD_PROGRAMS=OFF

make -C build-aarch64 -j$(nproc)
sudo make -C build-aarch64 DESTDIR=/opt/sysroot install
```

### 9. opusfile

```bash
git clone https://github.com/xiph/opusfile.git

cd opusfile
# 修复 doxygen 依赖
sed -i 's/find_package(Doxygen)/#find_package(Doxygen)/' CMakeLists.txt

PKG_CONFIG_PATH=/opt/sysroot/usr/lib/pkgconfig cmake -B build-aarch64 \
    -DCMAKE_TOOLCHAIN_FILE=/home/lcdyk/cross-aarch64.cmake \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=ON \
    -DCMAKE_INSTALL_PREFIX=/usr \
    -DOP_DISABLE_HTTP=ON \
    -DOP_DISABLE_EXAMPLES=ON

make -C build-aarch64 -j$(nproc)
sudo make -C build-aarch64 DESTDIR=/opt/sysroot install
```

**问题**:
- `Doxygen was not found` → 注释掉 doxygen 相关行
- `PkgConfig::Ogg target not found` → 手动创建 OggTargets.cmake

### 10. libsndfile

```bash
git clone https://github.com/libsndfile/libsndfile.git

cd libsndfile
cmake -B build-aarch64 \
    -DCMAKE_TOOLCHAIN_FILE=/home/lcdyk/cross-aarch64.cmake \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=ON \
    -DCMAKE_INSTALL_PREFIX=/usr \
    -DBUILD_PROGRAMS=OFF \
    -DBUILD_EXAMPLES=OFF \
    -DBUILD_TESTING=OFF \
    -DENABLE_EXTERNAL_LIBS=OFF

make -C build-aarch64 -j$(nproc)
sudo make -C build-aarch64 DESTDIR=/opt/sysroot install
```

**问题**: `FLAC::FLAC target not found` → 禁用外部库

### 11. WildMidi

```bash
git clone https://github.com/Mindwerks/wildmidi.git

cd wildmidi
cmake -B build-aarch64 \
    -DCMAKE_TOOLCHAIN_FILE=/home/lcdyk/cross-aarch64.cmake \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=ON \
    -DCMAKE_INSTALL_PREFIX=/usr \
    -DWANT_PLAYER=OFF

make -C build-aarch64 -j$(nproc)
sudo make -C build-aarch64 DESTDIR=/opt/sysroot install
```

### 12. libxmp

```bash
git clone https://github.com/libxmp/libxmp.git

cd libxmp
cmake -B build-aarch64 \
    -DCMAKE_TOOLCHAIN_FILE=/home/lcdyk/cross-aarch64.cmake \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=ON \
    -DCMAKE_INSTALL_PREFIX=/usr

make -C build-aarch64 -j$(nproc)
sudo make -C build-aarch64 DESTDIR=/opt/sysroot install
```

## EasyRPG Player 编译

### 1. 克隆并切换版本

```bash
cd ~
git clone https://github.com/EasyRPG/Player/
cd Player
git fetch origin 0-8-1-stable
git checkout -b 0-8-1-stable FETCH_HEAD
git submodule update --init
```

### 2. 创建工具链文件

`~/Player/aarch64-toolchain.cmake` (同上)

### 3. 创建 SDL2 CMake 配置

```bash
mkdir -p /tmp/sdl2-aarch64/lib/cmake/SDL2
cat > /tmp/sdl2-aarch64/lib/cmake/SDL2/SDL2Config.cmake << 'EOF'
set(SDL2_FOUND ON)
set(SDL2_INCLUDE_DIRS "/opt/sysroot/usr/include/SDL2")
set(SDL2_LIBRARIES "/opt/sysroot/usr/lib/aarch64-linux-gnu/libSDL2.so")
set(SDL2_VERSION "2.24.0")
if(NOT TARGET SDL2::SDL2)
    add_library(SDL2::SDL2 SHARED IMPORTED)
    set_target_properties(SDL2::SDL2 PROPERTIES
        IMPORTED_LOCATION "/opt/sysroot/usr/lib/aarch64-linux-gnu/libSDL2.so"
        INTERFACE_INCLUDE_DIRECTORIES "/opt/sysroot/usr/include/SDL2"
    )
endif()
EOF
```

**问题**: sysroot 中的 `sdl2-config.cmake` 会覆盖我们的配置，需要备份：
```bash
sudo mv /opt/sysroot/usr/lib/aarch64-linux-gnu/cmake/SDL2/sdl2-config.cmake \
        /opt/sysroot/usr/lib/aarch64-linux-gnu/cmake/SDL2/sdl2-config.cmake.bak
```

### 4. 创建 Ogg cmake 配置

**问题**: `PkgConfig::Ogg target not found`

```bash
cat << 'EOF' | sudo tee /opt/sysroot/usr/lib/cmake/Ogg/OggTargets.cmake > /dev/null
if(NOT TARGET PkgConfig::Ogg)
    add_library(PkgConfig::Ogg SHARED IMPORTED)
    set_target_properties(PkgConfig::Ogg PROPERTIES
        IMPORTED_LOCATION "/opt/sysroot/usr/lib/aarch64-linux-gnu/libogg.so"
        INTERFACE_INCLUDE_DIRECTORIES "/opt/sysroot/usr/include"
    )
endif()
if(NOT TARGET Ogg::ogg)
    add_library(Ogg::ogg SHARED IMPORTED)
    set_target_properties(Ogg::ogg PROPERTIES
        IMPORTED_LOCATION "/opt/sysroot/usr/lib/aarch64-linux-gnu/libogg.so"
        INTERFACE_INCLUDE_DIRECTORIES "/opt/sysroot/usr/include"
    )
endif()
EOF
```

### 5. 创建库符号链接

**问题**: cmake 配置文件引用的库路径与实际路径不匹配

```bash
# ogg
sudo ln -sf /opt/sysroot/usr/lib/aarch64-linux-gnu/libogg.so.0.8.6 /opt/sysroot/usr/lib/libogg.so.0.8.6
sudo ln -sf /opt/sysroot/usr/lib/aarch64-linux-gnu/libogg.so.0 /opt/sysroot/usr/lib/libogg.so.0
sudo ln -sf /opt/sysroot/usr/lib/aarch64-linux-gnu/libogg.so /opt/sysroot/usr/lib/libogg.so

# vorbis (需要先删除旧的符号链接)
sudo rm -f /opt/sysroot/usr/lib/libvorbis.so*
sudo cp /home/lcdyk/vorbis/build-aarch64/lib/libvorbis.so.0.4.9 /opt/sysroot/usr/lib/
sudo ln -sf libvorbis.so.0.4.9 /opt/sysroot/usr/lib/libvorbis.so.0
sudo ln -sf libvorbis.so.0.4.9 /opt/sysroot/usr/lib/libvorbis.so
```

### 6. 配置 CMake

```bash
cd ~/Player
rm -rf build-libretro-aarch64
PKG_CONFIG_PATH=/opt/sysroot/usr/lib/pkgconfig cmake -B build-libretro-aarch64 \
    -DCMAKE_TOOLCHAIN_FILE=aarch64-toolchain.cmake \
    -DCMAKE_BUILD_TYPE=Release \
    -DPLAYER_TARGET_PLATFORM=libretro \
    -DBUILD_SHARED_LIBS=ON \
    -DCMAKE_POLICY_VERSION_MINIMUM=3.5
```

### 7. 编译

```bash
make -C build-libretro-aarch64 -j$(nproc)
```

## 代码修改

### 1. 版本号修改

`CMakeLists.txt` 第 507 行：

```cmake
# 原来
set(PLAYER_VERSION_GIT "")
git_get_exact_tag(GIT_TAG)
# ... (30行 git 描述代码)

# 改为
set(PLAYER_VERSION_GIT "arkos4clone@lcdyk")
string(APPEND PLAYER_VERSION_FULL "-${PLAYER_VERSION_GIT}")
```

### 2. console_detect 检测

`src/platform/libretro/ui.cpp` 第 433 行：

```cpp
#include <unistd.h>

RETRO_API bool retro_load_game(const struct retro_game_info* game) {
    // ... 原有代码 ...

    // 检测 console_detect
    if (access("/usr/local/bin/console_detect", F_OK) != 0)
        return false;

    FILE* fp = popen("/usr/local/bin/console_detect -o", "r");
    if (fp) {
        char buf[16] = {0};
        if (fgets(buf, sizeof(buf), fp)) {
            int rotation = atoi(buf);
            pclose(fp);
            if (rotation != 0 && rotation != 90 && rotation != 180 && rotation != 270)
                return false;
        } else {
            pclose(fp);
            return false;
        }
    } else {
        return false;
    }

    // ... 原有代码 ...
}
```

## 目标设备部署

### 1. 复制文件

```bash
# 复制核心和依赖到设备
scp ~/Player/cores-aarch64/* user@device:/home/ark/.config/retroarch/cores/easyrpg_lib/
```

### 2. 创建符号链接

```bash
# 在设备上
cd /home/ark/.config/retroarch/cores/easyrpg_lib
ln -sf libspeexdsp.so.1.2.1 libspeexdsp.so.6
ln -sf libxmp.so.4.7.1 libxmp.so.4
```

### 3. 运行

```bash
export LD_LIBRARY_PATH=/home/ark/.config/retroarch/cores/easyrpg_lib:$LD_LIBRARY_PATH
/usr/local/bin/retroarch -L /home/ark/.config/retroarch/cores/easyrpg_libretro.so /roms/easyrpg/game/
```

## 问题总结

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `bits/libc-header-start.h` not found | multiarch 目录结构 | 创建符号链接 |
| ICU ABI 不兼容 | sysroot ICU 版本旧 | 从源码编译 ICU |
| `Could NOT find inih` | 缺少符号链接 | `ln -sf libinih.so.0 libinih.so` |
| `Doxygen was not found` | 缺少 doxygen | 注释掉 CMakeLists.txt 中的 doxygen |
| `PkgConfig::Ogg target not found` | cmake 配置问题 | 手动创建 OggTargets.cmake |
| `libxmp.so.4: version XMP_4.5 not found` | 系统库版本旧 | 使用编译的库 + LD_LIBRARY_PATH |
| `libspeexdsp.so.6` not found | 库名不匹配 | 创建符号链接 |
| 库路径不匹配 | cmake 配置引用错误路径 | 在 `/usr/lib/` 创建符号链接 |
| `FLAC::FLAC target not found` | 缺少 FLAC | `-DENABLE_EXTERNAL_LIBS=OFF` |
| SDL2 配置被覆盖 | sysroot 有旧配置 | 备份旧配置文件 |

## 依赖关系图

```
easyrpg_libretro.so
├── liblcf.so.0
│   ├── libicui18n.so.66
│   ├── libicuuc.so.66
│   │   └── libicudata.so.66
│   ├── libinih.so.0
│   └── libexpat.so.1 (系统)
├── libpng16.so.16
├── libfmt.so.12
├── libpixman-1.so.0
├── libspeexdsp.so.6
├── libmpg123.so.0
├── libsndfile.so.1
│   ├── libogg.so.0
│   └── libvorbis.so.0
├── libvorbisfile.so.3.3.8
│   ├── libvorbis.so.0.4.9
│   └── libogg.so.0
├── libopusfile.so.0
│   ├── libopus.so.0
│   └── libogg.so.0
├── libWildMidi.so.2
├── libxmp.so.4
├── libstdc++.so.6 (系统)
├── libgcc_s.so.1 (系统)
└── libc.so.6 (系统)
```

## 编译时间参考

| 步骤 | 时间 |
|------|------|
| ICU 编译 | ~10 分钟 |
| liblcf 编译 | ~2 分钟 |
| 其他依赖 | ~1-2 分钟/个 |
| EasyRPG Player | ~3 分钟 |
| 总计 | ~30 分钟 |

## 注意事项

1. **库版本符号链接**: 目标设备的系统库版本可能与编译的版本不同，需要创建符号链接
2. **LD_LIBRARY_PATH**: 必须设置才能使用编译的库而不是系统库
3. **pkg-config**: 许多 cmake 配置依赖 pkg-config，需要设置 `PKG_CONFIG_PATH`
4. **sysroot 准备**: 首次编译需要大量时间准备 sysroot
5. **子模块**: 必须 `git submodule update --init` 否则编译失败
