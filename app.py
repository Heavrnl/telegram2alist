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
CHAT_ID_TO_MONITOR = os.getenv('CHAT_ID_TO_MONITOR')
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


# async def download_file_chunk(session, url, start, end, chunk_num, temp_dir):
#     headers = {'Range': f'bytes={start}-{end}'}
#     chunk_path = os.path.join(temp_dir, f'chunk_{chunk_num}')
#
#     async with session.get(url, headers=headers) as response:
#         if response.status == 206:  # Partial Content
#             with open(chunk_path, 'wb') as f:
#                 while True:
#                     chunk = await response.content.read(1024)
#                     if not chunk:
#                         break
#                     f.write(chunk)
#         else:
#             raise Exception(f"Failed to download chunk {chunk_num}: {response.status}")
#     return chunk_path
#
#
# async def download_media(url, dest_file_path, num_chunks=8):
#     async with aiohttp.ClientSession() as session:
#         async with session.head(url) as response:
#             total_size = int(response.headers['Content-Length'])
#
#         chunk_size = total_size // num_chunks
#         ranges = [(i * chunk_size, (i + 1) * chunk_size - 1) for i in range(num_chunks)]
#         ranges[-1] = (ranges[-1][0], total_size - 1)  # Adjust the last chunk range
#
#         temp_dir = './temp_chunks'
#         os.makedirs(temp_dir, exist_ok=True)
#
#         tasks = [download_file_chunk(session, url, start, end, i, temp_dir) for i, (start, end) in enumerate(ranges)]
#         chunk_paths = await asyncio.gather(*tasks)
#
#         with open(dest_file_path, 'wb') as dest_file:
#             for chunk_path in chunk_paths:
#                 with open(chunk_path, 'rb') as chunk_file:
#                     dest_file.write(chunk_file.read())
#                 os.remove(chunk_path)
#
#         os.rmdir(temp_dir)
#
#     return dest_file_path

async def handle_file(event):
    logger.info(f"在聊天 {event.chat_id} 中收到消息")

    if str(event.chat_id) != CHAT_ID_TO_MONITOR:
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

    @client.on(events.NewMessage(chats=int(CHAT_ID_TO_MONITOR)))
    async def handler(event):
        await handle_file(event)

    logger.info("客户端现在开始监听消息")
    await client.run_until_disconnected()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
