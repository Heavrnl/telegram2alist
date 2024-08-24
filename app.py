import requests
import urllib.parse
import logging
import aiohttp
import telethon
from telethon import TelegramClient, events
from FastTelethonhelper import fast_download
import os
import shutil

# 设置日志
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
PHONE_NUMBER = os.getenv('PHONE_NUMBER')
BASE_URL = os.getenv('BASE_URL')
CHAT_IDS_TO_MONITOR = os.getenv('CHAT_IDS_TO_MONITOR')  # 多个 chat_id，用逗号分隔
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID'))  # 管理员用户 ID 从环境变量中读取

# SERVER_PATH 初始值从环境变量获取
SERVER_PATH = os.getenv('SERVER_PATH')


def get_token(username, password):
    logger.info(f"正在尝试获取用户 {username} 的令牌")
    login_url = f"{BASE_URL}/auth/login"
    logger.info(login_url)
    payload = {
        "username": username,
        "password": password
    }
    response = requests.post(login_url, json=payload)
    logger.info(f"登录响应状态码: {response.status_code}")
    if response.status_code == 200 and response.json().get("data"):
        token = response.json()["data"]["token"]
        logger.info("令牌获取成功")
        return token
    else:
        logger.error(f"获取令牌失败: {response.text}")
        raise Exception(f"获取令牌失败: {response.text}")


def upload_file_to_url(token, server_directory, as_task, local_file_path):
    logger.info(f"正在尝试上传文件: {local_file_path}")
    upload_url = f"{BASE_URL}/fs/form"
    file_size = os.path.getsize(local_file_path)
    local_file_name = os.path.basename(local_file_path)
    file_path = os.path.join(server_directory, local_file_name)

    logger.info(f"文件大小: {file_size}, 服务器路径: {file_path}")
    logger.info(f"file_path: {file_path}")
    logger.info("File-Path:"+urllib.parse.quote(file_path))

    with open(local_file_path, 'rb') as f:
        files = {'file': f}
        headers = {
            'Authorization': token,
            'File-Path': urllib.parse.quote(file_path),
            'As-Task': str(as_task).lower(),
            'Content-Length': str(file_size)
        }
        logger.info(f"正在发送 PUT 请求到 {upload_url}")
        response = requests.put(upload_url, headers=headers, files=files)

    logger.info(f"上传响应状态码: {response.status_code}")
    return response.json()


async def handle_file(event, client):
    logger.info(f"在聊天 {event.chat_id} 中收到消息")

    if str(event.chat_id) not in CHAT_IDS_TO_MONITOR:
        logger.warning(f"在非监控的聊天中收到消息: {event.chat_id}")
        return

    if event.message.media:
        try:
            if isinstance(event.message.media, telethon.tl.types.MessageMediaWebPage):
                logger.info("收到的是一个网页/URL，不处理为媒体文件")
                return

            if not event.message.media.document and not event.message.media.photo and not event.message.media.audio:
                await event.reply("这不是有效的媒体文件")
                logger.warning("收到的媒体不包含文档或照片")
                return

            logger.info("这是个媒体消息")
            await event.reply("已识别媒体文件，开始下载...")

            if not os.path.exists("./tmp/"):
                os.makedirs("./tmp/")
            
            local_file_path = await fast_download(client, event.message, download_folder="./tmp/")
            if not local_file_path:
                logger.error("文件下载失败")
                await event.reply("文件下载失败")
                return

            logger.info(f"文件已下载到: {local_file_path}")

            # 判断 SERVER_PATH 是否包含 "local"
            if "local" in SERVER_PATH:
                # 构建目标路径
                relative_path = SERVER_PATH.replace("/local", "").lstrip("/")
                target_directory = os.path.join("/root/docker/alist/local", relative_path)
                
                # 创建目录（如果不存在）
                if not os.path.exists(target_directory):
                    os.makedirs(target_directory)
                    logger.info(f"创建目录: {target_directory}")

                # 移动文件
                target_file_path = os.path.join(target_directory, os.path.basename(local_file_path))
                shutil.move(local_file_path, target_file_path)
                logger.info(f"文件已移动到: {target_file_path}")
                await event.reply(f"文件已成功移动到 {target_file_path}")
            else:
                logger.info("正在尝试获取令牌")
                token = get_token(USERNAME, PASSWORD)
                logger.info("正在尝试上传文件")
                result = upload_file_to_url(token, SERVER_PATH, False, local_file_path)
                logger.info("文件上传完成")
                await event.reply("文件上传成功")
        except Exception as e:
            logger.error(f"文件处理过程中出错: {str(e)}")
            await event.reply(f"处理文件时出错: {str(e)}")
        finally:
            # 删除临时文件
            if local_file_path and os.path.exists(local_file_path):
                logger.info(f"正在删除临时文件: {local_file_path}")
                os.remove(local_file_path)
    else:
        logger.info("收到的消息不包含媒体文件")


async def set_server_path(event):
    global SERVER_PATH
    
    # 检查是否是管理员发送的指令
    if event.sender_id != ADMIN_USER_ID:
        return

    # 获取用户发送的路径
    new_path = event.message.message.split(" ", 1)[1].strip()
    
    # 更新 SERVER_PATH
    SERVER_PATH = new_path
    logger.info(f"SERVER_PATH 已更新为: {SERVER_PATH}")
    
    # 回复用户
    await event.reply(f"SERVER_PATH 已更新为: {SERVER_PATH}")


async def main():
    logger.info("正在启动客户端")

    client = TelegramClient('session', API_ID, API_HASH)
    await client.start(phone=PHONE_NUMBER)

    # 解析多个 chat_id
    chat_ids = [int(chat_id.strip()) for chat_id in CHAT_IDS_TO_MONITOR.split(',')]

    # 监听消息事件
    @client.on(events.NewMessage(chats=chat_ids))
    async def handler(event):
        if event.message.message.startswith("/setpath"):
            await set_server_path(event)
        else:
            await handle_file(event, client)

    logger.info(f"客户端现在开始监听 {chat_ids} 中的消息")
    await client.run_until_disconnected()


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
