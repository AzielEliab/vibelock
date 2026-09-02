# VibeLock — iPhone & Android

Local-first Flutter client for VibeLock. Record from the microphone,
score with time-domain energy and zero-crossing heuristics, show a
score and reason-code placeholders.

**Audio authenticity advisory, not courtroom proof.** Dual-channel vibration
lives on the desktop package. Offline. No analytics. No STT.

Application id: `com.azieeliab.vibelock`

## Open in Android Studio / Xcode

The `android/` and `ios/` folders here are skeleton READMEs because
this tree was written without the Flutter SDK on PATH.

```bash
cd mobile
flutter create --org com.azieeliab --project-name vibelock .
# add RECORD_AUDIO / microphone usage (see android/README.md and ios/README.md)
flutter pub get
flutter run
```

Then open `android/` in Android Studio, or `ios/Runner.xcworkspace` in
Xcode.

## Desktop package (counted download)

This phone app does not replace the desktop package.

# → https://vibelock-download-tracker.vibelock.workers.dev/ ←

GitHub: https://github.com/AzielEliab/vibelock

**Forks are welcome and always allowed.**


## 0.2.0

Giant **Add file** (WAV) and **Export JSON report** (hashes, scores, limitation).
Simple / Advanced views. Kid-plain consistent / inconsistent.
