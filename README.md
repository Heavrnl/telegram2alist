### 本项目初衷是用于搭配[XiaoMengXinX/Music163bot-Go](https://github.com/XiaoMengXinX/Music163bot-Go)使用
也可当作监听指定chat里的所有媒体文件，只要捕获到了就会自动上传到指定的alist目录，本质上就是tg to alist

### 初次运行

在docker-compose.yml填入参数

```shell
docker-compose build
docker-compose up --no-start
docker start tg2alist
docker start -ia tg2alist  # 这时你将需要按指引登入账号，一切完成后 Ctrl-P Ctrl-Q 解离
```

完成登入后，考虑到安全性，可以注释掉 `docker-compose.yaml` 里标明的两行（不是必须）。

```shell
docker-compose down  # 先停止运行
vi docker-compose.yaml  # 注释掉标明的两行
```

### 再次运行


```shell
docker-compose up -d
```

然后往你监听的chat发送文件，本项目就会把文件通过alist api传入到你指定的目录
