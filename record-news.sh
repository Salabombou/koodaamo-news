#!/bin/bash

source=$1
start_second=$2
duration=$3

if [ "$source" = "yle" ]; then
  stream_url="https://yletv.akamaized.net/hls/live/622365/yletv1fin/index.m3u8"
  sleep 30
elif [ "$source" = "mtv3" ]; then
  stream_url="https://live.streaming.a2d.tv/asset/20025962.isml/.m3u8"
  sleep 45
else
  echo "Unknown news source: $source"
  exit 1
fi
sleep "$start_second"

timestamp=$(date +%Y-%m-%d-%H-%M)
output_path="/tmp/$source/$timestamp"
vods_dir="/vods/$source"

mkdir -p "$output_path"
mkdir -p "$vods_dir"

source_upper=$(echo "$source" | awk '{print toupper($0)}')
echo "$(date '+%Y-%m-%d %H:%M:%S') Downloading latest $source_upper news VOD..."

# Record VOD
ffmpeg \
  -user_agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.3" \
  -multiple_requests 1 \
  -reconnect 1 \
  -reconnect_streamed 1 \
  -reconnect_delay_max 4294 \
  -timeout 5000000 \
  -t "$duration" \
  -i "$stream_url" \
  -loglevel fatal \
  -codec copy \
  -flags +cgop \
  -t "$duration" \
  -g 30 \
  -hls_time 5 \
  -hls_playlist_type vod \
  -hls_segment_filename "$output_path/segment-%03d.ts" \
  "$output_path/index.m3u8"

mv "$output_path" "$vods_dir"

# Remove old VODs leaving only the latest 5
find "$vods_dir" -mindepth 1 -maxdepth 1 -type d \
  | sort -r \
  | tail -n +6 \
  | xargs rm -rf --

# Create master playlist
echo "#EXTM3U" > "$vods_dir/playlist.m3u8"
while read -r vod; do
  index_file="$vod/index.m3u8"
  if [ -f "$index_file" ]; then
    vod_timestamp=$(basename "$vod")
    {
      echo "#EXTINF:-1,$source_upper News $vod_timestamp"
      echo "$vod_timestamp/index.m3u8"
    } >> "$vods_dir/playlist.m3u8"
  fi
done < <(find "$vods_dir" -mindepth 1 -maxdepth 1 -type d | sort -r)

# Create latest VOD playlist
{
  echo "#EXTM3U"
  echo "#EXT-X-STREAM-INF:BANDWIDTH=1200000"
  echo "$timestamp/index.m3u8"
} > "$vods_dir/latest.m3u8"

base_url="https://$HOSTNAME$vods_dir/$timestamp"

echo "$(date '+%Y-%m-%d %H:%M:%S') Latest $source_upper news VOD is available at $base_url"

# Cache VOD segments in cloudfare
echo "$(date '+%Y-%m-%d %H:%M:%S') Creating cache for $source_upper news VOD at $base_url/index.m3u8..."
ffmpeg -i "$base_url/index.m3u8" -loglevel fatal -f null -

echo "$(date '+%Y-%m-%d %H:%M:%S') Cache for $source_upper news VOD is ready at $base_url/index.m3u8"
