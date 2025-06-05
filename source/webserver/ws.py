import os
os.environ["HF_HOME"] = "D:/ws"
from flask import Flask, request, Response, jsonify
from transformers import pipeline
import google.generativeai as genai
from gtts import gTTS
from pydub import AudioSegment
import wave

# Tải mô hình Whisper một lần khi ứng dụng khởi động
whisper_model = pipeline("automatic-speech-recognition", model="vinai/PhoWhisper-tiny")  
# Cấu hình Google Generative AI
genai.configure(api_key="AIzaSyCxA64e2X5EJn-d3i9GqOZo0iqancL53Ws")
model = genai.GenerativeModel("gemini-2.0-flash")

# Biến toàn cục để lưu trữ dữ liệu âm thanh và trạng thái sẵn sàng
audio_buffer = bytearray()
ready = 0 # 0: chưa sẵn sàng, 1: đã sẵn sàng

# Khởi tạo session_history một lần ở phạm vi toàn cục
# Đây là nơi duy trì ngữ cảnh cho cuộc trò chuyện
session_history = [
    {"role": "system", "content": "Bạn, tên là Kiddy, đang trò chuyện với một đứa bé trong vai trò 1 người bạn, trả lời đúng trọng tâm, thân thiện, không chứa các ký tự đặc biện như dấu *, đừng lặp lại câu trả lời, đừng chào lại nhiều lần, trả lời dưới 60 từ"}
]

app = Flask(__name__)  # Phải định nghĩa app trước

@app.route('/send_audio_chunk', methods=['POST'])
def receive_audio_chunk():
    global audio_buffer, ready
    ready = 0 # Đặt lại trạng thái ready khi nhận chunk mới
    try:
        chunk = request.data
        audio_buffer.extend(chunk)
        print(f"Nhận chunk audio, tổng {len(audio_buffer)} bytes")
        return Response("Chunk received")
    except Exception as e:
        print("Lỗi nhận chunk:", e)
        return Response("Error", status=500)

@app.route('/end_audio', methods=['POST'])
def end_audio():
    global audio_buffer, ready, session_history

    try:
        if len(audio_buffer) == 0:
            return Response("No audio data", status=400)

        # Lưu dữ liệu âm thanh đã nhận được thành file WAV
        # Đảm bảo các tham số (channels, sampwidth, framerate) phù hợp với client gửi lên
        with wave.open("stream_audio.wav", "wb") as wav_file:
            wav_file.setnchannels(1)    # 1 kênh (mono)
            wav_file.setsampwidth(2)    # 2 bytes per sample (16-bit)
            wav_file.setframerate(16000) # Tần số lấy mẫu 8kHz
            wav_file.writeframes(audio_buffer)
        print("Đã lưu file âm thanh hoàn chỉnh: stream_audio.wav")

        # Nhận diện giọng nói từ file audio đã lưu
        print("Đang nhận diện giọng nói...")
        result = whisper_model("stream_audio.wav")
        text = result["text"]

        print("Nội dung nhận diện:", text)

        # Thêm nội dung nhận diện của người dùng vào lịch sử trò chuyện
        session_history.append({"role": "user", "content": text})

        # Gửi toàn bộ lịch sử trò chuyện (bao gồm cả prompt hệ thống và các lượt trò chuyện trước)
        # tới mô hình Gemini để tạo phản hồi
        print("Đang tạo phản hồi từ Gemini...")
        response = model.generate_content([m["content"] for m in session_history])
        reply = response.text
        print("Kiddy trả lời:", reply)

        # Lưu lại phản hồi của trợ lý vào lịch sử trò chuyện để duy trì ngữ cảnh
        session_history.append({"role": "assistant", "content": reply})

        # Tạo file âm thanh từ phản hồi của Gemini bằng gTTS
        tts = gTTS(reply, lang='vi')
        tts.save("response_audio.mp3")
        print("Đã tạo file MP3 từ phản hồi.")

        # Xử lý file âm thanh để phù hợp với yêu cầu client (resampling, channels, sample width)
        audio = AudioSegment.from_mp3("response_audio.mp3")
        new_frame_rate = int(audio.frame_rate * 1.5)
        audio = audio._spawn(audio.raw_data, overrides={'frame_rate': new_frame_rate})
        audio = audio.set_frame_rate(16000)
        audio = audio.set_channels(1)
        audio = audio.set_sample_width(2)
        audio.export("response_audio.wav", format="wav")
        print("Đã chuyển đổi và lưu file WAV phản hồi: response_audio.wav")

        # Xóa buffer âm thanh để chuẩn bị cho lượt tiếp theo
        audio_buffer = bytearray()
        ready = 1 # Đánh dấu rằng đã có phản hồi sẵn sàng

        return Response("Audio processed and response generated")

    except Exception as e:
        print("Lỗi xử lý cuối:", e)
        # Xóa file audio đã tạo nếu có lỗi để tránh lỗi phát lại sau này
        if os.path.exists("stream_audio.wav"):
            os.remove("stream_audio.wav")
        if os.path.exists("response_audio.mp3"):
            os.remove("response_audio.mp3")
        if os.path.exists("response_audio.wav"):
            os.remove("response_audio.wav")
        return Response(f"Error processing: {e}", status=500)

@app.route('/get_audio_response', methods=['GET'])
def send_audio_response():
    global ready
    try:
        if not os.path.exists("response_audio.wav"):
            print("Không tìm thấy file response_audio.wav")
            return Response("No audio available", status=404)

        with open("response_audio.wav", "rb") as f:
            audio_data = f.read()
        
        print("Đang gửi file response_audio.wav...")
        # Đặt ready về 0 sau khi gửi để client biết cần chờ phản hồi mới
        ready = 0 
        os.remove("response_audio.wav") # Xóa file sau khi gửi để tránh gửi lại
        print("Đã gửi và xóa file response_audio.wav")
        return Response(audio_data, content_type="audio/wav")

    except Exception as e:
        print("Lỗi phát âm thanh:", e)
        return Response(f"Error sending audio: {e}", status=500)

@app.route('/get_ready', methods=['GET'])
def get_ready():
    global ready
    return jsonify({"ready": ready})

# Endpoint để reset session_history nếu muốn bắt đầu cuộc trò chuyện mới
@app.route('/reset_session', methods=['POST'])
def reset_session():
    global session_history
    session_history = [
        {"role": "system", "content": "Bạn, tên là Kiddy, đang trò chuyện với một đứa bé trong vai trò 1 người bạn, trả lời đúng trọng tâm, thân thiện, không chứa các ký tự, đừng lặp lại câu trả lời, đừng chào lại nhiều lần. Hãy trả lời dễ hiểu, dưới 60 từ"}
    ]
    print("Đã reset lịch sử trò chuyện.")
    return Response("Session history reset", status=200)


if __name__ == '__main__':
    # Chạy ứng dụng Flask
    # debug=True sẽ tự động reload server khi có thay đổi code và cung cấp thông báo lỗi chi tiết hơn
    app.run(host='0.0.0.0', port=8000, debug=True)