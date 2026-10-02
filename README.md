# 易学占卜 Agent

本地运行的六爻 / 梅花易数占卜程序，提供命令行与网页两种用法。网页可 `--host 0.0.0.0` 开放给局域网内他人使用。

## 设计原则

**「算」的环节全部写成确定性代码，「解」的环节才交给模型。**

判断标准：如果模型答错了自己也不会察觉，就必须代码化。

- 卦名、纳甲、世应、六亲、六神、旬空、体用生克 —— 一旦算错，模型毫无察觉，因此**全部硬编码在 `app/core/`**，由查表与算法得出，给定输入必得同一结果；这一层不联网、不调用模型，可独立测试。
- 「这句话问的是什么事」与「这个卦象意味着什么」—— 才交给模型。

## 工作流节点

```
[输入] 问题 + 起卦方式
   │
   ├─ N1 问题理解   LLM   问题 → {事项枚举, 性别}      （起卦方式由用户指定）
   ├─ N2 取时       code  前端传时间 / 服务器当前时间
   ├─ N3 历法换算   code  → 农历、四柱干支、月建、日辰、旬空   [lunar-python]
   ├─ N4 起卦       code  六爻:掷数→本卦+动爻+变卦 ｜ 梅花:报数/时间→本卦+互卦+变卦
   ├─ N5 排盘       code  六爻:纳甲·八宫·世应·六亲·六神·旬空 ｜ 梅花:体用·互·变
   ├─ N6 定用神     code  事项枚举 + 知识库 3.5 表 → 用神爻位
   ├─ N7 解读       LLM   排盘 JSON + 知识库全文 → 卦象解读
   └─ [输出] 结构化成卦单（网页渲染 + 流式解读）
```

**N2–N6 是纯函数**（`app/pipeline.py` 的 `build_result`），不碰网络与模型。**N1 / N7 是仅有的两个 LLM 节点**（`app/llm/`），由路由层编排。

## 安装

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env             # 按需填 LLM_API_KEY
```

依赖：`fastapi` / `uvicorn` / `openai` / `pydantic`(v2) / `pydantic-settings` / `lunar-python`；测试另需 `pytest`、`cnlunar`。

历法核心用 **`lunar-python`**（纯 Python，有 cp314 轮子）。`sxtwl` 需在 Windows 上现场编译 C++ 且无 cp314 轮子，故未采用。

## 运行

**网页**

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

浏览器打开 http://127.0.0.1:8000/ 。

**给手机 / 局域网内他人使用**：`--host` 必须是 `0.0.0.0`（`127.0.0.1` 是回环地址，只有本机能连，手机打不开）。查机器局域网 IP：

```bash
ipconfig        # 找 WLAN 适配器的 IPv4，例如 192.168.10.3
```

手机连**同一个 Wi-Fi**，访问 `http://192.168.10.3:8000/`。若仍打不开，多半是路由器开了「AP 隔离 / 客户端隔离」，或用了访客网络。

注意：这样同一网络下任何人都能打开这个页面，且没有任何鉴权。`LLM_API_KEY` 只在服务端使用，不会下发到浏览器。

**命令行**（无 Key 也能出完整排盘）

```bash
python -m app.cli -q "近期的工作变动会顺利吗"                  # 六爻
python -m app.cli -q "这笔钱能收回来吗" -m meihua_number -n 7 13
python -m app.cli -q "今年运势" -m meihua_time --at "2026-10-01 09:30"
python -m app.cli -q "随便看看" --no-llm                       # 只排盘，不调模型
```

## 配置模型

`openai` SDK 走 OpenAI 兼容协议，三家任选其一，改 `.env` 即可。**模型 id 各家变动频繁，以自家控制台文档为准。**

| 提供方 | `LLM_BASE_URL` | `LLM_MODEL` 示例 |
|---|---|---|
| DeepSeek（默认） | `https://api.deepseek.com` | `deepseek-chat` |
| 智谱 | `https://open.bigmodel.cn/api/paas/v4` | `glm-4.5` 等 |
| 通义 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` 等 |

知识库全文（约 8k 字）一次性进 system prompt，不做检索 —— 比检索更忠实于「唯一事实来源」。DeepSeek 侧会自动命中前缀缓存。

未配置 `LLM_API_KEY` 时，网页与命令行都只出排盘：事项退回「自身」，解读区提示未配置。

## 历法上的两点约定

- **晚子时（23:00–23:59）日柱归属**：`DAY_BOUNDARY_SECT=2`（默认）日柱算当天，与通行万年历一致；`=1` 则算次日。此设定影响日柱，进而影响六神起法与旬空。时柱始终由所选日柱经五鼠遁推出，保证日时自洽。
- **梅花时间起卦**用**农历**月日（古法），非公历。
- **变卦六亲**以变卦自身之宫为准（`app/core/paipan.py` 的 `BIAN_GUA_OWN_GONG`，多数排盘软件的做法）；置 `False` 则沿用本卦之宫。

## 测试

```bash
python -m pytest -q
```

- `test_constants.py` —— 64 卦表完备性、纳甲阴阳顺逆、八宫覆盖、五鼠遁、五行关系
- `test_calendar.py` —— 与 `cnlunar` 独立对拍 365 天；立春 / 节气 / 晚子时三处边界单列用例；旬空
- `test_cast.py` / `test_paipan.py` / `test_pipeline.py` —— 起卦确定性、纳甲世应六亲六神全表、用神、体用

历法用例的期望值取自第三方万年历，**不用 `lunar-python` 自身的输出当预期**，避免循环论证。与 `cnlunar` 的分歧已逐条核对，均为流派差异（本程序按节气**时刻**换月柱、按立春换年柱，合于六爻/八字惯例）。

## 目录结构

```
app/
├── main.py          FastAPI 路由（/api/meta、/api/divine、/api/interpret 流式 SSE）+ 挂载 static
├── pipeline.py      build_result()：N2–N6 串联，纯函数
├── config.py        pydantic-settings 读 .env
├── cli.py           命令行入口
├── core/            确定性内核，不 import llm
│   ├── constants.py 天干地支/八卦/64卦/八宫/纳甲/六神/用神 静态表
│   ├── models.py    Line / Gua / CalendarInfo / DivinationResult
│   ├── calendar.py  N3 历法
│   ├── cast.py      N4 起卦
│   ├── paipan.py    N5 排盘
│   └── yongshen.py  N6 用神
├── llm/
│   ├── client.py    N1 归类、N7 流式解卦
│   └── prompts.py   知识库装载 + 提示词
└── api/schemas.py   请求/响应模型
static/              index.html / style.css / app.js（原生，无构建步骤）
data/knowledge_base.md   知识库（唯一事实来源）
tests/
```

## 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/meta` | 起卦方式、事项枚举、模型是否就绪 |
| POST | `/api/divine` | 起卦排盘，返回结构化结果 |
| POST | `/api/interpret` | SSE 流式解读；事件为 `{"text"}` / `{"notice"}` / `{"error"}`，以 `data: [DONE]` 结束 |

`/api/divine` 的六爻结果带 `raw.throws`（六次掷数），前端解读时回传，可复现同一卦而不重新摇。
