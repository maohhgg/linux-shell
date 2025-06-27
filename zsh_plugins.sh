#!/bin/bash

# 确保脚本在遇到错误时立即停止执行
set -e

# 更新软件包列表
echo "Updating package lists..."
apt-get update

# 安装必要的软件包
echo "Installing necessary packages..."
apt-get install -y git zsh curl

# 下载并安装 Oh My Zsh
echo "Installing Oh My Zsh..."
# export http_proxy=http://127.0.0.1:1080
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"

# 设置自定义插件和主题的路径
ZSH_CUSTOM="${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}"

# 克隆插件和主题仓库
echo "Cloning Zsh plugins and themes..."
git clone https://github.com/zsh-users/zsh-completions.git   "$ZSH_CUSTOM/plugins/zsh-completions"
git clone --depth=1 https://github.com/romkatv/powerlevel10k.git  "$ZSH_CUSTOM/themes/powerlevel10k"
git clone https://github.com/zsh-users/zsh-autosuggestions.git   "$ZSH_CUSTOM/plugins/zsh-autosuggestions"
git clone https://github.com/zsh-users/zsh-syntax-highlighting.git   "$ZSH_CUSTOM/plugins/zsh-syntax-highlighting"

# 修改 .zshrc 文件以启用主题和插件
echo "Modifying .zshrc file..."
sed -i '/^ZSH_THEME=/c\ZSH_THEME="powerlevel10k/powerlevel10k"' ~/.zshrc
sed -i 's/^plugins=(.*)/plugins=(git zsh-autosuggestions zsh-syntax-highlighting zsh-completions)/' ~/.zshrc

echo "Zsh setup completed successfully!"
