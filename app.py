from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi

app = Flask(__name__)

# Dictionary to store cached srt_content based on video_code
srt_content_cache = {}

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)

    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def search_word_in_srt(srt_content, search_word):
    timecodes_list = []  # List to store all timecodes for the search word

    start_time, end_time, subtitle_text = None, None, ""

    for line in srt_content.splitlines():
        line = line.strip()

        if not line:  # Blank line indicates the end of a subtitle entry
            if search_word.lower() in subtitle_text.lower():
                timecodes_list.append(start_time)

            # Reset variables for the next subtitle entry
            start_time, end_time, subtitle_text = None, None, ""
        elif "-->" in line:  # Timecode line
            timecodes = line.split(" --> ")
            start_time, end_time = timecodes[0], timecodes[1]
        else:
            subtitle_text += line + " "  # Append subtitle text

    # Check for the last subtitle entry
    if search_word.lower() in subtitle_text.lower():
        timecodes_list.append(start_time)

    return timecodes_list

@app.route("/api", methods=["GET"])
def get_timestamps():
    video_code = request.args.get("video_code")
    search_word = request.args.get("search_word")

    if not video_code or not search_word:
        return jsonify({"error": "Both video_code and search_word parameters are required."}), 400

    try:
        # Check if the srt_content is available in the cache
        srt_content = srt_content_cache.get(video_code)

        if srt_content is None:
            # If not in the cache, fetch the video transcript
            subtitles = YouTubeTranscriptApi.get_transcript(video_code)

            # Combine the subtitle segments into an SRT format string
            srt_content = ""
            for i, subtitle in enumerate(subtitles, start=1):
                start_time = subtitle['start']
                end_time = subtitle['start'] + subtitle['duration']
                subtitle_text = subtitle['text'].strip().replace('\n', ' ')
                srt_content += f"{i}\n{format_time(start_time)} --> {format_time(end_time)}\n{subtitle_text}\n\n"

            # Store the srt_content in the cache
            srt_content_cache[video_code] = srt_content

        # Search for the search_word in the SRT content
        timecodes_list = search_word_in_srt(srt_content, search_word)

        if timecodes_list:
            return jsonify({"timestamps": timecodes_list})
        else:
            return jsonify({"message": f"The word '{search_word}' is not found in the subtitles."})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run()
