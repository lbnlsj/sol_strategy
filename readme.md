```text
1.API：多个API，需方可以自行填写API地址并命名保存。每种接口会传过来多种类型的TOKEN，比如说我可以保存为A接口，B接口。

2.钱包：需方可以自己增加钱包，秘钥加密保存（前端隐藏）可以命名保存

3.策略：除基本要求外（如图），增加极速模式和防夹模式

4.交易：交易时，可以勾选预先设置好的API和策略还有钱包。   API和钱包可以多选，策略只能单选。多选钱包时，交易时多个钱包同时进行。

5.供方给出详细的搭建和使用文档，现有功能如有bug帮助修复

6.上面几项内容的匹配

```

```text
static/js/
├── index.js              # 主入口文件
├── api.js               # API 请求封装
├── store.js             # 全局状态管理
├── modules/
│   ├── strategy.js      # 策略管理相关
│   ├── wallet.js        # 钱包管理相关
│   ├── settings.js      # 设置管理相关
│   ├── type.js          # 类型管理相关
│   ├── task.js          # 任务管理相关
│   └── log.js           # 日志管理相关
└── utils/
    ├── toast.js         # Toast提示工具
    └── stopLevel.js     # 止盈止损相关计算工具
```