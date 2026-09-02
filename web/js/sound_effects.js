/**
 * sound_effects.js
 * Synthesizes futuristic cyber-security audio effects using browser Web Audio API.
 * No external MP3 downloads required!
 */

const SoundFX = (() => {
  let audioCtx = null;
  let isMuted = false;

  function initAudio() {
    if (!audioCtx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (AudioContext) {
        audioCtx = new AudioContext();
      }
    }
  }

  // Play high-priority critical threat alarm
  function playThreatAlert() {
    if (isMuted) return;
    try {
      initAudio();
      if (!audioCtx) return;

      const osc1 = audioCtx.createOscillator();
      const osc2 = audioCtx.createOscillator();
      const gainNode = audioCtx.createGain();

      osc1.type = 'sawtooth';
      osc2.type = 'sine';

      const now = audioCtx.currentTime;

      // Pitch sweep
      osc1.frequency.setValueAtTime(880, now);
      osc1.frequency.exponentialRampToValueAtTime(440, now + 0.35);

      osc2.frequency.setValueAtTime(1200, now);
      osc2.frequency.exponentialRampToValueAtTime(600, now + 0.35);

      gainNode.gain.setValueAtTime(0.18, now);
      gainNode.gain.exponentialRampToValueAtTime(0.01, now + 0.35);

      osc1.connect(gainNode);
      osc2.connect(gainNode);
      gainNode.connect(audioCtx.destination);

      osc1.start(now);
      osc2.start(now);
      osc1.stop(now + 0.35);
      osc2.stop(now + 0.35);
    } catch (e) {
      console.warn('[SoundFX] Audio playback not allowed without user gesture');
    }
  }

  // Subtle clean tick for incoming safe trades
  function playTick() {
    if (isMuted) return;
    try {
      initAudio();
      if (!audioCtx) return;

      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      const now = audioCtx.currentTime;

      osc.type = 'sine';
      osc.frequency.setValueAtTime(1400, now);
      gain.gain.setValueAtTime(0.02, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.04);

      osc.connect(gain);
      gain.connect(audioCtx.destination);

      osc.start(now);
      osc.stop(now + 0.04);
    } catch (e) {}
  }

  return {
    threatAlert: playThreatAlert,
    tick: playTick,
    toggleMute: () => { isMuted = !isMuted; return isMuted; },
    isMuted: () => isMuted
  };
})();
