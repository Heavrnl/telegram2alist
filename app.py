import requests
import urllib.parse
import logging
import aiohttp
import telethon
from telethon import TelegramClient, events

import os

# 设置日志
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
PHONE_NUMBER = os.getenv('PHONE_NUMBER')
BASE_URL = os.getenv('BASE_URL')
CHAT_IDS_TO_MONITOR = os.getenv('CHAT_IDS_TO_MONITOR')  # 现在是多个 chat_id，用逗号分隔
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
SERVER_PATH = os.getenv('SERVER_PATH')

def get_token(username, password):
    logger.info(f"username:{username}")    
    logger.info(f"password:{password}")    
    logger.debug(f"正在尝试获取用户 {username} 的令牌")
    login_url = f"{BASE_URL}/auth/login"
    payload = {
        "username": username,
        "password": password
    }
    response = requests.post(login_url, json=payload)
    logger.debug(f"登录响应状态码: {response.status_code}")
    if response.status_code == 200 and response.json().get("data"):
        token = response.json()["data"]["token"]
        logger.info("令牌获取成功")
        return token
    else:
        logger.error(f"获取令牌失败: {response.text}")
        raise Exception(f"获取令牌失败: {response.text}")

def upload_file_to_url(token, server_directory, as_task, local_file_path):
    logger.debug(f"正在尝试上传文件: {local_file_path}")
    upload_url = f"{BASE_URL}/fs/form"
    file_size = os.path.getsize(local_file_path)
    local_file_name = os.path.basename(local_file_path)
    file_path = os.path.join(server_directory, local_file_name)

    logger.debug(f"文件大小: {file_size}, 服务器路径: {file_path}")

    with open(local_file_path, 'rb') as f:
        files = {'file': f}
        headers = {
            'Authorization': token,
            'File-Path': urllib.parse.quote(file_path),
            'As-Task': str(as_task).lower(),
            'Content-Length': str(file_size)
        }
        logger.debug(f"正在发送 PUT 请求到 {upload_url}")
        response = requests.put(upload_url, headers=headers, files=files)

    logger.debug(f"上传响应状态码: {response.status_code}")
    return response.json()

async def handle_file(event):
    logger.info(f"在聊天 {event.chat_id} 中收到消息")

    if str(event.chat_id) not in CHAT_IDS_TO_MONITOR:
        logger.warning(f"在非监控的聊天中收到消息: {event.chat_id}")
        return

    if event.message.media:
        try:
            if isinstance(event.message.media, telethon.tl.types.MessageMediaWebPage):
                logger.info("收到的是一个网页/URL，不处理为媒体文件")
                return

            # 检查是否为媒体消息
            if not event.message.media.document and not event.message.media.photo and not event.message.media.audio:
                await event.reply("这不是有效的媒体文件")
                logger.warning("收到的媒体不包含文档或照片")
                return

            logger.info("这是个媒体消息")
            await event.reply("已识别媒体文件，开始下载...")

            logger.info("正在下载文件")
            if not os.path.exists("./tmp/"):
                os.makedirs("./tmp/")
            local_file_path = await event.message.download_media(file="./tmp/")
            if not local_file_path:
                logger.error("文件下载失败")
                await event.reply("文件下载失败")
                return

            logger.debug(f"文件已下载到: {local_file_path}")
            logger.info("正在尝试获取令牌")

            token = get_token(USERNAME, PASSWORD)
            logger.info("正在尝试上传文件")
            result = upload_file_to_url(token, SERVER_PATH, False, local_file_path)
            logger.info("文件上传完成")
            await event.reply(f"文件上传成功")
        except Exception as e:
            logger.error(f"文件处理过程中出错: {str(e)}")
            await event.reply(f"处理文件时出错: {str(e)}")
        finally:
            if local_file_path and os.path.exists(local_file_path):
                logger.debug(f"正在删除临时文件: {local_file_path}")
                os.remove(local_file_path)
    else:
        logger.info("收到的消息不包含媒体文件")

async def main():
    logger.info("正在启动客户端")
    logger.info(f"Retrieved password: {PASSWORD}")
    
    client = TelegramClient('session', API_ID, API_HASH)
    await client.start(phone=PHONE_NUMBER)

    # 解析多个 chat_id
    chat_ids = [int(chat_id.strip()) for chat_id in CHAT_IDS_TO_MONITOR.split(',')]
    
    @client.on(events.NewMessage(chats=chat_ids))
    async def handler(event):
        await handle_file(event)

    logger.info(f"客户端现在开始监听 {chat_ids} 中的消息")
    await client.run_until_disconnected()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
