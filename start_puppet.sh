#!/bin/bash
export WECHATY_LOG="verbose"
export WECHATY_PUPPET="wechaty-puppet-wechat"
export WECHATY_PUPPET_SERVER_PORT="8788"
export WECHATY_TOKEN="2de7f518-908a-4553-9535-871c3e84a7ec"
cd $(dirname $0)

docker run -d \
--name wechaty_puppet_service_token_gateway \
--rm \
-e WECHATY_LOG \
-e WECHATY_PUPPET \
-e WECHATY_PUPPET_SERVER_PORT \
-e WECHATY_TOKEN \
-p "$WECHATY_PUPPET_SERVER_PORT:$WECHATY_PUPPET_SERVER_PORT" \
wechaty/wechaty:latest

docker logs --follow wechaty_puppet_service_token_gateway >> logs/puppet.log 2>&1 &
