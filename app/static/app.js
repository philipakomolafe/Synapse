const recordBtn = document.getElementById("recordBtn");
const stopBtn = document.getElementById("stopBtn");
const recordingStatus = document.getElementById("recordingStatus");
const questionEl = document.getElementById("question");
const imageEl = document.getElementById("image");
const previewEl = document.getElementById("preview");
const askBtn = document.getElementById("askBtn");
const answerEl = document.getElementById("answer");
const audioEl = document.getElementById("audio");
const speakToggle = document.getElementById("speakAnswer");

const gradeEl = document.getElementById("grade");
const subjectEl = document.getElementById("subject");
const languageEl = document.getElementById("language");
const modeEl = document.getElementById("mode");

let mediaRecorder;
let audioChunks = [];
let sessionId = localStorage.getItem("synapse_session_id");
let imageBase64 = null;
let imageMime = "image/jpeg";

function uuidv4() {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

async function startSession() {
  if (sessionId) return;
  try {
    const res = await fetch("/v1/session/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ locale: navigator.language })
    });
    if (!res.ok) throw new Error("session_start_failed");
    const data = await res.json();
    sessionId = data.session_id;
  } catch {
    sessionId = uuidv4();
  }
  localStorage.setItem("synapse_session_id", sessionId);
}

async function logEvent(eventType, payload = {}) {
  if (!sessionId) return;
  try {
    await fetch("/v1/session/event", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        event_type: eventType,
        payload,
        client_ts: new Date().toISOString()
      })
    });
  } catch {
    // best-effort only
  }
}

async function startRecording() {
  await startSession();
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);
  audioChunks = [];

  mediaRecorder.ondataavailable = (event) => {
    if (event.data.size > 0) audioChunks.push(event.data);
  };

  mediaRecorder.onstop = async () => {
    const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
    const formData = new FormData();
    formData.append("audio", audioBlob, "recording.webm");

    recordingStatus.textContent = "Transcribing...";
    try {
      const res = await fetch("/v1/transcribe", { method: "POST", body: formData });
      if (!res.ok) throw new Error("transcribe_failed");
      const data = await res.json();
      questionEl.value = data.text || "";
      recordingStatus.textContent = "Transcription ready";
      logEvent("voice_transcribed", { length: (data.text || "").length });
    } catch {
      recordingStatus.textContent = "Transcription failed";
    }
  };

  mediaRecorder.start();
  recordBtn.disabled = true;
  stopBtn.disabled = false;
  recordingStatus.textContent = "Recording...";
  logEvent("voice_record_start");
}

function stopRecording() {
  if (!mediaRecorder) return;
  mediaRecorder.stop();
  recordBtn.disabled = false;
  stopBtn.disabled = true;
  recordingStatus.textContent = "Processing audio...";
  logEvent("voice_record_stop");
}

function handleImageChange(event) {
  const file = event.target.files[0];
  if (!file) return;
  imageMime = file.type || "image/jpeg";
  const reader = new FileReader();
  reader.onload = () => {
    const dataUrl = reader.result;
    imageBase64 = dataUrl.split(",")[1];
    previewEl.src = dataUrl;
    previewEl.style.display = "block";
    logEvent("image_attached", { size: file.size, type: file.type });
  };
  reader.readAsDataURL(file);
}

async function askTutor() {
  await startSession();
  const question = questionEl.value.trim();
  if (!question) {
    answerEl.textContent = "Please enter a question.";
    return;
  }

  answerEl.textContent = "Thinking...";
  audioEl.src = "";

  const payload = {
    question,
    grade_level: gradeEl.value || null,
    subject: subjectEl.value || null,
    mode: modeEl.value || null,
    language: languageEl.value || "en",
    image_base64: imageBase64,
    image_mime: imageMime,
    session_id: sessionId,
    use_retrieval: false,
    retrieval_top_k: 3
  };

  logEvent("tutor_request", { has_image: Boolean(imageBase64), mode: payload.mode });

  try {
    const res = await fetch("/v1/tutor", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error("tutor_failed");
    const data = await res.json();
    answerEl.textContent = data.answer || "No response";
    logEvent("tutor_response", { guard: data.guard || null });

    if (speakToggle.checked && data.answer) {
      const ttsRes = await fetch("/v1/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: data.answer, voice: "alloy", response_format: "mp3" })
      });
      if (ttsRes.ok) {
        const audioBlob = await ttsRes.blob();
        audioEl.src = URL.createObjectURL(audioBlob);
        audioEl.play();
      }
    }
  } catch {
    answerEl.textContent = "Something went wrong. Please try again.";
  }
}

recordBtn.addEventListener("click", startRecording);
stopBtn.addEventListener("click", stopRecording);
imageEl.addEventListener("change", handleImageChange);
askBtn.addEventListener("click", askTutor);

startSession();
