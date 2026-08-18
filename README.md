# Subtitle Maker

Subtitle Maker 是一个 Python 项目，用于将英文视频转换为带中英双语字幕的 MP4 成片，并同时保留可独立下载的 SRT 字幕。

V1 使用 FFmpeg 提取并按 15 分钟切分音频，在 Apple Silicon 上调用本地 `whisper-turbo` 生成带时间戳的英文分段，再调用文本模型逐批翻译为简体中文，最后输出 SRT，并将中文在上、英文在下的字幕压制到视频底部。

> 当前版本面向单机开发和个人使用。任务状态存储在本地文件中，不依赖数据库或消息队列。

## V1 能力

- 通过命令行处理本地视频；
- 通过 HTTP 接口上传视频并异步生成字幕；
- 自动提取单声道音频并切成小片段；
- 默认使用 MLX `whisper-turbo` 在 Apple Silicon 本地生成英文文本和分段时间戳；
- 可通过配置切回 OpenAI `whisper-1`；
- 按上下文批量翻译为简体中文，并校验分段 ID；
- 输出 UTF-8 编码的中英双语 `.srt` 文件；
- 使用 FFmpeg 将双语字幕压制进视频并输出兼容性良好的 `.mp4` 成片；
- 将任务状态和中间文件隔离在独立任务目录中。

V1 的完整设计和实施顺序见 [docs/V1_EXECUTION_PLAN.md](docs/V1_EXECUTION_PLAN.md)。

## Web 界面

启动开发服务器后，访问 <http://127.0.0.1:8000/> 即可使用网页上传视频。页面会显示上传、识别、翻译与视频压制状态；任务完成后可下载带双语字幕的 MP4 成片，也可另存 SRT 字幕。

```bash
uvicorn subtitle_maker.api.app:app --reload
```

网页和 HTTP API 使用同一个 FastAPI 进程，不需要单独启动前端服务。

## 项目结构

项目采用 `src` layout。可复用代码全部放在 `subtitle_maker` Python 包中；测试、文档和运行数据与源码分离。

```text
subtitle-making/
├── docs/
│   └── V1_EXECUTION_PLAN.md       # V1 范围、里程碑和验收标准
├── src/
│   └── subtitle_maker/
│       ├── api/                    # HTTP 路由与响应模型
│       ├── domain/                 # 领域模型和抽象接口
│       ├── jobs/                   # 后台任务执行与本地持久化
│       ├── media/                  # FFmpeg 音频处理
│       ├── pipeline/               # 业务流程编排
│       ├── subtitles/              # SRT 等字幕格式输出
│       ├── transcription/          # ASR 服务适配器
│       ├── translation/            # 翻译服务适配器
│       ├── web/                    # Web 界面与静态资源
│       ├── bootstrap.py            # 依赖装配
│       ├── cli.py                  # 命令行入口
│       └── config.py               # 环境配置
├── tests/
│   └── unit/                       # 不访问网络的单元测试
├── .env.example
├── pyproject.toml                  # 依赖、打包和工具配置
└── README.md
```

这种组织方式有三个目的：

1. API 和 CLI 共享同一个 `SubtitlePipeline`，避免出现两套字幕逻辑；
2. OpenAI、FFmpeg 和文件系统都位于边界包中，核心流程可以用假实现做测试；
3. 未来新增其他 ASR 后端、WebVTT、数据库或队列时，可以替换适配器，而不用重写整个项目。

请不要把新的 `.py` 文件随意堆在项目根目录。新增能力时按职责放入已有包；只有形成独立业务边界时才新建包。

## 环境要求

- Apple Silicon Mac（本地 MLX 转写）或 Linux（使用 OpenAI 转写后端）；
- Python 3.11 及以上版本；
- FFmpeg（同时提供 `ffmpeg` 和 `ffprobe`）；
- OpenAI API Key（用于英译中；本地语音识别本身不消耗 API 额度）。

视频压制需要 FFmpeg 的 `libass/subtitles` 过滤器。在 macOS 安装完整版本：

```bash
brew install ffmpeg-full
```

程序会自动识别 Homebrew 的 `ffmpeg-full` 安装位置；Linux 用户请确认发行版的 FFmpeg 构建包含 `subtitles` 过滤器。

