import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';

import 'heuristics.dart';
import 'theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const VibeLockApp());
}

class VibeLockApp extends StatelessWidget {
  const VibeLockApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'VibeLock',
      debugShowCheckedModeBanner: false,
      theme: buildAppTheme(),
      home: const RecordPage(),
    );
  }
}

class RecordPage extends StatefulWidget {
  const RecordPage({super.key});

  @override
  State<RecordPage> createState() => _RecordPageState();
}

class _RecordPageState extends State<RecordPage> {
  final AudioRecorder _rec = AudioRecorder();
  bool _busy = false;
  String? _status;
  HeuristicResult? _result;

  @override
  void dispose() {
    _rec.dispose();
    super.dispose();
  }

  Future<void> _tap() async {
    if (_busy) return;
    final recording = await _rec.isRecording();
    if (recording) {
      await _stop();
    } else {
      await _start();
    }
  }

  Future<void> _start() async {
    setState(() {
      _busy = true;
      _status = 'Requesting microphone…';
      _result = null;
    });
    try {
      final ok = await _rec.hasPermission();
      if (!ok) {
        setState(() {
          _busy = false;
          _status = 'Microphone permission denied.';
        });
        return;
      }
      final dir = await getTemporaryDirectory();
      final path = '${dir.path}/vibelock.wav';
      await _rec.start(
        const RecordConfig(
          encoder: AudioEncoder.wav,
          sampleRate: 16000,
          numChannels: 1,
        ),
        path: path,
      );
      setState(() {
        _busy = false;
        _status = 'Recording… tap Stop when done.';
      });
    } catch (e) {
      setState(() {
        _busy = false;
        _status = 'Could not start recorder: $e';
      });
    }
  }

  Future<void> _stop() async {
    setState(() {
      _busy = true;
      _status = 'Scoring…';
    });
    try {
      final path = await _rec.stop();
      if (path == null) {
        setState(() {
          _busy = false;
          _status = 'No file produced.';
        });
        return;
      }
      final bytes = Uint8List.fromList(await File(path).readAsBytes());
      final pcm = stripWavHeader(bytes);
      final samples = pcm16leToFloat(pcm);
      final result = scoreSamples(samples);
      setState(() {
        _busy = false;
        _result = result;
        _status = 'Local score ready. Audio discarded after scoring.';
      });
      try {
        await File(path).delete();
      } catch (_) {}
    } catch (e) {
      setState(() {
        _busy = false;
        _status = 'Score failed: $e';
      });
    }
  }

  void _demo() {
    final result = scoreSamples(syntheticSpeechish());
    setState(() {
      _result = result;
      _status =
          'Demo waveform (synthetic). Risk assessment, not a liveness proof.';
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('VibeLock')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            'Sound can be forged. Physics is harder to fake.',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: kGold,
                ),
          ),
          const SizedBox(height: 8),
          const Text(
            'Audio-only energy / zero-crossing heuristics. This is a '
            'risk assessment, not a proof of liveness. Nothing is uploaded.',
          ),
          const SizedBox(height: 20),
          FilledButton.icon(
            onPressed: _busy ? null : _tap,
            icon: const Icon(Icons.mic),
            label: const Text('Record / Stop'),
          ),
          const SizedBox(height: 8),
          OutlinedButton(
            onPressed: _busy ? null : _demo,
            child: const Text('Score synthetic demo (no mic)'),
          ),
          if (_status != null) ...[
            const SizedBox(height: 16),
            Text(_status!),
          ],
          if (_result != null) ...[
            const SizedBox(height: 24),
            _ScoreCard(result: _result!),
          ],
        ],
      ),
    );
  }
}

class _ScoreCard extends StatelessWidget {
  const _ScoreCard({required this.result});
  final HeuristicResult result;

  @override
  Widget build(BuildContext context) {
    final codes = result.reasonCodes.isEmpty
        ? 'none (placeholder — not a liveness proof)'
        : result.reasonCodes.join(', ');
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Score ${result.score.toStringAsFixed(3)}',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    color: kGold,
                  ),
            ),
            const SizedBox(height: 8),
            LinearProgressIndicator(value: result.score),
            const SizedBox(height: 12),
            Text('RMS energy: ${result.rms.toStringAsFixed(4)}'),
            Text('Zero-crossing rate: ${result.zcr.toStringAsFixed(4)}'),
            const SizedBox(height: 8),
            Text('Reason codes: $codes'),
            const SizedBox(height: 8),
            Text(result.note, style: Theme.of(context).textTheme.bodySmall),
          ],
        ),
      ),
    );
  }
}
