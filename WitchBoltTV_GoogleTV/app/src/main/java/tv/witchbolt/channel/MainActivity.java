package tv.witchbolt.channel;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.InputType;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;
import android.widget.VideoView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** One-channel, clock-synchronized Google TV player. No always-on home computer required. */
public final class MainActivity extends Activity {
    private static final int INK = Color.rgb(235, 236, 222);
    private static final int MUTED = Color.rgb(158, 169, 147);
    private static final int ACID = Color.rgb(199, 221, 142);
    private static final int PANEL = Color.rgb(17, 22, 17);
    private static final int RED = Color.rgb(207, 97, 85);
    private static final String PREFS = "witch_bolt_tv";
    private static final String PLAYLIST_URL_KEY = "playlist_url";

    private static final class Program {
        final String title;
        final String description;
        final String url;
        final int durationSeconds;
        Program(String title, String description, String url, int durationSeconds) {
            this.title = title;
            this.description = description;
            this.url = url;
            this.durationSeconds = durationSeconds;
        }
    }

    private static final class Broadcast {
        final int index;
        final int elapsedSeconds;
        final int totalSeconds;
        Broadcast(int index, int elapsedSeconds, int totalSeconds) {
            this.index = index;
            this.elapsedSeconds = elapsedSeconds;
            this.totalSeconds = totalSeconds;
        }
    }

    private final Handler ui = new Handler(Looper.getMainLooper());
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private List<Program> programs = new ArrayList<>();
    private String station = "WITCH BOLT TV";
    private int activeIndex = -1;
    private boolean guideVisible = false;
    private boolean isLoading = false;
    private boolean hasError = false;
    private VideoView player;
    private FrameLayout root;
    private LinearLayout guide;
    private TextView guideTitle, guideCurrent, guideNext, guideClock, emptyMessage, stationBug;
    private FrameLayout empty;

