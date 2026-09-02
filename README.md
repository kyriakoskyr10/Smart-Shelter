# Smart-Shelter

# CCTV Livestream Viewer

A Docker-based CCTV livestream viewer that captures video from an RTSP camera and streams it via HLS (HTTP Live Streaming).

## Features

- **HLS Streaming**: Low-latency HTTP Live Streaming for better browser compatibility
- **Error Recovery**: Automatic reconnection and error recovery
- **Responsive Design**: Works on desktop and mobile devices
- **Fullscreen Support**: View stream in fullscreen mode
- **Control Buttons**: Play, pause, restart stream, and fullscreen controls

## Requirements

- Docker and Docker Compose
- A camera that supports RTSP protocol

## Setup

### 1. Configure Environment Variables

Edit the `.env` file and set your camera's RTSP URL:

```env
RTSP_URL=rtsp://username:password@camera-ip:port/stream/path
```

### 2. Start the Services

```bash
docker-compose up -d
```

This will start:
- **FFmpeg service**: Captures video from the RTSP camera and converts it to HLS
- **Nginx service**: Serves the HTML interface and streams on port 8080

### 3. Access the Viewer

Open your browser and navigate to:
```
http://localhost:8080
```

## HLS Configuration

The setup uses the following HLS parameters for low latency:
- **Segment Duration**: 2 seconds
- **Cache Size**: 6 segments
- **Low Latency Mode**: Enabled
- **Live Sync Duration**: 2 segments

## Troubleshooting

### Stream Not Loading
1. Check if the RTSP URL in `.env` is correct
2. Verify Docker containers are running: `docker-compose ps`
3. Check FFmpeg logs: `docker-compose logs ffmpeg`

### Browser Compatibility
- Chrome, Firefox, Safari, and Edge support HLS streaming
- For older browsers, you may need fallback video sources

### Network Errors
The player has built-in error recovery and will automatically attempt to reconnect if the stream drops.

## File Structure

- `docker-compose.yml` - Docker service configuration
- `index.html` - Web interface for streaming
- `nginx.conf` - Nginx server configuration
- `.env` - Environment variables (keep secret!)
- `hls/` - Directory for HLS stream segments

## Security Notes

- Keep your `.env` file secret (it contains camera credentials)
- Use strong passwords for camera access
- Consider using firewall rules to restrict access to port 8080
- Never commit `.env` to version control
