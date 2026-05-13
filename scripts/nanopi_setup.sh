#!/bin/bash
# NanoPi 환경 설치 스크립트 — 백그라운드 실행용
# 실행: nohup bash ~/nanopi_setup.sh > ~/nanopi_setup.log 2>&1 &

set -e
LOG=~/nanopi_setup.log

echo "[$(date)] === 1. 기본 패키지 설치 ===" | tee -a $LOG
sudo apt-get update -qq 2>&1 | tail -3 | tee -a $LOG
sudo apt-get install -y git curl build-essential nginx ffmpeg python3-pip python3-venv 2>&1 | tail -5 | tee -a $LOG
echo "[$(date)] 기본 패키지 OK" | tee -a $LOG

echo "[$(date)] === 2. yt-dlp 설치 ===" | tee -a $LOG
sudo curl -sL https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp
sudo chmod +x /usr/local/bin/yt-dlp
yt-dlp --version | tee -a $LOG

echo "[$(date)] === 3. nvm 설치 ===" | tee -a $LOG
export NVM_DIR="$HOME/.nvm"
if [ ! -s "$NVM_DIR/nvm.sh" ]; then
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash 2>&1 | tail -5 | tee -a $LOG
fi
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
echo "[$(date)] nvm OK" | tee -a $LOG

echo "[$(date)] === 4. Node.js 22 설치 ===" | tee -a $LOG
nvm install 22 2>&1 | tail -5 | tee -a $LOG
nvm alias default 22
echo "Node: $(node --version)  npm: $(npm --version)" | tee -a $LOG

echo "[$(date)] === 5. node/npm 시스템 링크 ===" | tee -a $LOG
sudo ln -sf "$(which node)" /usr/local/bin/node
sudo ln -sf "$(which npm)" /usr/local/bin/npm
echo "symlink OK" | tee -a $LOG

echo "[$(date)] === 6. nginx 설정 ===" | tee -a $LOG
cat > /tmp/voicechat_nginx.conf << 'NGINX'
server {
    listen 80;
    server_name voicechat.tyranno.xyz localhost;

    location / {
        proxy_pass http://127.0.0.1:8090;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }
}
NGINX
sudo cp /tmp/voicechat_nginx.conf /etc/nginx/sites-available/voicechat
sudo ln -sf /etc/nginx/sites-available/voicechat /etc/nginx/sites-enabled/voicechat
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t 2>&1 | tee -a $LOG && sudo systemctl enable nginx && sudo systemctl restart nginx
echo "[$(date)] nginx OK" | tee -a $LOG

echo "[$(date)] === 7. Python3 패키지 ===" | tee -a $LOG
pip3 install --user google-cloud-speech numpy websockets 2>&1 | tail -5 | tee -a $LOG

echo "[$(date)] === 8. openclaw 전역 설치 ===" | tee -a $LOG
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
npm install -g openclaw 2>&1 | tail -5 | tee -a $LOG
openclaw --version | tee -a $LOG

echo "[$(date)] === 9. ~/.bashrc에 nvm 추가 확인 ===" | tee -a $LOG
grep -q 'nvm.sh' ~/.bashrc || cat >> ~/.bashrc << 'BASHRC'

# nvm
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
BASHRC
echo "[$(date)] bashrc OK" | tee -a $LOG

echo "[$(date)] === 완료 ===" | tee -a $LOG
git --version
node --version
npm --version
nginx -v 2>&1
ffmpeg -version 2>&1 | head -1
yt-dlp --version
openclaw --version 2>/dev/null || echo "openclaw 경로 확인 필요"
df -h /
echo "[$(date)] ALL DONE" | tee -a $LOG
