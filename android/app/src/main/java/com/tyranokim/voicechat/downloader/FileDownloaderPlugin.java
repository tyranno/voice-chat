package com.tyranokim.voicechat.downloader;

import android.app.DownloadManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.webkit.MimeTypeMap;

import androidx.core.content.FileProvider;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import java.io.File;

@CapacitorPlugin(name = "FileDownloader")
public class FileDownloaderPlugin extends Plugin {
    private static final String TAG = "FileDownloader";
    private long downloadId = -1;
    private Handler progressHandler;
    private boolean tracking = false;

    @PluginMethod
    public void download(PluginCall call) {
        String url = call.getString("url");
        String filename = call.getString("filename");

        if (url == null || url.isEmpty()) {
            call.reject("URL is required");
            return;
        }

        // Extract filename from URL if not provided
        if (filename == null || filename.isEmpty()) {
            filename = extractFilename(url);
        }

        Log.d(TAG, "Starting download: " + url + " -> " + filename);

        try {
            DownloadManager dm = (DownloadManager) getContext().getSystemService(Context.DOWNLOAD_SERVICE);
            DownloadManager.Request request = new DownloadManager.Request(Uri.parse(url));

            // Guess MIME type
            String mimeType = guessMimeType(filename);

            request.setTitle(filename);
            request.setDescription("다운로드 중...");
            request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
            request.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, filename);
            if (mimeType != null) {
                request.setMimeType(mimeType);
            }

            // Allow scanning by MediaScanner
            request.allowScanningByMediaScanner();

            final String finalFilename = filename;
            downloadId = dm.enqueue(request);
            Log.d(TAG, "Download enqueued, id=" + downloadId);

            // Register completion receiver
            BroadcastReceiver receiver = new BroadcastReceiver() {
                @Override
                public void onReceive(Context context, Intent intent) {
                    long id = intent.getLongExtra(DownloadManager.EXTRA_DOWNLOAD_ID, -1);
                    if (id == downloadId) {
                        tracking = false;
                        try {
                            context.unregisterReceiver(this);
                        } catch (Exception e) {
                            Log.w(TAG, "unregisterReceiver failed", e);
                        }

                        // Check download status
                        DownloadManager.Query query = new DownloadManager.Query();
                        query.setFilterById(downloadId);
                        Cursor cursor = dm.query(query);
                        if (cursor != null && cursor.moveToFirst()) {
                            int statusIdx = cursor.getColumnIndex(DownloadManager.COLUMN_STATUS);
                            if (statusIdx >= 0) {
                                int status = cursor.getInt(statusIdx);
                                if (status == DownloadManager.STATUS_SUCCESSFUL) {
                                    Log.d(TAG, "Download complete: " + finalFilename);
                                    JSObject result = new JSObject();
                                    result.put("success", true);
                                    result.put("filename", finalFilename);
                                    
                                    // Notify frontend
                                    JSObject event = new JSObject();
                                    event.put("status", "complete");
                                    event.put("filename", finalFilename);
                                    notifyListeners("downloadComplete", event);
                                    
                                    call.resolve(result);
                                } else {
                                    int reasonIdx = cursor.getColumnIndex(DownloadManager.COLUMN_REASON);
                                    int reason = reasonIdx >= 0 ? cursor.getInt(reasonIdx) : -1;
                                    Log.e(TAG, "Download failed, status=" + status + " reason=" + reason);
                                    call.reject("Download failed (status=" + status + ", reason=" + reason + ")");
                                }
                            }
                            cursor.close();
                        } else {
                            call.reject("Could not query download status");
                        }
                    }
                }
            };

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                getContext().registerReceiver(receiver, new IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE), Context.RECEIVER_EXPORTED);
            } else {
                getContext().registerReceiver(receiver, new IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE));
            }

            // Start progress tracking
            startProgressTracking(dm);

        } catch (Exception e) {
            Log.e(TAG, "Download failed", e);
            call.reject("Download failed: " + e.getMessage());
        }
    }

    @PluginMethod
    public void openFile(PluginCall call) {
        String filename = call.getString("filename");
        if (filename == null || filename.isEmpty()) {
            call.reject("filename is required");
            return;
        }

        try {
            File file = new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), filename);
            if (!file.exists()) {
                call.reject("File not found: " + filename);
                return;
            }

            Uri uri = FileProvider.getUriForFile(getContext(),
                    getContext().getPackageName() + ".fileprovider", file);

            String mimeType = guessMimeType(filename);
            if (mimeType == null) mimeType = "*/*";

            Intent intent = new Intent(Intent.ACTION_VIEW);
            intent.setDataAndType(uri, mimeType);
            intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_GRANT_READ_URI_PERMISSION);
            getContext().startActivity(intent);

            JSObject result = new JSObject();
            result.put("success", true);
            call.resolve(result);
        } catch (Exception e) {
            Log.e(TAG, "Open file failed", e);
            call.reject("Failed to open file: " + e.getMessage());
        }
    }

    private void startProgressTracking(DownloadManager dm) {
        tracking = true;
        progressHandler = new Handler(Looper.getMainLooper());
        progressHandler.post(new Runnable() {
            @Override
            public void run() {
                if (!tracking) return;
                DownloadManager.Query query = new DownloadManager.Query();
                query.setFilterById(downloadId);
                Cursor cursor = dm.query(query);
                if (cursor != null && cursor.moveToFirst()) {
                    int bytesIdx = cursor.getColumnIndex(DownloadManager.COLUMN_BYTES_DOWNLOADED_SO_FAR);
                    int totalIdx = cursor.getColumnIndex(DownloadManager.COLUMN_TOTAL_SIZE_BYTES);
                    if (bytesIdx >= 0 && totalIdx >= 0) {
                        long downloaded = cursor.getLong(bytesIdx);
                        long total = cursor.getLong(totalIdx);
                        if (total > 0) {
                            int percent = (int) (downloaded * 100 / total);
                            JSObject data = new JSObject();
                            data.put("progress", percent);
                            data.put("downloaded", downloaded);
                            data.put("total", total);
                            notifyListeners("downloadProgress", data);
                        }
                    }
                    cursor.close();
                }
                progressHandler.postDelayed(this, 500);
            }
        });
    }

    private String extractFilename(String url) {
        try {
            // Remove query params
            String path = url.split("\\?")[0];
            String[] segments = path.split("/");
            String last = segments[segments.length - 1];
            if (last != null && !last.isEmpty() && last.contains(".")) {
                return Uri.decode(last);
            }
        } catch (Exception e) {
            Log.w(TAG, "Failed to extract filename from URL", e);
        }
        return "download_" + System.currentTimeMillis();
    }

    private String guessMimeType(String filename) {
        String ext = MimeTypeMap.getFileExtensionFromUrl(filename);
        if (ext == null || ext.isEmpty()) {
            int dotIdx = filename.lastIndexOf('.');
            if (dotIdx >= 0) {
                ext = filename.substring(dotIdx + 1).toLowerCase();
            }
        }
        if (ext != null && !ext.isEmpty()) {
            return MimeTypeMap.getSingleton().getMimeTypeFromExtension(ext);
        }
        return null;
    }
}
