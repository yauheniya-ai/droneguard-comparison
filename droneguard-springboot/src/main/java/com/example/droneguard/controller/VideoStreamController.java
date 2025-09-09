package com.example.droneguard.controller;

import com.example.droneguard.video.VideoCaptureLoop;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;

@Controller
public class VideoStreamController {

    private final VideoCaptureLoop videoCaptureLoop;
    private static final String BOUNDARY = "frame";

    public VideoStreamController(VideoCaptureLoop videoCaptureLoop) {
        this.videoCaptureLoop = videoCaptureLoop;
    }

    /**
     * Redirect root URL to the video stream
     */
    @GetMapping("/")
    public String rootRedirect() {
        return "redirect:/video/stream";
    }

    /**
     * MJPEG video stream endpoint
     */
    @GetMapping(value = "/video/stream")
    public ResponseEntity<StreamingResponseBody> videoStream() {
        StreamingResponseBody stream = outputStream -> {
            System.out.println("📺 Client connected to video stream");
            try {
                int streamedFrames = 0;

                while (!Thread.currentThread().isInterrupted()) {
                    byte[] frameData = videoCaptureLoop.getLatestJpeg();

                    if (frameData != null && frameData.length > 0) {
                        try {
                            String boundary = "--" + BOUNDARY + "\r\n";
                            String header = "Content-Type: image/jpeg\r\n\r\n";
                            outputStream.write(boundary.getBytes(StandardCharsets.US_ASCII));
                            outputStream.write(header.getBytes(StandardCharsets.US_ASCII));
                            outputStream.write(frameData);
                            outputStream.write("\r\n".getBytes(StandardCharsets.US_ASCII));
                            outputStream.flush();

                            streamedFrames++;
                            if (streamedFrames % 300 == 0) {
                                System.out.println("📺 Streamed " + streamedFrames + " frames");
                            }
                        } catch (IOException e) {
                            System.out.println("📺 Client disconnected: " + e.getMessage());
                            break;
                        }
                    }

                    try {
                        Thread.sleep(33); // ~30 FPS
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                }

            } catch (Exception e) {
                System.err.println("❌ Streaming error: " + e.getMessage());
            } finally {
                System.out.println("📺 Video stream ended");
            }
        };

        HttpHeaders headers = new HttpHeaders();
        headers.set("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0");
        headers.set("Pragma", "no-cache");
        headers.set("Expires", "Thu, 01 Jan 1970 00:00:00 GMT");
        headers.set("Connection", "close");
        headers.set("Content-Type", "multipart/x-mixed-replace;boundary=" + BOUNDARY);

        return new ResponseEntity<>(stream, headers, HttpStatus.OK);
    }

    /**
     * Single frame endpoint
     */
    @GetMapping(value = "/video/frame", produces = MediaType.IMAGE_JPEG_VALUE)
    public ResponseEntity<byte[]> getSingleFrame() {
        byte[] frame = videoCaptureLoop.getLatestJpeg();

        if (frame == null || frame.length == 0) {
            return ResponseEntity.status(HttpStatus.NO_CONTENT).build();
        }

        HttpHeaders headers = new HttpHeaders();
        headers.set("Cache-Control", "no-cache");

        return ResponseEntity.ok()
                .headers(headers)
                .body(frame);
    }

    /**
     * Status endpoint
     */
    @GetMapping("/video/status")
    public ResponseEntity<String> getStatus() {
        byte[] frame = videoCaptureLoop.getLatestJpeg();
        String captureStats = videoCaptureLoop.getStats();

        String timestamp = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")
                .withZone(ZoneId.systemDefault())
                .format(Instant.now());

        String status = "📊 DroneGuard Status:\n" +
                        "Frame available: " + (frame != null && frame.length > 0) + "\n" +
                        "Frame size: " + (frame != null ? frame.length : 0) + " bytes\n" +
                        "Capture: " + captureStats + "\n" +
                        "Memory: " + (Runtime.getRuntime().totalMemory() - Runtime.getRuntime().freeMemory()) / 1024 / 1024 + "MB\n" +
                        "Timestamp: " + timestamp;

        return ResponseEntity.ok(status);
    }
}
