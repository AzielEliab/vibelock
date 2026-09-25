# VibeLock — iPhone & Android

Record a short clip and see whether it looks physically consistent with a real voice.

**Author:** Aziel Eliab

## Start

1. `cd mobile && flutter create --org com.azieeliab --project-name vibelock .`
2. `flutter pub get`
3. `flutter run`, then tap **Record**.

The phone scores time-domain energy and zero-crossings. Desktop `vibelock ui` is the full check (audio, photo, and short clip). Application id: `com.azieeliab.vibelock`

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


## Notes

The phone result is a media authenticity advisory. The About panel states the courtroom limitation. Dual-channel vibration and image or video checks live on the desktop package. Offline. No analytics. No STT.

## 0.3.0

Desktop engine: physics + A/V deepfake detection (PNG/PPM/VLVD + WAV).
**Add file** is the primary action. **Sample photo**, **Sample deepfake**, and **Export JSON report** are under **Advanced**.
The simple result is one sentence and a score: consistent or inconsistent.