    private final Runnable heartbeat = new Runnable() {
        @Override public void run() {
            if (!isFinishing() && !isDestroyed()) {
                updateBroadcast(false);
                ui.postDelayed(this, 1000);
            }
        }
    };

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_FULLSCREEN | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION |
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN |
                View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_LAYOUT_STABLE);
        createDemoSchedule();
        createScreen();
        updateBroadcast(true);
        ui.postDelayed(heartbeat, 1000);
        String saved = getPreferences().getString(PLAYLIST_URL_KEY, "");
        if (!saved.isEmpty()) loadPlaylist(saved, false);
        else showGuide(true);
    }

    private SharedPreferences getPreferences() {
        return getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    private void createDemoSchedule() {
        programs.clear();
        programs.add(new Program("Station Identification", "Demo transmission - replace with your videos",
                "android.resource://" + getPackageName() + "/" + R.raw.station_ident, 15));
        programs.add(new Program("Night Signal", "An original test card for Witch Bolt TV",
                "android.resource://" + getPackageName() + "/" + R.raw.night_signal, 15));
    }

    private static GradientDrawable background(int color, int borderColor, float radius) {
        GradientDrawable d = new GradientDrawable();
        d.setColor(color);
        d.setCornerRadius(radius);
        if (borderColor != Color.TRANSPARENT) d.setStroke(1, borderColor);
        return d;
    }

    private TextView text(String value, int sizeSp, int color, boolean bold) {
        TextView tv = new TextView(this);
        tv.setText(value);
        tv.setTextSize(sizeSp);
        tv.setTextColor(color);
        tv.setTypeface(Typeface.create("monospace", bold ? Typeface.BOLD : Typeface.NORMAL));
        tv.setIncludeFontPadding(false);
        return tv;
    }

    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }

    private void createScreen() {
        root = new FrameLayout(this);
        root.setBackgroundColor(Color.BLACK);
        setContentView(root);
        player = new VideoView(this);
        player.setKeepScreenOn(true);
        root.addView(player, new FrameLayout.LayoutParams(-1, -1));

        empty = new FrameLayout(this);
        empty.setBackground(new GradientDrawable(GradientDrawable.Orientation.TL_BR,
                new int[] { Color.rgb(16, 28, 19), Color.rgb(4, 8, 7), Color.rgb(10, 13, 10) }));
        root.addView(empty, new FrameLayout.LayoutParams(-1, -1));
        LinearLayout ident = new LinearLayout(this);
        ident.setOrientation(LinearLayout.VERTICAL);
        ident.setGravity(Gravity.CENTER);
        FrameLayout.LayoutParams identLp = new FrameLayout.LayoutParams(-1, -2, Gravity.CENTER);
        empty.addView(ident, identLp);
        TextView symbol = text("ϟ", 72, ACID, false);
        symbol.setGravity(Gravity.CENTER);
        ident.addView(symbol);
        TextView title = text("WITCH BOLT TV", 38, INK, true);
        title.setGravity(Gravity.CENTER);
        ident.addView(title);
        TextView tagline = text("PRIVATE TRANSMISSION / CHANNEL 01", 16, MUTED, false);
        tagline.setGravity(Gravity.CENTER);
        tagline.setPadding(0, dp(12), 0, dp(23));
        ident.addView(tagline);
        emptyMessage = text("TUNING TO THE SIGNAL…", 15, ACID, false);
        emptyMessage.setGravity(Gravity.CENTER);
        ident.addView(emptyMessage);

        stationBug = text("●  WBTV 01  /  ON AIR", 13, INK, true);
        stationBug.setPadding(dp(18), dp(10), dp(18), dp(10));
        stationBug.setBackground(background(0xBB111812, 0xFF49533C, dp(3)));
        FrameLayout.LayoutParams bugLp = new FrameLayout.LayoutParams(-2, -2, Gravity.TOP | Gravity.LEFT);
        bugLp.setMargins(dp(32), dp(26), 0, 0);
        root.addView(stationBug, bugLp);

        guide = new LinearLayout(this);
        guide.setOrientation(LinearLayout.VERTICAL);
        guide.setPadding(dp(42), dp(24), dp(42), dp(27));
        guide.setBackground(background(0xF5111713, 0xFF4E5C3F, dp(6)));
        FrameLayout.LayoutParams guideLp = new FrameLayout.LayoutParams(-1, -2, Gravity.BOTTOM);
        guideLp.setMargins(dp(28), 0, dp(28), dp(25));
        root.addView(guide, guideLp);

        LinearLayout top = new LinearLayout(this);
        top.setOrientation(LinearLayout.HORIZONTAL);
        top.setGravity(Gravity.CENTER_VERTICAL);
        guide.addView(top, new LinearLayout.LayoutParams(-1, -2));
        guideTitle = text("WBTV 01  •  WITCH BOLT TV", 17, ACID, true);
        top.addView(guideTitle, new LinearLayout.LayoutParams(0, -2, 1f));
        guideClock = text("", 14, MUTED, false);
        top.addView(guideClock);
        guideCurrent = text("NOW  /  STATION IDENTIFICATION", 23, INK, true);
        guideCurrent.setPadding(0, dp(14), 0, dp(4));
        guide.addView(guideCurrent);
        guideNext = text("UP NEXT  /  NIGHT SIGNAL", 15, MUTED, false);
        guide.addView(guideNext);
        TextView hint = text("OK  SET PLAYLIST LINK     •     BACK  HIDE GUIDE     •     MENU  SETTINGS", 12, ACID, false);
        hint.setPadding(0, dp(19), 0, 0);
        guide.addView(hint);
        guide.setVisibility(View.GONE);

        player.setOnPreparedListener(mediaPlayer -> {
            Broadcast b = broadcastAtNow();
            if (b.index == activeIndex) {
                player.seekTo(b.elapsedSeconds * 1000);
                player.start();
                empty.setVisibility(View.GONE);
                hasError = false;
            }
        });
        player.setOnCompletionListener(mediaPlayer -> updateBroadcast(true));
        player.setOnErrorListener((mediaPlayer, what, extra) -> {
            hasError = true;
            empty.setVisibility(View.VISIBLE);
            emptyMessage.setText("CANNOT PLAY VIDEO  /  CHECK URL OR FORMAT");
            showGuide(true);
            return true;
        });
    }

    private Broadcast broadcastAtNow() {
        int total = 0;
        for (Program p : programs) total += p.durationSeconds;
        if (total <= 0) return new Broadcast(0, 0, 1);
        long nowSec = System.currentTimeMillis() / 1000L;
        int elapsed = (int) Math.floorMod(nowSec, (long) total);
        for (int i = 0; i < programs.size(); i++) {
            if (elapsed < programs.get(i).durationSeconds) return new Broadcast(i, elapsed, total);
            elapsed -= programs.get(i).durationSeconds;
        }
        return new Broadcast(0, 0, total);
    }

    private void updateBroadcast(boolean force) {
        if (programs.isEmpty()) return;
        Broadcast b = broadcastAtNow();
        Program p = programs.get(b.index);
        if (force || activeIndex != b.index) {
            activeIndex = b.index;
            hasError = false;
            empty.setVisibility(View.VISIBLE);
            emptyMessage.setText("TUNING  /  " + p.title.toUpperCase(Locale.US));
            player.setVideoURI(Uri.parse(p.url));
        } else if (!hasError && player.isPlaying() && Math.abs(player.getCurrentPosition() - b.elapsedSeconds * 1000L) > 6000L) {
            player.seekTo(b.elapsedSeconds * 1000);
        }
        if (guideVisible) {
            guideTitle.setText("WBTV 01  •  " + station);
            guideCurrent.setText("NOW  /  " + p.title.toUpperCase(Locale.US) + "  [" + formatClock(b.elapsedSeconds) + "]");
            Program next = programs.get((b.index + 1) % programs.size());
            guideNext.setText("UP NEXT  /  " + next.title + "  •  " + p.description);
            guideClock.setText(new SimpleDateFormat("EEE h:mm:ss a", Locale.US).format(new Date()));
        }
    }

    private String formatClock(int value) {
        return String.format(Locale.US, "%02d:%02d", value / 60, value % 60);
    }

    private void showGuide(boolean show) {
        guideVisible = show;
        guide.setVisibility(show ? View.VISIBLE : View.GONE);
        updateBroadcast(false);
    }

    private void openPlaylistDialog() {
        EditText input = new EditText(this);
        input.setSingleLine(true);
        input.setTextColor(INK);
        input.setHintTextColor(MUTED);
        input.setHint("https://.../channel.json");
        input.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        input.setText(getPreferences().getString(PLAYLIST_URL_KEY, ""));
        input.setSelectAllOnFocus(true);
        LinearLayout holder = new LinearLayout(this);
        holder.setPadding(dp(18), 0, dp(18), 0);
        holder.addView(input, new LinearLayout.LayoutParams(-1, -2));
        new AlertDialog.Builder(this)
                .setTitle("WITCH BOLT TV  /  VIDEO PLAYLIST")
                .setMessage("Paste the public HTTPS address of your channel.json file. Leave blank to use the built-in demo channel.")
                .setView(holder)
                .setNegativeButton("Cancel", (dialog, which) -> {})
                .setPositiveButton("Load channel", (dialog, which) -> {
                    String url = input.getText().toString().trim();
                    if (url.isEmpty()) {
                        getPreferences().edit().remove(PLAYLIST_URL_KEY).apply();
                        station = "WITCH BOLT TV";
                        createDemoSchedule();
                        activeIndex = -1;
                        updateBroadcast(true);
                        showGuide(true);
                    } else loadPlaylist(url, true);
                }).show();
    }

    private void loadPlaylist(String url, boolean saveIfValid) {
        if (isLoading) return;
        if (!url.startsWith("https://")) {
            Toast.makeText(this, "Use an HTTPS playlist URL", Toast.LENGTH_LONG).show();
            return;
        }
        isLoading = true;
        emptyMessage.setText("CONTACTING THE STATION…");
        worker.execute(() -> {
            try {
                HttpURLConnection connection = (HttpURLConnection) new URL(url).openConnection();
                connection.setConnectTimeout(8000);
                connection.setReadTimeout(8000);
                connection.setInstanceFollowRedirects(true);
                connection.setRequestProperty("Accept", "application/json");
                try {
                    if (connection.getResponseCode() != 200) throw new Exception("HTTP " + connection.getResponseCode());
                    ByteArrayOutputStream buffer = new ByteArrayOutputStream();
                    try (InputStream stream = connection.getInputStream()) {
                        byte[] chunk = new byte[4096];
                        int n;
                        while ((n = stream.read(chunk)) != -1) {
                            buffer.write(chunk, 0, n);
                            if (buffer.size() > 512 * 1024) throw new Exception("Playlist is too large");
                        }
                    }
                    JSONObject doc = new JSONObject(buffer.toString("UTF-8"));
                    JSONArray entries = doc.getJSONArray("programs");
                    if (entries.length() < 1 || entries.length() > 300) throw new Exception("Expected 1–300 programs");
                    List<Program> nextPrograms = new ArrayList<>();
                    for (int i = 0; i < entries.length(); i++) {
                        JSONObject entry = entries.getJSONObject(i);
                        String videoUrl = entry.getString("url");
                        int duration = entry.getInt("duration_seconds");
                        if (!videoUrl.startsWith("https://") || duration < 2 || duration > 12 * 3600)
                            throw new Exception("Program " + (i + 1) + " needs an HTTPS URL and valid duration_seconds");
                        String title = entry.getString("title");
                        nextPrograms.add(new Program(title, entry.optString("description", ""), videoUrl, duration));
                    }
                    String nextStation = doc.optString("station", "WITCH BOLT TV");
                    ui.post(() -> {
                        programs = nextPrograms;
                        station = nextStation;
                        activeIndex = -1;
                        if (saveIfValid) getPreferences().edit().putString(PLAYLIST_URL_KEY, url).apply();
                        isLoading = false;
                        updateBroadcast(true);
                        showGuide(true);
                        Toast.makeText(this, "Channel playlist loaded", Toast.LENGTH_SHORT).show();
                    });
                } finally {
                    connection.disconnect();
                }
            } catch (Exception error) {
                ui.post(() -> {
                    isLoading = false;
                    showGuide(true);
                    Toast.makeText(this, "Playlist error: " + error.getMessage(), Toast.LENGTH_LONG).show();
                });
            }
        });
    }

    @Override public boolean onKeyDown(int keyCode, KeyEvent event) {
        switch (keyCode) {
            case KeyEvent.KEYCODE_DPAD_CENTER:
            case KeyEvent.KEYCODE_ENTER:
                if (guideVisible) openPlaylistDialog();
                else showGuide(true);
                return true;
            case KeyEvent.KEYCODE_MENU:
            case KeyEvent.KEYCODE_SETTINGS:
                openPlaylistDialog();
                return true;
            case KeyEvent.KEYCODE_BACK:
                if (guideVisible) { showGuide(false); return true; }
                break;
            case KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE:
                if (player.isPlaying()) player.pause();
                else updateBroadcast(true);
                return true;
        }
        return super.onKeyDown(keyCode, event);
    }

    @Override protected void onResume() {
        super.onResume();
        if (player != null && !programs.isEmpty()) updateBroadcast(true);
    }

    @Override protected void onPause() {
        if (player != null) player.pause();
        super.onPause();
    }

    @Override protected void onDestroy() {
        ui.removeCallbacks(heartbeat);
        worker.shutdownNow();
        if (player != null) player.stopPlayback();
        super.onDestroy();
    }
}
