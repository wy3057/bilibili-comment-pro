# AI Reply

## Overview

The platform now supports AI-assisted reply suggestion generation inside the unified ops inbox.
Generated text is only a suggestion draft. The operator still reviews and sends replies manually.

Implementation style:

- official OpenAI Python SDK
- configurable `base_url`
- provider presets for multiple OpenAI-compatible vendors

## Supported Providers

### OpenAI

```bash
AI_REPLY_ENABLED=true
AI_REPLY_PROVIDER=openai
AI_REPLY_API_KEY=your-openai-key
AI_REPLY_MODEL=gpt-4.1-mini
AI_REPLY_API_MODE=chat_completions
```

Default base URL:

- `https://api.openai.com/v1`

### Alibaba Qwen / Bailian

```bash
AI_REPLY_ENABLED=true
AI_REPLY_PROVIDER=qwen
AI_REPLY_API_KEY=your-dashscope-key
AI_REPLY_MODEL=qwen-plus
AI_REPLY_API_MODE=chat_completions
```

Default base URL:

- `https://dashscope.aliyuncs.com/compatible-mode/v1`

### Volcengine Ark

```bash
AI_REPLY_ENABLED=true
AI_REPLY_PROVIDER=volcengine
AI_REPLY_API_KEY=your-ark-key
AI_REPLY_MODEL=your-endpoint-id
AI_REPLY_API_MODE=chat_completions
```

Default base URL:

- `https://ark.cn-beijing.volces.com/api/v3`

### DeepSeek

```bash
AI_REPLY_ENABLED=true
AI_REPLY_PROVIDER=deepseek
AI_REPLY_API_KEY=your-deepseek-key
AI_REPLY_MODEL=deepseek-chat
AI_REPLY_API_MODE=chat_completions
```

Default base URL:

- `https://api.deepseek.com`

## Optional Overrides

You can override the preset base URL manually:

```bash
AI_REPLY_BASE_URL=https://your-openai-compatible-gateway/v1
```

Other tuning options:

```bash
AI_REPLY_TEMPERATURE=0.7
AI_REPLY_MAX_TOKENS=300
AI_REPLY_TIMEOUT_SECONDS=30
```

## Current Product Behavior

- available in unified ops inbox comment drawer
- operator can add extra instruction before generation
- generated text is inserted into the reply form
- Bilibili comments can still be saved as drafts after generation
- Douyin comments currently use AI suggestion only, without draft persistence
