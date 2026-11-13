# WITCH BOLT TV — Google TV Starter App

A one-channel fictional cable station you can install on **Chromecast with Google TV**. This project is **Android Studio source code**, not a compiled APK.

## What the first version does

- Shows its own **Witch Bolt TV** icon on Google TV.
- Starts on **one channel: WBTV 01**.
- Includes two original 15-second test broadcasts so it can run **before any cloud storage is configured**.
- Uses the real clock to pick what's on air and jump to the correct point in the video after reopening the app.
- Plays MP4s using Android's built-in video player.
- Uses the TV remote. OK shows the guide; OK again opens the playlist address dialog; BACK hides the guide; MENU opens settings.
- Saves the address of a cloud playlist on the TV so you don't need your laptop running.

## Step 1A — Build online without installing Android Studio (recommended if laptop space is limited)

This project includes `.github/workflows/build-apk.yml`. GitHub Actions can build the APK **on a cloud computer**, so you do not need to install the Android SDK or leave your computer running.

1. Create a GitHub repository for the source (a private repo is fine). Unzip this archive, then upload the **contents** of the `WitchBoltTV_GoogleTV` folder to the repository. **Keep the `.github` folder**: it contains the build instructions.
2. Open your repo's **Actions** tab. Find **Build Witch Bolt TV APK** and click **Run workflow** (or commit the source to the `main` branch to start an automatic build).
3. When the build finishes successfully, open its run and download the **witch-bolt-tv-apk** artifact.
4. Unzip that artifact to get `app-debug.apk`. This is the file to install on your Google TV.

**Important:** This workflow has not been run in this environment. If GitHub reports a build error, the run log will show where it failed. You don't need to pay for an app store listing or download Android Studio to try this route (GitHub's usage limits depend on your plan).

## Step 1B — Build locally with Android Studio (alternative)

1. Install **Android Studio** from https://developer.android.com/studio on your computer.
2. Unzip this project and use **File → Open** to choose the `WitchBoltTV_GoogleTV` folder.
3. Allow Android Studio to download the required Android SDK and Gradle build tools. The project uses Android Gradle Plugin 8.9.2, Gradle 8.11.1, SDK 35, and Java 17.
4. If Android Studio asks you to generate Gradle wrapper files, use the included version (`8.11.1`). This source archive does not contain the generated wrapper JAR (a generated build-tool file), so you may need to set up or generate the wrapper using Android Studio/Gradle.
5. Choose **Build → Build Bundle(s) / APK(s) → Build APK(s)**. The output is `app/build/outputs/apk/debug/app-debug.apk`.

*I couldn't compile or test an APK in the file-generation environment, because the Android SDK / Gradle tooling isn't installed here. This is a complete starter project to compile in Android Studio, not a tested release binary.*

## Step 2 — Install on your Chromecast (one time)

1. Find your Chromecast remote. If missing, the **Google TV remote** in the Google TV / Google Home app may be usable depending on your setup.
2. On the Chromecast, open **Settings → System → About**, and click **Android TV OS build** repeatedly until Developer Options are enabled.
3. If your device shows **Wireless debugging** under Developer options, turn it on. Make sure the TV and computer are on the same Wi-Fi network.
4. In Android Studio, pair/connect the TV via **Device Manager → Pair Devices Using Wi-Fi** (the exact method depends on your Chromecast's Android TV version), then run the app on the TV. Alternately, install the compiled APK with Android Debug Bridge if your device supports network ADB.
5. Find **Witch Bolt TV** in your Google TV app list. Launch it and watch the demo station.

You do **not** need to publish the app in Google Play, purchase a developer account, or keep your laptop turned on. If you have an APK but no Android Studio, another installation method is the **Downloader by AFTVnews** app on your Google TV, which can open a downloadable APK from a URL after you enable app installation from that source.

## Step 3 — Replace the demos with your real programs

You need public HTTPS **direct video file** links (not a YouTube or Google Drive watch page). H.264/AAC MP4 is the safest starting format.

1. Upload your own MP4 videos to Cloudflare R2 or another host that lets the TV fetch them over HTTPS. Cloudflare R2's public development URL is for testing and is rate limited; a custom domain is recommended for routine use.
2. Copy `app/src/main/assets/channel.example.json`, replace the example URL and timing values, and save it as `channel.json`.
3. Upload `channel.json` to the same host and copy its public HTTPS URL.
4. On your Chromecast, launch Witch Bolt TV, press OK twice, and enter the `channel.json` URL in the settings box.
5. Choose **Load channel**. Your new schedule loads. Next time you open Witch Bolt TV, it remembers your playlist URL. To change programming later, update `channel.json` on your host. Restart the app to reload it.

**Important:** A public R2 URL makes the file reachable by anyone who has the link. Do not use public cloud links for content you want to keep confidential. Private video access can be added in a later version.

### Example `channel.json`

```json
{
  "station": "WITCH BOLT TV",
  "programs": [
    {
      "title": "The Midnight Feature",
      "description": "A Witch Bolt original",
      "duration_seconds": 1800,
      "url": "https://videos.example.com/midnight.mp4"
    },
    {
      "title": "Station ID",
      "description": "Thirty-second ident",
      "duration_seconds": 30,
      "url": "https://videos.example.com/ident.mp4"
    }
  ]
}
```

Set `duration_seconds` to the real video length, rounded to seconds, or playback may skip/cut off. You can read it from your computer using `ffprobe` or from your video editor's export details.

## A few limitations

- Video storage isn't included; demos are bundled in the APK.
- This is a **personal, experimental app**; not yet a commercial release or tested across devices.
- Remote URLs are expected to be **direct HTTPS MP4 URLs**. DRM, protected HLS, and subscriber-only content are not implemented.
- The playlist schedules the videos back-to-back and loops indefinitely, not by named clock slots. It starts at the correct point calculated from UTC epoch time, which stays consistent across restarts and devices.
- The app has no background broadcasting or home server. It only plays when opened, and calculates the correct place in the schedule.
- Remote video compatibility depends on the exact encoding and server behavior.

## Project files

- `app/src/main/java/tv/witchbolt/channel/MainActivity.java` — one-channel UI, playback, scheduler, and remote controls
- `app/src/main/res/raw/` — two original 15-second test broadcasts
- `app/src/main/res/drawable/` — Witch Bolt TV icon and launcher banner
- `app/src/main/assets/channel.example.json` — template playlist
- `app/src/main/AndroidManifest.xml` — TV launcher / internet support
- `.github/workflows/build-apk.yml` — optional cloud build so Android Studio is not required
