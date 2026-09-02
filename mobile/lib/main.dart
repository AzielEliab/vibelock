import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:file_picker/file_picker.dart';
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
  bool _advanced = false;
  String? _status;
  String? _exportPath;
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

  HeuristicResult _scoreBytes(Uint8List bytes, String filename) {
    const maxBytes = 12 * 1024 * 1024;
    if (bytes.length > maxBytes) {
      throw StateError('That file is too big. Please use a smaller recording.');
    }
    if (bytes.isEmpty) {
      throw StateError('That file is empty. Please add a real audio file.');
    }
    final isPng = bytes.length >= 8 &&
        bytes[0] == 0x89 &&
        bytes[1] == 0x50 &&
        bytes[2] == 0x4e &&
        bytes[3] == 0x47;
    final isRiff = bytes.length >= 12 &&
        bytes[0] == 0x52 &&
        bytes[1] == 0x49 &&
        bytes[2] == 0x46 &&
        bytes[3] == 0x46;
    if (isPng || (!isRiff && !filename.toLowerCase().endsWith('.wav'))) {
      throw StateError('That file is not audio. Please add a WAV file.');
    }
    if (isRiff && bytes.length < 44) {
      throw StateError(
          'That audio file looks broken or cut off. Try another file.');
    }
    final digest = sha256.convert(bytes).toString();
    final pcm = stripWavHeader(bytes);
    final samples = pcm16leToFloat(pcm);
    return scoreSamples(samples, sha256: digest, filename: filename);
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
      final result = _scoreBytes(bytes, 'recording.wav');
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

  Future<void> _addFile() async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _status = 'Add file…';
    });
    try {
      final picked = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: const ['wav'],
        withData: true,
      );
      if (picked == null || picked.files.isEmpty) {
        setState(() {
          _busy = false;
          _status = 'No file added.';
        });
        return;
      }
      final file = picked.files.single;
      final bytes = file.bytes ??
          (file.path != null
              ? Uint8List.fromList(await File(file.path!).readAsBytes())
              : null);
      if (bytes == null) {
        setState(() {
          _busy = false;
          _status = 'Could not read that file.';
        });
        return;
      }
      final result = _scoreBytes(bytes, file.name);
      setState(() {
        _busy = false;
        _result = result;
        _status = 'Local score ready. Nothing was uploaded.';
      });
    } catch (e) {
      setState(() {
        _busy = false;
        _status = '$e';
      });
    }
  }

  Future<void> _export() async {
    final result = _result;
    if (result == null) {
      setState(() => _status = 'Add a file first, then export.');
      return;
    }
    try {
      final dir = await getApplicationDocumentsDirectory();
      final path = '${dir.path}/vibelock-report.json';
      const encoder = JsonEncoder.withIndent('  ');
      await File(path).writeAsString(encoder.convert(result.toReport()));
      setState(() {
        _exportPath = path;
        _status = 'Exported JSON report to $path';
      });
    } catch (e) {
      setState(() => _status = 'Export failed: $e');
    }
  }

  void _demo() {
    final result = scoreSamples(
      syntheticSpeechish(),
      filename: 'sample-tone.wav',
    );
    setState(() {
      _result = result;
      _status = 'Demo waveform (synthetic). $kLimitation';
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
          const Text(kLimitation),
          const SizedBox(height: 20),
          SizedBox(
            height: 88,
            child: FilledButton(
              onPressed: _busy ? null : _addFile,
              child: const Text('Add file', style: TextStyle(fontSize: 28)),
            ),
          ),
          const SizedBox(height: 8),
          FilledButton.icon(
            onPressed: _busy ? null : _tap,
            icon: const Icon(Icons.mic),
            label: const Text('Record / Stop'),
          ),
          const SizedBox(height: 8),
          OutlinedButton(
            onPressed: _busy ? null : _demo,
            child: const Text('Sample tone (no mic)'),
          ),
          const SizedBox(height: 8),
          OutlinedButton(
            onPressed: _result == null ? null : _export,
            child: const Text('Export JSON report'),
          ),
          const SizedBox(height: 16),
          SegmentedButton<bool>(
            segments: const [
              ButtonSegment(value: false, label: Text('Simple')),
              ButtonSegment(value: true, label: Text('Advanced')),
            ],
            selected: {_advanced},
            onSelectionChanged: (s) => setState(() => _advanced = s.first),
          ),
          if (_status != null) ...[
            const SizedBox(height: 16),
            Text(_status!),
          ],
          if (_exportPath != null) ...[
            const SizedBox(height: 8),
            Text('Report: $_exportPath',
                style: Theme.of(context).textTheme.bodySmall),
          ],
          if (_result != null) ...[
            const SizedBox(height: 24),
            _ScoreCard(result: _result!, advanced: _advanced),
          ],
        ],
      ),
    );
  }
}

class _ScoreCard extends StatelessWidget {
  const _ScoreCard({required this.result, required this.advanced});
  final HeuristicResult result;
  final bool advanced;

  @override
  Widget build(BuildContext context) {
    final codes = result.reasonCodes.isEmpty
        ? 'none (placeholder — not courtroom proof)'
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
            Text(
              result.plainSentence,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            LinearProgressIndicator(value: result.score),
            const SizedBox(height: 12),
            const Text(kLimitation),
            if (advanced) ...[
              const SizedBox(height: 12),
              Text('RMS energy: ${result.rms.toStringAsFixed(4)}'),
              Text('Zero-crossing rate: ${result.zcr.toStringAsFixed(4)}'),
              if (result.sha256.isNotEmpty) Text('SHA-256: ${result.sha256}'),
              const SizedBox(height: 8),
              Text('Reason codes: $codes'),
              const SizedBox(height: 8),
              Text(result.note, style: Theme.of(context).textTheme.bodySmall),
            ],
          ],
        ),
      ),
    );
  }
}
