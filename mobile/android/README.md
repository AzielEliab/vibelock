# Android platform folder

This tree was authored without the Flutter SDK on PATH, so the Gradle
project is not generated here.

From the parent `mobile/` directory:

    flutter create --org com.azieeliab --project-name vibelock .

That fills `android/` (and `ios/`) with the platform projects. Keep this
README or replace it; the generated Gradle tree is what Android Studio
opens.

After `flutter create .`, add to `android/app/src/main/AndroidManifest.xml`
inside `<manifest>` (sibling of `<application>`):

    <uses-permission android:name="android.permission.RECORD_AUDIO" />

Then:

    flutter pub get
    flutter run

Or open the generated `android/` folder in Android Studio.
Offline. No analytics. Application id: `com.azieeliab.vibelock`.