## 安装

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev,local]"
cp .env.example .env
```

编辑 `.env`，填写 API Key：

```dotenv
OPENAI_API_KEY=your_api_key_here
```

不要将 `.env` 或 API Key 提交到版本库。

首次处理视频时，程序会从 Hugging Face 下载 `mlx-community/whisper-turbo` 权重；完成后模型会保存在本机缓存中，后续转写可以离线运行。默认的 15 分钟音频分片适合 20–50 分钟电视剧，可避免单次加载过长音轨。

## 命令行使用

```bash
subtitle-maker create /path/to/episode.mp4
```

默认在视频旁边生成 `episode.bilingual.srt`。也可以指定输出路径：

```bash
subtitle-maker create /path/to/episode.mp4 --output /path/to/episode.srt
```

也可以不安装命令行脚本，直接执行包：

```bash
python -m subtitle_maker create /path/to/episode.mp4
```

## HTTP API 使用

启动开发服务器：

```bash
uvicorn subtitle_maker.api.app:app --reload
```

上传视频：

```bash
curl -X POST http://127.0.0.1:8000/v1/jobs \
  -F "video=@/path/to/episode.mp4"
```

接口会返回任务 ID 和 `status_url`。查询进度：

```bash
curl http://127.0.0.1:8000/v1/jobs/<job-id>
```

任务状态为 `succeeded` 后下载字幕：

```bash
curl -OJ http://127.0.0.1:8000/v1/jobs/<job-id>/subtitles
```

下载已经压制双语字幕的视频：

```bash
curl -OJ http://127.0.0.1:8000/v1/jobs/<job-id>/video
```

交互式接口文档位于 <http://127.0.0.1:8000/docs>。

## 配置

| 环境变量 | 默认值 | 说明 |
|---|---:|---|
| `OPENAI_API_KEY` | 无 | 必填；用于字幕英译中 |
| `SUBTITLE_TRANSCRIPTION_BACKEND` | `mlx` | 转写后端；Apple Silicon 使用 `mlx`，也可设为 `openai` |
| `LOCAL_WHISPER_MODEL` | `mlx-community/whisper-turbo` | 本地 MLX Whisper 模型 |
| `SUBTITLE_TRANSCRIPTION_LANGUAGE` | `en` | 原始音轨语言；当前项目默认处理英语电视剧 |
| `OPENAI_TRANSCRIPTION_MODEL` | `whisper-1` | ASR 模型 |
| `OPENAI_TRANSLATION_MODEL` | `gpt-5.4-mini` | 英译中模型，可按账号权限替换 |
| `SUBTITLE_DATA_DIR` | `var` | 上传文件、任务状态和结果目录 |
| `SUBTITLE_AUDIO_CHUNK_SECONDS` | `900` | 音频分片秒数 |
| `SUBTITLE_TRANSLATION_BATCH_SIZE` | `30` | 每批翻译的字幕段数 |
| `SUBTITLE_CHINESE_FONT` | macOS: `Hiragino Sans GB`；Linux: `Noto Sans CJK SC` | 中文硬字幕字体，可按系统已安装字体覆盖；旧的 `SUBTITLE_FONT` 仍兼容 |
| `SUBTITLE_ENGLISH_FONT` | `Roboto` | 英文硬字幕字体，固定使用 weight 400 |

本地 MLX 和 `whisper-1` 都接收音频而不是原始视频，因此本项目先使用 FFmpeg 提取音轨。MLX Whisper 的安装和模型使用方式见 [Apple MLX Whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper)；OpenAI 后端说明见 [Whisper 文档](https://developers.openai.com/api/docs/models/whisper-1)。

## 开发检查

```bash
pytest
# 无 pytest 时也可运行标准库测试：
python -m unittest discover -s tests -p "test_*.py"
ruff check .
mypy src
```

单元测试不会访问 OpenAI，也不需要真实视频。端到端测试需要 FFmpeg、API Key 和测试媒体文件，因此不包含在默认测试命令中。

## V1 限制

- 后台任务依赖当前 API 进程，服务重启不会自动恢复运行中的任务；
- 任务存储仅适合单进程，不适合多实例部署；
- 尚未实现用户系统、配额、上传大小限制和自动清理；
- 字幕分段沿用 Whisper 的 segment，尚未按阅读速度二次切分；
- 尚未提供人工校对界面、说话人标签和字幕样式自定义。

这些能力属于 V2 或后续版本，详见执行方案。
