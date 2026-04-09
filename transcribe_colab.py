"""Google Colab only: browser mic recording + ffmpeg + faster-whisper.

Run this notebook cell stack in Colab, not on your Mac terminal.
"""

from IPython.display import Javascript, display
from google.colab import output
from base64 import b64decode

record_js = """
async function recordAudio() {
  const div = document.createElement('div');
  const stopButton = document.createElement('button');
  stopButton.textContent = '⏹️ Stop Recording';
  stopButton.style.padding = '10px 20px';
  stopButton.style.fontSize = '16px';
  stopButton.style.backgroundColor = '#ff4c4c';
  stopButton.style.color = 'white';
  stopButton.style.border = 'none';
  stopButton.style.borderRadius = '5px';
  stopButton.style.cursor = 'pointer';
  stopButton.style.marginTop = '10px';

  div.appendChild(stopButton);
  document.body.appendChild(div);

  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const recorder = new MediaRecorder(stream);
  let chunks = [];

  recorder.ondataavailable = e => chunks.push(e.data);
  recorder.start();

  await new Promise(resolve => {
    stopButton.onclick = resolve;
  });

  recorder.stop();
  stopButton.disabled = true;
  stopButton.textContent = '⏳ Processing...';
  stopButton.style.backgroundColor = '#cccccc';

  await new Promise(resolve => recorder.onstop = resolve);

  const blob = new Blob(chunks, { type: 'audio/webm' });
  const arrayBuffer = await blob.arrayBuffer();
  const bytes = new Uint8Array(arrayBuffer);

  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }

  stream.getTracks().forEach(track => track.stop());
  div.remove();
  return btoa(binary);
}
"""

display(Javascript(record_js))
print("Recording started. Click the 'Stop Recording' button to stop...")

audio_base64 = output.eval_js("recordAudio()")
audio_bytes = b64decode(audio_base64)

with open("recorded_audio.webm", "wb") as f:
    f.write(audio_bytes)

print("Saved recorded_audio.webm")

import ffmpeg

(
    ffmpeg.input("recorded_audio.webm")
    .output("audio.wav", ac=1, ar=16000)
    .overwrite_output()
    .run(quiet=True)
)

from faster_whisper import WhisperModel

model_size = "large-v3"
model = WhisperModel(model_size, device="cuda", compute_type="float16")

segments, info = model.transcribe("audio.wav", beam_size=3, temperature=0.3)

print("Detected language '%s' with probability %f" % (info.language, info.language_probability))

full_text = []
for segment in segments:
    print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))
    full_text.append(segment.text)

final_text = " ".join(full_text)
print("\nFinal transcription:")
print(final_text)

with open("transcription.txt", "w", encoding="utf-8") as f:
    f.write(final_text)

print("Saved transcription to transcription.txt")
