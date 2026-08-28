import 'dart:math';
import 'dart:typed_data';

/// Time-domain energy + zero-crossing heuristics.
///
/// This is a **risk assessment, not a liveness proof.** Desktop VibeLock
/// uses numpy/scipy dual-channel and forensic checks. The phone v1 scores
/// a mono PCM clip with RMS energy and ZCR only, then emits placeholder
/// reason codes in the same family as the desktop list.
class HeuristicResult {
  HeuristicResult({
    required this.score,
    required this.reasonCodes,
    required this.rms,
    required this.zcr,
    required this.note,
  });

  final double score;
  final List<String> reasonCodes;
  final double rms;
  final double zcr;
  final String note;
}

double _rms(List<double> x) {
  if (x.isEmpty) return 0;
  var s = 0.0;
  for (final v in x) {
    s += v * v;
  }
  return sqrt(s / x.length);
}

double _zcr(List<double> x) {
  if (x.length < 2) return 0;
  var c = 0;
  for (var i = 1; i < x.length; i++) {
    if ((x[i - 1] >= 0 && x[i] < 0) || (x[i - 1] < 0 && x[i] >= 0)) {
      c++;
    }
  }
  return c / (x.length - 1);
}

/// PCM16 little-endian mono → float in [-1, 1].
List<double> pcm16leToFloat(Uint8List bytes) {
  final n = bytes.length ~/ 2;
  final out = List<double>.filled(n, 0);
  final bd = ByteData.sublistView(bytes);
  for (var i = 0; i < n; i++) {
    out[i] = bd.getInt16(i * 2, Endian.little) / 32768.0;
  }
  return out;
}

/// Strip a RIFF/WAVE header if present; otherwise treat as raw PCM16LE.
Uint8List stripWavHeader(Uint8List bytes) {
  if (bytes.length > 44 &&
      bytes[0] == 0x52 &&
      bytes[1] == 0x49 &&
      bytes[2] == 0x46 &&
      bytes[3] == 0x46) {
    var offset = 12;
    while (offset + 8 < bytes.length) {
      final id = String.fromCharCodes(bytes.sublist(offset, offset + 4));
      final size = ByteData.sublistView(bytes, offset + 4, offset + 8)
          .getUint32(0, Endian.little);
      offset += 8;
      if (id == 'data') {
        final end = min(offset + size, bytes.length);
        return Uint8List.sublistView(bytes, offset, end);
      }
      offset += size;
    }
  }
  return bytes;
}

HeuristicResult scoreSamples(List<double> samples, {int sampleRate = 16000}) {
  final codes = <String>[];
  if (samples.isEmpty) {
    return HeuristicResult(
      score: 0,
      reasonCodes: const ['VIBRATION_UNUSABLE'],
      rms: 0,
      zcr: 0,
      note: 'Empty buffer. Risk assessment only — not a liveness proof.',
    );
  }
  final rms = _rms(samples);
  final zcr = _zcr(samples);
  var score = 0.72;

  // Silence / too-quiet: energy implausible for speech.
  if (rms < 0.01) {
    score -= 0.35;
    codes.add('DECAY_IMPLAUSIBLE');
  } else if (rms > 0.45) {
    score -= 0.12;
    codes.add('SPECTRAL_UNNATURAL');
  }

  // Speech-ish ZCR is typically modest; buzzing / vocoder-like is high.
  if (zcr > 0.28) {
    score -= 0.22;
    codes.add('VOCODER_BUZZ');
  } else if (zcr < 0.02 && rms > 0.05) {
    score -= 0.15;
    codes.add('PHASE_OVERFLAT');
  }

  // Crude splice: large frame-energy jumps.
  const hop = 256;
  if (samples.length > hop * 4) {
    var jumps = 0;
    double? prev;
    for (var i = 0; i + hop <= samples.length; i += hop) {
      final e = _rms(samples.sublist(i, i + hop));
      if (prev != null && (e - prev).abs() > 0.25) jumps++;
      prev = e;
    }
    if (jumps >= 3) {
      score -= 0.18;
      codes.add('TEMPORAL_SPLICE');
    }
  }

  if (samples.length < sampleRate ~/ 4) {
    score -= 0.1;
    codes.add('COHERENCE_UNSTABLE');
  }

  score = score.clamp(0.0, 1.0);
  return HeuristicResult(
    score: score,
    reasonCodes: codes,
    rms: rms,
    zcr: zcr,
    note: 'Audio-only time-domain energy/ZCR. Risk assessment, not a '
        'proof of liveness. Dual-channel vibration is desktop-only.',
  );
}

/// Synthetic demo clip so the UI can be exercised without a mic.
List<double> syntheticSpeechish({int n = 8000, int seed = 3}) {
  final rng = Random(seed);
  final out = List<double>.filled(n, 0);
  for (var i = 0; i < n; i++) {
    final t = i / 16000.0;
    final env = 0.3 + 0.2 * sin(2 * pi * 3 * t);
    out[i] = env *
        (0.4 * sin(2 * pi * 180 * t) +
            0.2 * sin(2 * pi * 320 * t) +
            0.05 * (rng.nextDouble() * 2 - 1));
  }
  return out;
}
