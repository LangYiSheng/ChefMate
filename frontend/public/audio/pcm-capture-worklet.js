class PcmCaptureWorklet extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0]
    const channel = input?.[0]
    if (channel?.length) {
      const buffer = new Float32Array(channel.length)
      buffer.set(channel)
      this.port.postMessage(buffer.buffer, [buffer.buffer])
    }
    return true
  }
}

registerProcessor('pcm-capture-worklet', PcmCaptureWorklet)
