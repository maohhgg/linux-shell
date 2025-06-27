apt-get update
apt-get git zsh curl

# export http_proxy=http://127.0.0.1:1080
sh -c "$(curl -fsSL https://install.ohmyz.sh/)

ZSH_CUSTOM="${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}"
git clone https://github.com/zsh-users/zsh-completions.git   "$ZSH_CUSTOM/plugins/zsh-completions"
git clone --depth=1 https://github.com/romkatv/powerlevel10k.git  "$ZSH_CUSTOM/themes/powerlevel10k"
git clone https://github.com/zsh-users/zsh-autosuggestions.git   "$ZSH_CUSTOM/plugins/zsh-autosuggestions"
git clone https://github.com/zsh-users/zsh-syntax-highlighting.git   "$ZSH_CUSTOM/plugins/zsh-syntax-highlighting"

sed -i '/^ZSH_THEME=/c\ZSH_THEME="powerlevel10k/powerlevel10k"' ~/.zshrc\nsed -i 's/^plugins=(.*)/plugins=(git zsh-autosuggestions zsh-syntax-highlighting zsh-completions\n)/' ~/.zshrc
