#! /bin/bash
set -e
set -o pipefail
cd /root/anchored-amazing-race/bot
py_env/bin/pip install -r requirements.txt
pm2 restart bot
cd /root/anchored-amazing-race/dashboard
yarn
yarn build
cp -r /root/anchored-amazing-race/dashboard/dist/* /var/www/anchored-amazing-race/
