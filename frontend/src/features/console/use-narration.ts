"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * The microphone, for the half of a demonstration that is not on screen.
 *
 * Clicks say what was done; narration says why — which branch the operator was
 * checking for, when they would stop and ask someone. That reasoning is not
 * recoverable from the network trace afterwards, so it is recorded while it is
 * being said or not at all.
 *
 * Opt-in per session, and never started for the operator: a microphone that
 * turns itself on in a warehouse is a different product.
 */
export type Narration = {
  recording: boolean;
  level: number;
  error: string | null;
  start: () => Promise<void>;
  /** Stops and hands back what was captured, with when it started. */
  stop: () => Promise<{ audio: Blob; startedAt: Date } | null>;
};

export function useNarration(): Narration {
  const [recording, setRecording] = useState(false);
  const [level, setLevel] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const recorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const startedAt = useRef<Date | null>(null);
  const meter = useRef<{ context: AudioContext; frame: number } | null>(null);

  const teardown = useCallback(() => {
    meter.current?.context.close().catch(() => {});
    if (meter.current) cancelAnimationFrame(meter.current.frame);
    meter.current = null;
    recorder.current?.stream.getTracks().forEach((track) => track.stop());
  }, []);

  useEffect(() => teardown, [teardown]);

  const start = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunks.current = [];
      const media = new MediaRecorder(stream);
      media.ondataavailable = (event) => {
        if (event.data.size > 0) chunks.current.push(event.data);
      };
      media.start(1000);
      recorder.current = media;
      startedAt.current = new Date();
      setRecording(true);

      // A level meter is not decoration. A muted or unplugged microphone looks
      // exactly like a working one, and the operator only finds out after the
      // demonstration they cannot repeat.
      const context = new AudioContext();
      const source = context.createMediaStreamSource(stream);
      const analyser = context.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      const samples = new Uint8Array(analyser.frequencyBinCount);
      const tick = () => {
        analyser.getByteTimeDomainData(samples);
        const peak = samples.reduce((worst, value) => Math.max(worst, Math.abs(value - 128)), 0);
        setLevel(Math.min(1, peak / 64));
        if (meter.current) meter.current.frame = requestAnimationFrame(tick);
      };
      meter.current = { context, frame: requestAnimationFrame(tick) };
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
      setRecording(false);
    }
  }, []);

  const stop = useCallback(async () => {
    const media = recorder.current;
    const began = startedAt.current;
    if (!media || !began) return null;

    const finished = new Promise<Blob>((resolve) => {
      media.onstop = () => resolve(new Blob(chunks.current, { type: media.mimeType }));
    });
    media.stop();
    const audio = await finished;

    teardown();
    recorder.current = null;
    startedAt.current = null;
    setRecording(false);
    setLevel(0);

    return audio.size > 0 ? { audio, startedAt: began } : null;
  }, [teardown]);

  return { recording, level, error, start, stop };
}
