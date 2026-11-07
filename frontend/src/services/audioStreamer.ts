/**
 * Real-Time Audio Streaming Manager
 * Handles PCM16 Streaming Queue Playback and Microphone Streaming Capture
 * with Sub-20ms Barge-In Instant Purge and Generation Invalidation.
 */

const WORKLET_PROCESSOR_CODE = `
class PcmCaptureProcessor extends AudioWorkletProcessor {
  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (input && input.length > 0) {
      const channelData = input[0];
      const pcm16 = new Int16Array(channelData.length);
      for (let i = 0; i < channelData.length; i++) {
        const s = Math.max(-1, Math.min(1, channelData[i]));
        pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
      }
      this.port.postMessage(pcm16.buffer, [pcm16.buffer]);
    }
    return true;
  }
}
registerProcessor('pcm-capture-processor', PcmCaptureProcessor);
`;

export class AudioStreamer {
  private playbackContext: AudioContext | null = null;
  private captureContext: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private scriptProcessor: ScriptProcessorNode | null = null;
  private workletNode: AudioWorkletNode | null = null;
  private muteGainNode: GainNode | null = null;
  private activeSourceNodes: AudioBufferSourceNode[] = [];
  private nextPlayTime: number = 0;
  private isPlaying: boolean = false;
  private playbackGenerationId: number = 0;
  private readonly sampleRatePlayback: number = 24000; // Gemini Live & OpenAI Realtime standard
  private readonly sampleRateCapture: number = 16000;

  constructor() {}

  private getPlaybackContext(): AudioContext {
    if (!this.playbackContext || this.playbackContext.state === 'closed') {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      this.playbackContext = new AudioCtx({ sampleRate: this.sampleRatePlayback });
    }
    if (this.playbackContext.state === 'suspended') {
      this.playbackContext.resume();
    }
    return this.playbackContext;
  }

  /**
   * Enqueues an incoming raw PCM16 chunk for gapless real-time playback.
   */
  public enqueuePcmChunk(pcmData: ArrayBuffer | Uint8Array, onPlayEnd?: () => void): void {
    const currentGen = this.playbackGenerationId;
    const ctx = this.getPlaybackContext();
    const bytes = pcmData instanceof Uint8Array ? pcmData : new Uint8Array(pcmData);

    // Convert Int16 bytes to Float32 samples
    const numSamples = Math.floor(bytes.length / 2);
    if (numSamples <= 0) return;

    // Check if generation changed during parsing
    if (currentGen !== this.playbackGenerationId) return;

    const int16Array = new Int16Array(bytes.buffer, bytes.byteOffset, numSamples);
    const float32Array = new Float32Array(numSamples);
    for (let i = 0; i < numSamples; i++) {
      float32Array[i] = int16Array[i] / 32768.0;
    }

    const audioBuffer = ctx.createBuffer(1, numSamples, this.sampleRatePlayback);
    audioBuffer.copyToChannel(float32Array, 0);

    const source = ctx.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(ctx.destination);

    const currentTime = ctx.currentTime;
    if (this.nextPlayTime < currentTime) {
      this.nextPlayTime = currentTime;
    }

    source.start(this.nextPlayTime);
    this.activeSourceNodes.push(source);
    this.isPlaying = true;

    this.nextPlayTime += audioBuffer.duration;

    source.onended = () => {
      const idx = this.activeSourceNodes.indexOf(source);
      if (idx !== -1) {
        this.activeSourceNodes.splice(idx, 1);
      }
      if (this.activeSourceNodes.length === 0) {
        this.isPlaying = false;
        onPlayEnd?.();
      }
    };
  }

  /**
   * BARGE-IN: Instantly purges all playing and queued audio buffers and invalidates generation.
   * Execution time is typically <5ms.
   */
  public instantBargeIn(): number {
    const t0 = performance.now();
    this.playbackGenerationId++;
    for (const node of this.activeSourceNodes) {
      try {
        node.stop();
        node.disconnect();
      } catch {}
    }
    this.activeSourceNodes = [];
    this.nextPlayTime = 0;
    this.isPlaying = false;
    return Math.round((performance.now() - t0) * 10) / 10;
  }

  /**
   * Starts microphone capture and streams PCM16 chunks via callback.
   * Employs AudioWorklet with fallback to ScriptProcessorNode, enforcing AEC, NS, and AGC.
   */
  public async startCapture(onChunk: (pcmChunk: Uint8Array) => void): Promise<void> {
    this.stopCapture();

    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        sampleRate: this.sampleRateCapture,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true
      }
    });
    this.mediaStream = stream;

    const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
    this.captureContext = new AudioCtx({ sampleRate: this.sampleRateCapture });

    const source = this.captureContext.createMediaStreamSource(stream);

    // Attempt modern AudioWorkletNode first for glitch-free background processing
    let workletSuccess = false;
    if (this.captureContext.audioWorklet) {
      try {
        const blob = new Blob([WORKLET_PROCESSOR_CODE], { type: 'application/javascript' });
        const workletUrl = URL.createObjectURL(blob);
        await this.captureContext.audioWorklet.addModule(workletUrl);
        URL.revokeObjectURL(workletUrl);

        const workletNode = new AudioWorkletNode(this.captureContext, 'pcm-capture-processor');
        workletNode.port.onmessage = (event) => {
          onChunk(new Uint8Array(event.data));
        };
        source.connect(workletNode);
        this.workletNode = workletNode;
        workletSuccess = true;
      } catch (err) {
        console.warn('AudioWorklet initialization fallback to ScriptProcessor:', err);
      }
    }

    if (!workletSuccess) {
      // Robust ScriptProcessorNode fallback with 0-gain sink to prevent feedback
      const processor = this.captureContext.createScriptProcessor(2048, 1, 1);
      this.scriptProcessor = processor;

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        const pcm16 = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]));
          pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        onChunk(new Uint8Array(pcm16.buffer));
      };

      const muteGain = this.captureContext.createGain();
      muteGain.gain.value = 0.0;
      this.muteGainNode = muteGain;

      source.connect(processor);
      processor.connect(muteGain);
      muteGain.connect(this.captureContext.destination);
    }
  }

  /**
   * Stops microphone recording and completely frees audio hardware and processing nodes.
   */
  public stopCapture(): void {
    if (this.workletNode) {
      try {
        this.workletNode.disconnect();
      } catch {}
      this.workletNode = null;
    }
    if (this.scriptProcessor) {
      try {
        this.scriptProcessor.disconnect();
      } catch {}
      this.scriptProcessor = null;
    }
    if (this.muteGainNode) {
      try {
        this.muteGainNode.disconnect();
      } catch {}
      this.muteGainNode = null;
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }
    if (this.captureContext && this.captureContext.state !== 'closed') {
      try {
        this.captureContext.close();
      } catch {}
      this.captureContext = null;
    }
  }

  /**
   * Closes all audio contexts and clears all pending buffers.
   */
  public teardown(): void {
    this.instantBargeIn();
    this.stopCapture();
    if (this.playbackContext && this.playbackContext.state !== 'closed') {
      try {
        this.playbackContext.close();
      } catch {}
      this.playbackContext = null;
    }
  }

  public getIsPlaying(): boolean {
    return this.isPlaying;
  }
}

export const globalAudioStreamer = new AudioStreamer();
