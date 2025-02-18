# Flask应用部署教程 - Ubuntu服务器


## 1. 环境准备

首先，确保你的Ubuntu服务器已经安装了必要的基础软件：

```bash
# 更新包列表
sudo apt update
sudo apt upgrade -y

# 安装Python3和pip
sudo apt install python3 python3-pip -y

# 安装git
sudo apt install git -y

# 安装虚拟环境工具
sudo apt install python3-venv -y
```

## 2. 克隆项目

```bash
# 切换到需要部署的目录
cd /var/www

# 克隆项目
git clone https://github.com/lbnlsj/sol_strategy.git

# 进入项目目录
cd sol_strategy
```

## 3. 创建并激活虚拟环境（默认可忽略）

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate
```

## 4. 安装项目依赖

```bash
# 升级pip
pip install --upgrade pip

# 安装项目依赖
pip install -r requirements.txt
```

## 6. 测试应用

在正式部署前，先测试应用是否能正常运行：

```bash
# 确保在项目目录下并已激活虚拟环境
python app.py
```

如果能够正常访问应用（默认地址是 http://localhost:5000），则说明应用运行正常。

## 7. 后台运行应用

有两种方式可以让应用在后台运行：

### 方式一：使用nohup

```bash
# 在项目根目录下
nohup python app.py > app.log 2>&1 &

# 查看进程
ps aux | grep python

# 查看日志
tail -f app.log
```

### 方式二：使用Supervisor



## 注意事项

1. 确保服务器防火墙允许相应端口的访问（默认是5000端口）
4. 建议配置日志轮转，避免日志文件过大
5. 定期备份重要数据

## 故障排查

如果应用无法正常运行，请检查：

1. 查看错误日志：
```bash
tail -f app.log
# 或
sudo supervisorctl tail sol_strategy
```

2. 检查端口占用：
```bash
sudo lsof -i :5000
```

3. 检查Python虚拟环境是否正确激活：
```bash
which python
```

4. 检查所有依赖是否正确安装：
```bash
pip freeze
```

如果仍然有问题，可以查看应用的详细日志来定位具体原因。

### 需求
```text
1.API：多个API，需方可以自行填写API地址并命名保存。每种接口会传过来多种类型的TOKEN，比如说我可以保存为A接口，B接口。

2.钱包：需方可以自己增加钱包，秘钥加密保存（前端隐藏）可以命名保存

3.策略：除基本要求外（如图），增加极速模式和防夹模式

4.交易：交易时，可以勾选预先设置好的API和策略还有钱包。   API和钱包可以多选，策略只能单选。多选钱包时，交易时多个钱包同时进行。

5.供方给出详细的搭建和使用文档，现有功能如有bug帮助修复

6.上面几项内容的匹配

```
