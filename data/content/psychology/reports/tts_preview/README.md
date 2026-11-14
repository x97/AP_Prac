# Kokoro 发音试听

- 术语：30 个高频 AP Psychology 概念，来自 `concept_clusters` 权重排序。
- 引擎：Kokoro-82M ONNX（`kokoro-onnx`）。
- 默认音色：`af_heart`，语速 0.9。
- 文件：`index.html`、`manifest.json`、`*.wav`。
- 音色对比：`Operant conditioning` 的 `af_heart` / `af_bella` / `am_michael` / `bf_emma`。

这是试听样片。正式上线建议：

1. 官方术语批量预生成音频，按术语哈希缓存。
2. 输出 MP3 48–64 kbps 单声道，减少流量。
3. 自定义卡片按需生成，服务端缓存，不把用户内容发给第三方 TTS。
4. Web 和小程序共用同一套音频 URL。

重新生成：

```bash
python3 _tools/kokoro_tts_preview.py \
  --model /tmp/kokoro_models/kokoro-v1.0.onnx \
  --voices /tmp/kokoro_models/voices-v1.0.bin
```
