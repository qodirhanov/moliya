/**
 * OVOZLI YORDAMCHI — «Salom Moliya».
 * Nutqni brauzer matnga aylantiradi (Web Speech API: Chrome, Edge, Safari; Firefox'da yo'q — u yerda buyruq yoziladi).
 * Matn serverga yuboriladi (POST /api/v1/voice/ — mainapp/voice.py): server tushunadi va bajaradi, yetishmagan
 * ma'lumotni so'raydi. Bajarilgan amal ovozda aytilmaydi — orb yashil bo'ladi va «Bekor qilish» tugmali xabar chiqadi.
 * Brauzer tanimasa (Firefox, internet/til xatosi, gap tushunilmadi yoki umuman eshitilmadi) va serverda
 * OPENAI_API_KEY bo'lsa — shu gapning ovoz yozuvi serverga yuboriladi (mainapp/stt.py, Whisper) va o'sha yerda taniladi.
 * Shuning uchun kompyuterda tinglash paytida ovoz parallel yozib turiladi (telefonda mikrofon ikki joyga bo'linmaydi —
 * u yerda keyingi gap to'g'ridan-to'g'ri server orqali tinglanadi). Yozuv hech qayerda saqlanmaydi.
 * Holatlar: off → wake (fonda «Salom Moliya» kutiladi) → listen (orb ochiq, buyruq tinglanadi) → think → speak.
 * app.js dagi umumiy funksiyalardan foydalanadi (API_BASE, state, showToast, refreshAll, setTheme, open* ...),
 * shuning uchun undan keyin yuklanadi. Ilova nomi o'zgarsa — BRAND va WAKE_NAME ni yangilang
 */
(function () {
  const BRAND = 'Moliya';
  // Chaqiruv — faqat «Salom Moliya» (foydalanuvchi talabi: boshqa gapda yordamchi ochilmasin; «Moliya, …», «Hi Moliya»,
  // «Assalomu alaykum Moliya» ham chaqiruv emas). Tanish xizmati uni turlicha yozadi: "Salom, Moliya", "salom maliya",
  // "Салом Молия", "Salommoliya" — shuning uchun har so'z 1 harf farqigacha (Levenshtein) solishtiriladi.
  // 2 harf ruxsat etilmaydi: "Salom Malika" chaqiruv deb olinmasin
  const WAKE_NAME = 'moliya';
  const WAKE_GREETING = 'salom';

  const WAKE_KEY = 'moliyaVoiceWakeOn';  // standart yoqilgan (eski 'moliyaVoiceWake' — o'chiq edi)
  const LANG_KEY = 'moliyaVoiceLang';
  const GENDER_KEY = 'moliyaVoiceGender';  // javob ovozi: female (Madina) | male (Sardor)
  // Suhbat rejimi: amal yoki javobdan keyin «Salom Moliya»siz yana FOLLOWUP_MS tinglanadi ("yana taksiga 20 ming")
  const CONVO_KEY = 'moliyaVoiceConversation';
  const FOLLOWUP_MS = 7000;
  const FOLLOWUP_DELAY_MS = 900;  // natija bir lahza ko'rinib tursin
  const LANGS = ['uz-UZ', 'ru-RU'];  // o'zbekcha tanilmasa — ruscha (kirillda keladi, server lotinga o'giradi)
  const LISTEN_TIMEOUT_MS = 8000;    // orb ochiq, lekin gap yo'q — yopiladi
  // Brauzer «yakuniy» natijani gapdan 1–2 soniya keyin beradi. Tanilgan so'zlar shuncha vaqt o'zgarmasa va
  // mikrofon jim bo'lsa — buyruq kutmasdan yuboriladi (javob tezroq keladi)
  const SETTLE_MS = 800;
  const CLOSE_AFTER_DONE_MS = 1600;
  // Bilmaydigan yoki ilovaga aloqasiz savol ("ob-havo qanday"): javob shuncha ko'rinib turadi, so'ng orb yopiladi
  const UNKNOWN_CLOSE_MS = 3000;
  // Umumiy qo'riqchi: shuncha vaqt hech narsa aytilmasa/yozilmasa — orb har qanday holatda yopiladi
  // (shovqin «gap» deb olinib «Eshitmadim» → qayta tinglash aylanasi, yozish rejimi, mikrofon ruxsati yo'q...)
  const IDLE_CLOSE_MS = 2000;
  const MAX_UNDO = 5;
  // Server orqali tanish (VAD — gap tugaganini ovoz balandligidan aniqlash)
  const SPEECH_START_MS = 150;        // shuncha davom etgan ovoz — gap boshlandi
  const SPEECH_END_SILENCE_MS = 800;  // gapdan keyin shuncha jimlik — gap tugadi
  const NO_SPEECH_MS = 7000;          // umuman gapirilmasa — tinglash to'xtaydi
  const MAX_RECORD_MS = 15000;
  const MIN_AUDIO_BYTES = 2000;
  // Gapni bo'lish: yordamchi gapirayotganda foydalanuvchi gapirsa — javob to'xtaydi va tinglashga o'tiladi.
  // Mikrofon yordamchining o'z ovozini ham eshitadi: avval BARGE_GRACE_MS davomida shu aks-sado darajasi o'rganiladi,
  // so'ng undan aniq balandroq va BARGE_SPEECH_MS dan uzoq davom etgan ovozgina "foydalanuvchi gapirdi" deb olinadi
  const BARGE_GRACE_MS = 600;
  const BARGE_SPEECH_MS = 300;
  const BARGE_MIN_LEVEL = 0.25;
  const BARGE_ECHO_RATIO = 1.6;      // foydalanuvchi ovozi aks-sadoning eng baland joyidan shuncha marta baland
  const BARGE_ECHO_HALF_LIFE_MS = 3000;

  // Gapni bo'lish aniqlagichi: (daraja, vaqt) -> true, foydalanuvchi gapira boshlagan bo'lsa. Vaqtga asoslangan
  // (kadrlar soniga emas): sahifa sekin chizilsa ham aks-sado to'g'ri o'rganiladi. Aks-sadoning eng baland darajasi
  // eslab qolinadi va asta pasayadi; undan aniq baland ovoz BARGE_SPEECH_MS davom etsa — gapirildi
  function bargeDetector(startedAt) {
    let echo = 0;
    let last = startedAt;
    let loudSince = 0;
    return (level, now) => {
      echo *= Math.pow(0.5, Math.max(0, now - last) / BARGE_ECHO_HALF_LIFE_MS);
      last = now;
      if (now - startedAt < BARGE_GRACE_MS) {
        echo = Math.max(echo, level);
        return false;
      }
      if (level > Math.max(BARGE_MIN_LEVEL, echo * BARGE_ECHO_RATIO)) {
        loudSince = loudSince || now;
        return now - loudSince >= BARGE_SPEECH_MS;
      }
      loudSince = 0;
      echo = Math.max(echo, level);
      return false;
    };
  }

  // Mikrofon har gapdan keyin yopilib qayta ochilsa, Windows'dagi ovoz dasturlari (Acer Purified Voice, Realtek,
  // Nahimic...) har safar "qo'ng'iroq boshlandi" xabarini chiqaradi. Shuning uchun bitta oqim ochiq ushlab turiladi:
  // orb yopilgach shuncha vaqt kutiladi, «Salom Moliya» yoqilgan bo'lsa — varaq ochiq turguncha
  const MIC_IDLE_MS = 90000;       // bundan kichik yozuv — deyarli bo'sh
  const AUDIO_TYPES = ['audio/webm;codecs=opus', 'audio/ogg;codecs=opus', 'audio/mp4', 'audio/webm'];

  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const canListen = !!Recognition;
  const canSpeak = 'speechSynthesis' in window;
  const canRecord = !!(window.MediaRecorder && navigator.mediaDevices?.getUserMedia);
  // Telefonda brauzer tanish xizmati bilan parallel yozish mikrofonni band qiladi
  const isTouch = window.matchMedia('(pointer: coarse)').matches;

  const v = {
    mode: 'off',
    wake: false,        // foydalanuvchi «Salom Moliya» ni yoqqanmi
    rec: null,
    recMode: null,      // 'wake' | 'listen'
    restartDelay: 300,
    listenTimer: null,
    closeTimer: null,
    idleTimer: null,
    settleTimer: null,  // so'zlar o'zgarmay qolganini kutish (gap tugadimi)
    // Orb har yopilganda oshadi: yopilishdan oldin yuborilgan buyruqning kech kelgan javobi tashlanadi
    session: 0,
    abort: null,        // yuborilayotgan so'rov (yopilganda uziladi)
    fresh: false,       // orb yangi ochildi — serverdagi eski savol (javob kutilayotgan) unutilsin
    lang: null,
    heard: '',
    lastDone: [],
    voices: [],
    capture: null,      // mikrofon o'lchagichi va yozuv: { stream, ctx, recorder, chunks, hadSpeech, ... }
    started: false,
    busy: false,
    speakSeq: 0,        // har yangi gapda oshadi — eski (kech kelgan) ovoz ijro etilmaydi
    audioSource: null,  // hozir ijro etilayotgan server ovozi
    browserBroken: false,  // brauzer tanish xizmati ishlamadi (internet, til) — shu safar server taniydi
    preferServer: false,   // brauzer tanigan gap tushunilmadi — keyingi javob server orqali tinglanadi
    conversation: true,    // suhbat rejimi (sozlamalarda o'chiriladi)
    followUp: false,       // hozirgi tinglash — suhbat davomi (tushunilmasa jimgina yopiladi)
  };

  function storageGetSafe(key) { try { return localStorage.getItem(key); } catch (e) { return null; } }
  function storageSetSafe(key, value) { try { localStorage.setItem(key, value); } catch (e) { /* faqat shu safar */ } }

  // Standart — yoqilgan: foydalanuvchi o'zi o'chirmagan bo'lsa «Salom Moliya» eshitiladi (mikrofonga ruxsat berilgach)
  v.wake = storageGetSafe(WAKE_KEY) !== '0';
  v.conversation = storageGetSafe(CONVO_KEY) !== '0';
  v.micAllowed = false;  // mikrofonga ruxsat berilganmi — bermasdan fonda tinglash boshlanmaydi (kutilmagan so'rov chiqmasin)
  v.lang = LANGS.includes(storageGetSafe(LANG_KEY)) ? storageGetSafe(LANG_KEY) : LANGS[0];

  const $ = (id) => document.getElementById(id);
  const layer = $('voiceLayer');
  const orb = $('voiceOrb');
  const heardEl = $('voiceHeard');
  const replyEl = $('voiceReply');
  const typeForm = $('voiceTypeForm');
  const typeInput = $('voiceTypeInput');
  const navBtn = $('btnVoice');
  if (!layer || !orb) return;

  // ---------- Orb ----------

  function setOrb(mode) {
    v.mode = mode;
    layer.dataset.state = mode;
    orb.setAttribute('aria-label', {
      listen: 'Tinglayapman — gapiring', think: "O'ylayapman", speak: 'Javob beryapman',
      done: 'Bajarildi', error: 'Xatolik',
    }[mode] || 'Ovozli yordamchi');
    navBtn?.classList.toggle('is-active', !layer.hidden);
    navBtn?.classList.toggle('is-wake', wakeActive());
  }

  // Foydalanuvchi biror narsa aytdi yoki yozdi — qo'riqchi qaytadan sanaydi. Javob kutilayotgan yoki o'qilayotgan
  // paytda yopilmaydi, faqat keyinga suriladi
  function armIdle(ms = IDLE_CLOSE_MS) {
    clearTimeout(v.idleTimer);
    v.idleTimer = setTimeout(() => {
      if (layer.hidden) return;
      // Javob kutilmoqda/o'qilmoqda — keyinga suriladi
      if (v.busy || v.mode === 'think' || v.mode === 'speak') {
        armIdle();
        return;
      }
      // Yordamchi savol berdi yoki javobdan keyin suhbat davomini kutmoqda: foydalanuvchiga o'ylash uchun to'liq
      // vaqt beriladi — uni tinglash taymerlari (LISTEN_TIMEOUT_MS / FOLLOWUP_MS / NO_SPEECH_MS) o'zi yopadi
      if (v.awaiting) {
        armIdle();
        return;
      }
      // Foydalanuvchi hozirgina gapirgan — jimlik so'nggi ovozdan IDLE_CLOSE_MS o'tganda hisoblanadi
      const sinceVoice = Date.now() - (v.voiceAt || 0);
      if (sinceVoice < IDLE_CLOSE_MS) {
        armIdle(IDLE_CLOSE_MS - sinceVoice);
        return;
      }
      closeOrb();
    }, ms);
  }

  function openOrb() {
    clearTimeout(v.closeTimer);
    if (layer.hidden) {
      armIdle();
      v.fresh = true;
      layer.hidden = false;
      heardEl.textContent = '';
      replyEl.textContent = '';
      replyEl.className = 'voice-reply';
      renderItems([]);
      typeForm.hidden = currentEngine() !== 'type';
    }
    navBtn?.classList.add('is-active');
  }

  function closeOrb() {
    clearTimeout(v.closeTimer);
    clearTimeout(v.listenTimer);
    clearTimeout(v.idleTimer);
    clearTimeout(v.settleTimer);
    // Yopildi — yordamchiga aytilgan gap shu bilan tugaydi: yo'ldagi so'rov uziladi, kech kelgan javob ijro etilmaydi
    v.session++;
    v.abort?.abort();
    v.abort = null;
    stopCapture(true);
    stopSpeaking();
    layer.hidden = true;
    navBtn?.classList.remove('is-active');
    v.busy = false;
    v.awaiting = false;
    v.preferServer = false;
    v.followUp = false;
    delete layer.dataset.follow;
    // Fonda yana «Salom Moliya» kutiladi
    if (wakeActive()) {
      startRecognition('wake');
      holdMicForWake();
    } else {
      stopRecognition();
      releaseMicLater();
    }
    setOrb(wakeActive() ? 'wake' : 'off');
  }

  function closeLater(ms = CLOSE_AFTER_DONE_MS) {
    clearTimeout(v.closeTimer);
    v.closeTimer = setTimeout(closeOrb, ms);
  }

  function showHeard(text) {
    heardEl.textContent = text ? `«${text}»` : '';
  }

  // Javob tagidagi ro'yxat: [{label, value}]. Matn faqat textContent bilan — serverdan kelgan nomlar HTML bo'lmaydi
  const itemsEl = document.createElement('ul');
  itemsEl.className = 'voice-items';
  itemsEl.hidden = true;
  replyEl.after(itemsEl);

  function renderItems(items) {
    itemsEl.textContent = '';
    (items || []).slice(0, 8).forEach(item => {
      const li = document.createElement('li');
      const label = document.createElement('span');
      label.className = 'voice-item-label';
      label.textContent = item.label;
      const value = document.createElement('span');
      value.className = 'voice-item-value';
      value.textContent = item.value;
      li.append(label, value);
      itemsEl.appendChild(li);
    });
    itemsEl.hidden = !itemsEl.childElementCount;
  }

  function showReply(text, kind = '') {
    replyEl.textContent = text || '';
    replyEl.className = `voice-reply${kind ? ` is-${kind}` : ''}`;
  }

  // ---------- Qaysi yo'l bilan tinglanadi ----------

  const serverStt = () => !!state.currentUser?.voice_server_stt && canRecord;

  // browser — brauzer o'zi taniydi; server — ovoz yozilib serverda taniladi; type — faqat yozish
  function currentEngine() {
    const browserOk = canListen && !v.browserBroken;
    if (browserOk && !(v.preferServer && serverStt())) return 'browser';
    if (serverStt()) return 'server';
    return browserOk ? 'browser' : 'type';
  }

  // Brauzer xizmati ishlamay qoldi: server bor bo'lsa — shu seans davomida o'shanga o'tiladi
  function useServerFallback() {
    if (!serverStt()) return false;
    v.browserBroken = true;
    stopRecognition();
    if (!layer.hidden && v.mode === 'listen' && !v.busy) {
      stopCapture(true);
      listen();
    }
    return true;
  }

  // ---------- Mikrofon: orb "nafasi", gap tugaganini aniqlash va ovoz yozuvi ----------
  let micStream = null;
  let micPromise = null;
  let micReleaseTimer = null;
  let micWanted = 0;  // releaseMicNow() har chaqirilganda oshadi: kutilayotgan so'rov bekor qilinganini bildiradi

  // Umumiy mikrofon oqimi: ochiq bo'lsa qayta so'ralmaydi
  async function acquireMic() {
    clearTimeout(micReleaseTimer);
    if (micStream?.getAudioTracks().some(t => t.readyState === 'live')) return micStream;
    if (!micPromise) {
      const wanted = micWanted;
      micPromise = navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } })
        .then(stream => {
          // So'rov kutilayotganda mikrofon yopilgan bo'lsa, kech kelgan oqim saqlanib yonib qolmasin
          if (micWanted !== wanted) { stream.getTracks().forEach(t => t.stop()); throw new DOMException('Mikrofon yopildi', 'AbortError'); }
          micStream = stream; v.micAllowed = true; v.micDenied = false; return stream;
        })
        .finally(() => { micPromise = null; });
    }
    return micPromise;
  }

  function releaseMicNow() {
    clearTimeout(micReleaseTimer);
    micWanted++;
    micStream?.getTracks().forEach(t => t.stop());
    micStream = null;
  }

  function releaseMicLater(ms = MIC_IDLE_MS) {
    clearTimeout(micReleaseTimer);
    micReleaseTimer = setTimeout(releaseMicNow, ms);
  }

  // «Salom Moliya» yoqilgan bo'lsa mikrofon oldindan ochib qo'yiladi (ruxsat allaqachon berilgan — so'rov chiqmaydi):
  // tanish xizmati har qayta boshlanganda qurilma yangidan ochilmaydi
  function holdMicForWake() {
    if (!(wakeActive()) || document.hidden || !navigator.mediaDevices?.getUserMedia) return;
    acquireMic().catch(() => { /* ruxsat yo'q — onError xabar beradi */ });
  }

  // record — yozib olish (serverga yuborish uchun); vad — gap tugaganda onDone(blob, hadSpeech) chaqiriladi
  async function startCapture({ record = false, vad = false, onDone = null, onBarge = null,
                                noSpeechMs = NO_SPEECH_MS, maxMs = MAX_RECORD_MS } = {}) {
    if (v.capture || !navigator.mediaDevices?.getUserMedia) return;
    const cap = { raf: 0, hadSpeech: false, chunks: [], recorder: null, finished: false, onDone, vad, onBarge,
                  noSpeechMs, maxMs, startedAt: performance.now(), loudSince: 0, quietSince: 0, floor: 0.05 };
    if (onBarge) cap.barge = bargeDetector(cap.startedAt);
    v.capture = cap;
    try {
      cap.stream = await acquireMic();
    } catch (e) {
      if (v.capture === cap) v.capture = null;
      if (e?.name === 'AbortError') return;  // mikrofon so'rov paytida yopildi — rad etilgan emas
      if (vad) onDone?.(null, false, 'denied');
      return;  // ruxsat yo'q — orb oddiy animatsiya bilan ishlayveradi
    }
    if (v.capture !== cap) return;  // shu orada to'xtatilgan (oqim keyingi gap uchun ochiq qoladi)
    cap.ctx = new (window.AudioContext || window.webkitAudioContext)();
    const analyser = cap.ctx.createAnalyser();
    analyser.fftSize = 512;
    cap.ctx.createMediaStreamSource(cap.stream).connect(analyser);
    const data = new Uint8Array(analyser.frequencyBinCount);

    if (record && canRecord) {
      const mimeType = AUDIO_TYPES.find(t => MediaRecorder.isTypeSupported?.(t));
      try {
        cap.recorder = new MediaRecorder(cap.stream, mimeType ? { mimeType } : undefined);
        cap.recorder.ondataavailable = (e) => { if (e.data?.size) cap.chunks.push(e.data); };
        cap.recorder.start(250);
      } catch (e) {
        cap.recorder = null;
      }
    }

    const tick = () => {
      if (v.capture !== cap) return;
      analyser.getByteFrequencyData(data);
      let sum = 0;
      for (let i = 0; i < data.length; i++) sum += data[i];
      const level = Math.min(1, sum / data.length / 70);
      const now = performance.now();

      if (cap.barge) {
        // Yordamchi gapirmoqda: orb mikrofon darajasini ko'rsatmaydi (o'z ovozi bilan "tebranmasin")
        if (cap.barge(level, now)) {
          v.voiceAt = Date.now();
          cap.onBarge();
          return;
        }
        cap.raf = requestAnimationFrame(tick);
        return;
      }

      orb.style.setProperty('--level', level.toFixed(3));
      // Shovqin darajasi asta-sekin moslashadi: konditsioner yoki ko'cha shovqini "gap" deb olinmasin
      if (!cap.loudSince) cap.floor = cap.floor * 0.97 + level * 0.03;
      const speakThreshold = Math.max(0.16, cap.floor * 2.6);
      const silenceThreshold = Math.max(0.09, cap.floor * 1.7);
      if (level > speakThreshold) {
        cap.loudSince = cap.loudSince || now;
        cap.quietSince = 0;
        if (now - cap.loudSince > SPEECH_START_MS) {
          cap.hadSpeech = true;
          v.voiceAt = Date.now();
        }
      } else if (level < silenceThreshold) {
        cap.loudSince = 0;
        cap.quietSince = cap.quietSince || now;
      }
      if (cap.vad) {
        const elapsed = now - cap.startedAt;
        if ((cap.hadSpeech && cap.quietSince && now - cap.quietSince > SPEECH_END_SILENCE_MS)
            || (!cap.hadSpeech && elapsed > cap.noSpeechMs)
            || elapsed > cap.maxMs) {
          finishCapture(cap);
          return;
        }
      }
      cap.raf = requestAnimationFrame(tick);
    };
    tick();
  }

  // Yozuvni yakunlab Blob qaytaradi (yozilmagan yoki gap bo'lmagan bo'lsa null). discard — natija kerak emas
  function stopCapture(discard = false) {
    const cap = v.capture;
    v.capture = null;
    orb.style.setProperty('--level', '0');
    if (!cap) return Promise.resolve(null);
    cancelAnimationFrame(cap.raf);
    // Mikrofon oqimi yopilmaydi — faqat shu gapning o'lchagichi (orb yopilganda releaseMicLater)
    const release = () => {
      cap.ctx?.close().catch(() => {});
    };
    if (!cap.recorder || cap.recorder.state === 'inactive' || discard) {
      try { cap.recorder?.stop(); } catch (e) { /* allaqachon to'xtagan */ }
      release();
      return Promise.resolve(null);
    }
    return new Promise((resolve) => {
      cap.recorder.onstop = () => {
        release();
        const blob = new Blob(cap.chunks, { type: cap.recorder.mimeType || 'audio/webm' });
        resolve(cap.hadSpeech && blob.size >= MIN_AUDIO_BYTES ? blob : null);
      };
      try { cap.recorder.stop(); } catch (e) { release(); resolve(null); }
    });
  }

  async function finishCapture(cap) {
    if (cap.finished) return;
    cap.finished = true;
    const hadSpeech = cap.hadSpeech;
    const blob = await stopCapture();
    cap.onDone?.(blob, hadSpeech);
  }

  // ---------- Server orqali «Salom Moliya» (Android ilovasi, Firefox: brauzerda nutq xizmati yo'q) ----------
  // Ilova ochiq turganda mikrofon qisqa oynalarda tinglanadi: gap boshlansa — yozib, serverga yuboriladi (matnga
  // aylantiriladi, buyruq bajarilmaydi). Matnda «Salom Moliya» topilsa yordamchi ochiladi. Gap bo'lmasa hech narsa yuborilmaydi
  const WAKE_WINDOW_MS = 3000;     // jim turganda yozuv oynasi shuncha davom etadi va qayta boshlanadi
  const WAKE_MAX_MS = 6000;        // «Salom Moliya» qisqa: bundan uzun gap yuborilmaydi
  const WAKE_MIN_GAP_MS = 2500;    // serverga yuborishlar orasidagi eng kam vaqt (limit va kredit tejash)
  const serverWake = () => serverStt() && (v.noSpeechService || !canListen);

  function runWakeCapture() {
    if (!v.wakeLoop || v.capture) return;
    startCapture({ record: true, vad: true, onDone: onWakeUtterance, noSpeechMs: WAKE_WINDOW_MS, maxMs: WAKE_MAX_MS });
  }

  function startWakeLoop() {
    if (!serverWake() || !layer.hidden || v.busy || document.hidden) return;
    v.wakeLoop = true;
    runWakeCapture();
  }

  function stopWakeLoop() {
    if (!v.wakeLoop) return;
    v.wakeLoop = false;
    stopCapture(true);
  }

  async function onWakeUtterance(blob, hadSpeech, problem) {
    if (!v.wakeLoop) return;
    if (problem === 'denied') {
      v.wakeLoop = false;
      v.micAllowed = false;
      renderSettings();
      return;
    }
    if (!layer.hidden || v.busy) return;  // yordamchi shu orada qo'lda ochilgan — sikl keyin o'zi qayta boshlanadi
    let wait = 0;
    if (blob && hadSpeech) {
      wait = Math.max(0, WAKE_MIN_GAP_MS - (Date.now() - (v.wakeSentAt || 0)));
      v.wakeSentAt = Date.now() + wait;
      const session = v.session;
      let heard = '';
      try {
        if (wait) await new Promise(r => setTimeout(r, wait));
        const form = new FormData();
        form.append('audio', blob, `wake.${(blob.type.split('/')[1] || 'webm').split(';')[0]}`);
        const res = await fetch(`${API_BASE}/voice/wake/`, { method: 'POST', body: form });
        if (res.ok) heard = String((await res.json().catch(() => ({}))).heard || '');
      } catch (e) { /* internet yo'q — keyingi gapda qayta uriniladi */ }
      if (!v.wakeLoop || session !== v.session || !layer.hidden || v.busy) return;
      const wake = findWake(heard);
      if (wake) {
        v.wakeLoop = false;
        openOrb();
        setOrb('listen');
        chime('listen');
        if (wake.rest) submit(wake.rest);
        else greetAndListen();
        return;
      }
      wait = 0;
    }
    runWakeCapture();
  }

  // ---------- Qisqa ovozli signal (tinglash boshlandi / bajarildi) ----------
  let audioCtx = null;
  function chime(kind) {
    try {
      audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
      if (audioCtx.state === 'suspended') audioCtx.resume();
      const notes = kind === 'done' ? [660, 990] : kind === 'error' ? [330, 247] : [523, 784];
      notes.forEach((freq, i) => {
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        const at = audioCtx.currentTime + i * 0.09;
        osc.type = 'sine';
        osc.frequency.value = freq;
        gain.gain.setValueAtTime(0.0001, at);
        gain.gain.exponentialRampToValueAtTime(0.12, at + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, at + 0.16);
        osc.connect(gain).connect(audioCtx.destination);
        osc.start(at);
        osc.stop(at + 0.18);
      });
    } catch (e) { /* ovoz chiqmasa ham ish to'xtamaydi */ }
  }

  // ---------- Nutqni tanish ----------

  const CYR = { а: 'a', б: 'b', в: 'v', г: 'g', д: 'd', е: 'e', ё: 'yo', ж: 'j', з: 'z', и: 'i', й: 'y', к: 'k', л: 'l',
    м: 'm', н: 'n', о: 'o', п: 'p', р: 'r', с: 's', т: 't', у: 'u', ф: 'f', х: 'x', ц: 'ts', ч: 'ch', ш: 'sh', щ: 'sh',
    ъ: '', ы: 'i', ь: '', э: 'e', ю: 'yu', я: 'ya', ў: 'o', қ: 'q', ғ: 'g', ҳ: 'h' };

  function wakeWords(text) {
    return String(text || '').toLowerCase().replace(/[а-яёўқғҳ]/g, ch => CYR[ch] ?? ch)
      .replace(/[ʻʼ‘’'`]/g, '').replace(/[^a-z0-9\s]/g, ' ').split(/\s+/).filter(Boolean);
  }

  function editDistance(a, b) {
    if (Math.abs(a.length - b.length) > 2) return 3;
    let prev = Array.from({ length: b.length + 1 }, (_, j) => j);
    for (let i = 1; i <= a.length; i++) {
      const cur = [i];
      for (let j = 1; j <= b.length; j++) {
        cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      }
      prev = cur;
    }
    return prev[b.length];
  }

  const isName = (w) => !!w && editDistance(w, WAKE_NAME) <= 1;
  const isGreeting = (w) => !!w && editDistance(w, WAKE_GREETING) <= 1;  // salom, salam, salom

  // «Salom Moliya ...» bormi; bo'lsa — undan keyingi gap (buyruq) qaytariladi
  function findWake(text) {
    const words = wakeWords(text);
    // Buyruq qismi asl matndan olinadi (tutuq belgilari va bosh harflar saqlansin — izohga shunday yoziladi)
    const original = String(text || '').split(/\s+/).filter(w => wakeWords(w).length);
    const restFrom = (k) => ({ rest: original.slice(k).join(' ').replace(/^[\s,.!?]+/, '') });
    for (let i = 0; i < words.length; i++) {
      // "salommoliya" — ikki so'z qo'shilib tanilgan
      if (editDistance(words[i], WAKE_GREETING + WAKE_NAME) <= 1) return restFrom(i + 1);
      if (!isGreeting(words[i])) continue;
      if (isName(words[i + 1])) return restFrom(i + 2);
    }
    return null;
  }

  function stopRecognition() {
    stopWakeLoop();
    const rec = v.rec;
    v.rec = null;
    v.recMode = null;
    if (rec) {
      rec.onend = rec.onresult = rec.onerror = null;
      try { rec.abort(); } catch (e) { /* allaqachon to'xtagan */ }
    }
  }

  function startRecognition(mode) {
    // Bu qurilmada nutq xizmati yo'q (ilova, Firefox): fonda eshitish server orqali, tinglash esa listen() da
    if (serverWake()) {
      if (mode === 'wake') startWakeLoop();
      return;
    }
    if (!canListen || v.noSpeechService) return;
    if (v.rec && v.recMode === mode) return;
    stopRecognition();
    if (document.hidden) return;  // yashirin varaqda tinglanmaydi — qaytganda qayta yoqiladi
    const rec = new Recognition();
    rec.lang = v.lang;
    rec.continuous = true;
    rec.interimResults = true;
    rec.maxAlternatives = 3;
    v.rec = rec;
    v.recMode = mode;

    rec.onresult = (event) => onResult(event);
    rec.onerror = (event) => onError(event.error);
    rec.onend = () => {
      if (v.rec !== rec) return;
      v.rec = null;
      // Brauzer uzluksiz tinglashni vaqti-vaqti bilan to'xtatadi — kerak bo'lsa qayta boshlanadi
      const want = v.mode === 'listen' ? 'listen' : (wakeActive() && layer.hidden ? 'wake' : null);
      if (want) setTimeout(() => { if (!v.rec && !v.busy) startRecognition(want); }, v.restartDelay);
    };
    try {
      rec.start();
    } catch (e) {
      // Oldingi seans hali to'liq yopilmagan — biroz kutib qayta urinadi
      v.rec = null;
      setTimeout(() => { if (!v.rec && !v.busy && (mode === 'listen' ? v.mode === 'listen' : layer.hidden)) startRecognition(mode); }, 400);
    }
  }

  // Mikrofon brauzer sozlamasida aniq bloklanganmi (so'rab bo'lmasa — noma'lum, bloklangan deb hisoblanmaydi)
  async function micBlocked() {
    try { return (await navigator.permissions.query({ name: 'microphone' })).state === 'denied'; }
    catch (e) { return false; }
  }

  function showMicDenied() {
    v.micAllowed = false;  // tanlov saqlanadi: ruxsat keyin berilsa «Salom Moliya» yana ishlaydi
    stopRecognition();
    if (!layer.hidden) {
      // Yordamchining savoli (masalan «Qaysi hamyondan?») o'chmasin — ogohlantirish eshitilgan matn o'rnida
      heardEl.textContent = "Mikrofonga ruxsat yo'q — manzil satridagi qulf belgisidan yoqing yoki javobni yozing.";
      if (!replyEl.textContent) setOrb('error');
      typeForm.hidden = false;
      typeInput.focus();
    } else {
      showToast("Mikrofonga ruxsat yo'q — «Salom Moliya» ishlashi uchun manzil satridagi qulf belgisidan mikrofonni yoqing", 'error');
    }
    renderSettings();
  }

  function onError(error) {
    // Nutq xizmati brauzerda o'chirilgan (siyosat, Brave va h.k.), mikrofon esa bor — server taniydi
    if (error === 'service-not-allowed' && useServerFallback()) return;
    if (error === 'not-allowed' || error === 'service-not-allowed') {
      // Android ilovasi (WebView): nutq tanish xizmati yo'q va u ham «not-allowed» beradi, mikrofonning o'zi esa
      // ishlaydi. Mikrofon sozlamada aniq bloklanmagan bo'lsa — mikrofonga ruxsat so'ralmaydi, server taniydi
      if (serverStt() && !v.noSpeechService) {
        v.noSpeechService = true;
        stopRecognition();
        micBlocked().then(blocked => {
          if (blocked) { v.noSpeechService = false; showMicDenied(); return; }
          useServerFallback();
          if (layer.hidden && wakeActive()) startRecognition('wake');  // fonda «Salom Moliya» — server orqali
        });
        return;
      }
      showMicDenied();
      return;
    }
    if (error === 'language-not-supported') {
      const next = LANGS[LANGS.indexOf(v.lang) + 1];
      if (next) {
        v.lang = next;
        storageSetSafe(LANG_KEY, next);
      } else {
        useServerFallback();
      }
      return;  // onend qayta boshlaydi
    }
    if (error === 'network') {
      if (useServerFallback()) return;
      v.restartDelay = Math.min(v.restartDelay * 2, 10000);  // internet uzilgan — tez-tez urinmaslik uchun
      if (!layer.hidden) showReply("Nutqni tanish uchun internet kerak. Buyruqni yozib yuboring.", 'error');
      typeForm.hidden = false;
    }
    // no-speech, aborted — onend o'zi qayta boshlaydi
  }

  function bestTranscript(result) {
    return (result[0]?.transcript || '').trim();
  }

  function onResult(event) {
    v.restartDelay = 300;
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const result = event.results[i];
      const text = bestTranscript(result);

      if (v.recMode === 'wake') {
        // Uyg'otish so'zi istalgan muqobil tanilishda bo'lsa yetadi: "Salom Moliya" ba'zan 2-variantda keladi
        let wake = null;
        for (let a = 0; a < result.length && !wake; a++) wake = findWake(result[a].transcript || '');
        if (!wake) continue;
        openOrb();
        setOrb('listen');
        chime('listen');
        startCapture({ record: canRecordParallel() });
        armListenTimeout();
        if (result.isFinal) {
          stopRecognition();
          if (wake.rest) submit(wake.rest);
          else greetAndListen();
        } else {
          // Gap davom etmoqda: tinglash rejimiga o'tiladi, yakuniy matn kutiladi
          v.recMode = 'listen';
          showHeard(wake.rest);
        }
        return;
      }

      if (v.recMode === 'listen') {
        armListenTimeout();
        armIdle();
        const wake = findWake(text);
        const command = wake ? wake.rest : text;
        showHeard(command);
        clearTimeout(v.settleTimer);
        if (result.isFinal && command) {
          stopRecognition();
          submit(command);
          return;
        }
        if (command) armSettle(command);
      }
    }
  }

  // So'zlar SETTLE_MS o'zgarmadi: mikrofon ham jim bo'lsa — gap tugagan, yakuniy natija kutilmaydi.
  // Mikrofon hali ovoz eshitayotgan bo'lsa (o'ylab gapirilmoqda) — yana kutiladi
  function armSettle(command) {
    clearTimeout(v.settleTimer);
    v.settleTimer = setTimeout(() => {
      if (v.mode !== 'listen' || v.busy || v.recMode !== 'listen' || layer.hidden) return;
      if (Date.now() - (v.voiceAt || 0) < SETTLE_MS) {
        armSettle(command);
        return;
      }
      stopRecognition();
      submit(command);
    }, SETTLE_MS);
  }

  // Kompyuterda brauzer tinglayotganda ovoz parallel yoziladi: tanilmasa — shu yozuv serverga ketadi
  function canRecordParallel() {
    return serverStt() && !isTouch;
  }

  function armListenTimeout(ms = LISTEN_TIMEOUT_MS) {
    clearTimeout(v.listenTimer);
    v.listenTimer = setTimeout(async () => {
      if (v.mode !== 'listen' || v.busy) return;
      // Suhbat davomida hech narsa aytilmadi — jimgina yopiladi
      if (v.followUp && !v.capture?.hadSpeech) {
        closeOrb();
        return;
      }
      // Gapirildi, lekin brauzer hech narsa tanimadi — yozuv bo'lsa server taniydi
      if (v.capture?.hadSpeech && v.capture.recorder) {
        stopRecognition();
        const blob = await stopCapture();
        if (blob) {
          submitAudio(blob);
          return;
        }
      }
      // Telefonda parallel yozuv yo'q: gap eshitilgan bo'lishi mumkin — keyingi urinish server orqali
      if (serverStt() && isTouch && currentEngine() === 'browser' && !v.preferServer) {
        v.preferServer = true;
        stopRecognition();
        stopCapture(true);
        showReply('Eshitmadim. Qaytadan ayting.');
        listen();
        return;
      }
      closeOrb();
    }, ms);
  }

  // followUp — suhbat davomi: «Salom Moliya»siz qisqa tinglash (natija va ro'yxat ko'rinib turadi)
  function listen({ followUp = false } = {}) {
    openOrb();
    v.followUp = followUp;
    if (followUp) layer.dataset.follow = '1';
    else delete layer.dataset.follow;
    heardEl.textContent = '';
    setOrb('listen');
    const engine = currentEngine();
    if (engine === 'server') {
      // Gap tugashi ovoz balandligidan aniqlanadi (VAD), yozuv serverga yuboriladi
      stopRecognition();
      clearTimeout(v.listenTimer);
      startCapture({ record: true, vad: true, onDone: onServerUtterance });
    } else if (engine === 'browser') {
      startCapture({ record: canRecordParallel() });
      armListenTimeout(followUp ? FOLLOWUP_MS : LISTEN_TIMEOUT_MS);
      startRecognition('listen');
    } else {
      typeForm.hidden = false;
      typeInput.focus();
    }
  }

  function onServerUtterance(blob, hadSpeech, problem) {
    if (v.mode !== 'listen' || v.busy || layer.hidden) return;
    if (problem === 'denied') {
      heardEl.textContent = "Mikrofonga ruxsat yo'q — manzil satridagi qulf belgisidan yoqing yoki javobni yozing.";
      typeForm.hidden = false;
      typeInput.focus();
      return;
    }
    if (blob) submitAudio(blob);
    else if (!hadSpeech) closeOrb();
    else listen();  // juda qisqa — qayta tinglanadi
  }

  // Faqat «Salom Moliya» deyilsa: ism bilan javob beriladi va buyruq kutiladi
  function greetAndListen() {
    const name = state.currentUser?.first_name || state.currentUser?.username || '';
    const text = name ? `Ha, ${name}?` : 'Ha?';
    showReply(text);
    speak(text, () => {
      v.awaiting = true;
      armIdle();
      listen();
    });
  }

  // ---------- Ovozli javob ----------

  function loadVoices() {
    if (canSpeak) v.voices = speechSynthesis.getVoices();
  }
  if (canSpeak) {
    loadVoices();
    // Ovozlar ro'yxati kech keladi — sozlamalardagi "o'zbekcha ovoz bormi" holati yangilanadi
    speechSynthesis.addEventListener?.('voiceschanged', () => { loadVoices(); renderSettings(); });
  }

  // Server ovozi (mainapp/tts.py): Azure'ning o'zbek neyron ovozlari yoki OpenAI — ravon o'zbekcha talaffuz
  const serverTts = () => !!state.currentUser?.voice_server_tts;
  const voiceGender = () => (storageGetSafe(GENDER_KEY) === 'male' ? 'male' : 'female');

  // Brauzer ovozi (zaxira): o'zbekcha faqat Edge'da bor (Madina, Sardor). Bo'lmasa turkcha — lotin yozuvini yaqinroq o'qiydi
  function pickVoice() {
    const uz = v.voices.filter(x => x.lang?.toLowerCase().startsWith('uz'));
    const wanted = voiceGender() === 'male' ? /sardor|male|erkak/i : /madina|female|ayol/i;
    return uz.find(x => wanted.test(x.name)) || uz[0] || v.voices.find(x => x.lang?.toLowerCase().startsWith('tr')) || null;
  }

  function stopSpeaking() {
    v.speakSeq++;
    if (v.audioSource) {
      try { v.audioSource.stop(); } catch (e) { /* allaqachon tugagan */ }
      v.audioSource = null;
    }
    if (canSpeak) speechSynthesis.cancel();
  }

  function speak(text, onDone) {
    stopRecognition();  // yordamchi o'z ovozini buyruq deb eshitmasin
    stopCapture(true);
    stopSpeaking();
    if (!text) {
      onDone?.();
      return;
    }
    const seq = v.speakSeq;
    let finished = false;
    const stopBarge = () => {
      if (v.capture?.barge) stopCapture(true);
    };
    const finish = () => {
      if (finished || seq !== v.speakSeq) return;
      finished = true;
      clearTimeout(guard);
      stopBarge();
      onDone?.();
    };
    // Ba'zi brauzerlarda tugash hodisasi kelmay qoladi — zaxira taymer (server ovozini yuklash vaqti bilan)
    const guard = setTimeout(finish, Math.min(25000, (serverTts() ? 6000 : 1500) + text.length * 100));
    // Orb bosilsa: javob to'xtatiladi va keyingi qadamga (savol bo'lsa — tinglashga) darhol o'tiladi
    v.skipSpeech = () => {
      if (finished) return;
      finished = true;
      clearTimeout(guard);
      stopSpeaking();
      stopBarge();
      onDone?.();
    };
    setOrb('speak');
    // Foydalanuvchi gapirib yuborsa — javob shu zahoti to'xtaydi va uning gapi tinglanadi. Mikrofon oqimi allaqachon
    // ochiq bo'lsagina (javob o'qilayotganda kutilmagan ruxsat so'rovi chiqmasin)
    if (micStream?.active && !layer.hidden && currentEngine() !== 'type') {
      startCapture({
        onBarge: () => {
          if (finished || seq !== v.speakSeq) return;
          finished = true;
          clearTimeout(guard);
          stopSpeaking();
          stopBarge();
          if (!layer.hidden) listen();
        },
      });
    }
    if (serverTts()) {
      speakServer(text, seq, finish).catch(() => {
        if (seq === v.speakSeq) speakBrowser(text, finish);
      });
    } else {
      speakBrowser(text, finish);
    }
  }

  // Bir marta eshitilgan gap («Qancha sarfladingiz?», «Ha, Abdurahmon?») xotirada qoladi — keyingi safar serverga
  // so'rov ketmaydi va darhol yangraydi. Faqat shu varaq ochiq turguncha; ko'p xotira olmasin deb oxirgi AUDIO_CACHE_MAX ta
  const audioCache = new Map();
  const AUDIO_CACHE_MAX = 40;

  async function speakServer(text, seq, finish) {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    const key = `${voiceGender()}|${text}`;
    let buffer = audioCache.get(key);
    if (!buffer) {
      const res = await fetch(`${API_BASE}/voice/tts/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, voice: voiceGender() }),
      });
      if (!res.ok) throw new Error(`tts ${res.status}`);
      const data = await res.arrayBuffer();
      if (seq !== v.speakSeq) return;  // shu orada yopildi yoki yangi javob keldi
      buffer = await audioCtx.decodeAudioData(data);
      audioCache.set(key, buffer);
      if (audioCache.size > AUDIO_CACHE_MAX) audioCache.delete(audioCache.keys().next().value);
    }
    if (seq !== v.speakSeq) return;
    if (audioCtx.state === 'suspended') await audioCtx.resume();
    if (audioCtx.state !== 'running') throw new Error('audio blocked');
    if (seq !== v.speakSeq) return;
    const source = audioCtx.createBufferSource();
    source.buffer = buffer;
    source.connect(audioCtx.destination);
    source.onended = () => {
      if (v.audioSource === source) v.audioSource = null;
      finish();
    };
    v.audioSource = source;
    source.start();
  }

  function speakBrowser(text, finish) {
    if (!canSpeak) {
      finish();
      return;
    }
    const utter = new SpeechSynthesisUtterance(text);
    const voice = pickVoice();
    if (voice) utter.voice = voice;
    utter.lang = voice?.lang || 'uz-UZ';
    utter.rate = 1.0;
    utter.onend = finish;
    utter.onerror = finish;
    speechSynthesis.speak(utter);
  }

  // ---------- Serverga buyruq ----------

  async function postVoice(body, isJson) {
    const ctrl = new AbortController();
    v.abort = ctrl;
    try {
      const res = await fetch(`${API_BASE}/voice/`, {
        method: 'POST',
        headers: isJson ? { 'Content-Type': 'application/json' } : {},
        body,
        signal: ctrl.signal,
      });
      const data = await res.json().catch(() => null);
      if (res.ok && data) return data;
      const text = res.status === 429 ? "Juda ko'p buyruq berildi. Birozdan keyin urinib ko'ring." : (data?.error || 'Buyruq bajarilmadi.');
      return { status: 'error', text, say: text };
    } catch (e) {
      if (ctrl.signal.aborted) return { status: 'none', cancelled: true };
      return { status: 'error', text: NETWORK_ERROR_MESSAGE, say: "Serverga ulanib bo'lmadi." };
    } finally {
      if (v.abort === ctrl) v.abort = null;
    }
  }

  function takeFresh() {
    const fresh = v.fresh;
    v.fresh = false;
    return fresh;
  }

  // Orb javob kelguncha yopilgan bo'lsa: javob aytilmaydi, bo'lim ochilmaydi. Server amalni yozib ulgurgan
  // bo'lsa — u ham bekor qilinadi (foydalanuvchi buyruqni yopish bilan bekor qildi)
  async function dropLate(data) {
    const undoable = (data?.done || []).filter(d => d.type && d.id);
    if (undoable.length) await undo(undoable);
  }

  function startThinking(heard) {
    v.busy = true;
    clearTimeout(v.listenTimer);
    clearTimeout(v.closeTimer);
    openOrb();
    delete layer.dataset.follow;
    showHeard(heard);
    showReply('');
    renderItems([]);
    setOrb('think');
  }

  // Brauzer tanigan matn. Server tushunmasa (understood: false) — shu gapning yozuvi server orqali qayta taniladi:
  // xato odatda tanishda ("qirq besh" o'rniga "kirk besh"), buyruqning o'zida emas
  async function submit(text) {
    text = String(text || '').trim();
    if (!text || v.busy) return;
    v.awaiting = false;
    armIdle();
    const followUp = v.followUp;
    v.followUp = false;
    const audio = stopCapture();
    startThinking(text);
    const session = v.session;
    let data = await postVoice(JSON.stringify({ text, follow_up: followUp, fresh: takeFresh() }), true);
    if (session !== v.session) return dropLate(data);
    // Suhbat davomida tasodifiy gap (yonidagi odam bilan suhbat) — "Tushunmadim" deb gapirmasdan yopiladi
    if (followUp && data.understood === false) {
      v.busy = false;
      closeOrb();
      return;
    }
    if (data.understood === false && serverStt()) {
      const blob = await audio;
      if (session !== v.session) return;
      if (blob) {
        showReply("Aniqroq tanib ko'ryapman…");
        data = await postVoice(audioForm(blob), false);
        if (session !== v.session) return dropLate(data);
      } else {
        v.preferServer = true;  // yozuv yo'q (telefon) — javob server orqali tinglanadi
      }
    }
    v.busy = false;
    await handleResponse(data);
  }

  function audioForm(blob, followUp = false) {
    const ext = (blob.type.split('/')[1] || 'webm').split(';')[0];
    const form = new FormData();
    form.append('audio', blob, `voice.${ext}`);
    if (followUp) form.append('follow_up', 'true');
    if (takeFresh()) form.append('fresh', 'true');
    return form;
  }

  async function submitAudio(blob) {
    if (v.busy) return;
    v.awaiting = false;
    const followUp = v.followUp;
    v.followUp = false;
    startThinking('');
    showReply('Tanilmoqda…');
    const session = v.session;
    const data = await postVoice(audioForm(blob, followUp), false);
    if (session !== v.session) return dropLate(data);
    v.busy = false;
    if (followUp && (data.understood === false || data.heard === '')) {
      closeOrb();
      return;
    }
    await handleResponse(data);
  }

  // Javobdan keyin: suhbat rejimi yoqilgan bo'lsa qisqa tinglash, aks holda orb yopiladi
  function afterTurn(closeMs) {
    if (v.conversation && !layer.hidden && currentEngine() !== 'type') {
      v.awaiting = true;
      armIdle();
      clearTimeout(v.closeTimer);
      v.closeTimer = setTimeout(() => {
        if (!layer.hidden && !v.busy && (v.mode === 'done' || v.mode === 'speak' || v.mode === 'error')) listen({ followUp: true });
      }, FOLLOWUP_DELAY_MS);
    } else {
      closeLater(closeMs);
    }
  }

  async function handleResponse(data) {
    // Server ovozdan biror gap tanidi — bu haqiqiy suhbat (bo'sh «Eshitmadim» aylanasi emas)
    if (data.heard || data.status === 'done') armIdle();
    if (typeof data.heard === 'string' && data.heard) showHeard(data.heard);
    renderItems(data.items);
    if (data.done?.length) remember(data.done);
    if (data.refresh) refreshAll();
    if (data.client) data.text = (await runClientAction(data.client)) || data.text;
    // «Yop» buyrug'i orbni yopdi — javob endi ko'rsatilmaydi va aytilmaydi
    if (data.client?.action === 'close' && layer.hidden) return;

    if (data.status === 'none') {
      closeOrb();
      return;
    }
    if (data.status === 'done') {
      showReply(data.text, 'done');
      setOrb('done');
      chime('done');
      const undoable = (data.done || []).filter(d => d.type && d.id);
      if (undoable.length) {
        showToast(data.text, 'success', { action: { label: 'Bekor qilish', onClick: () => undo(undoable) } });
      }
      if (data.end) closeLater();
      else afterTurn();
      return;
    }

    const kind = data.status === 'error' ? 'error' : '';
    // Tushunilmadi (ovoz yozuvi ham qayta tanitib ko'rilgan) yoki ilovaga aloqasiz savol — qayta tinglanmaydi
    const unknown = data.status === 'reply' && (data.off_topic || data.understood === false);
    showReply(data.text, kind);
    if (kind) chime('error');
    const shownAt = Date.now();
    speak(data.say || data.text, () => {
      if (unknown) {
        // Javob chiqqanidan UNKNOWN_CLOSE_MS o'tib yopiladi; ovozda o'qish uzoqroq bo'lsa — gap tugashi bilan
        setOrb('done');
        closeLater(Math.max(0, UNKNOWN_CLOSE_MS - (Date.now() - shownAt)));
      } else if (data.expect_reply) {
        v.awaiting = true;
        armIdle();
        listen();
      }
      else {
        setOrb(kind ? 'error' : 'done');
        if (data.end) closeLater(2600);
        else afterTurn(kind ? 3500 : 2600);
      }
    });
  }

  // ---------- Bekor qilish (oxirgi ovozli amallar) ----------

  function remember(done) {
    const items = done.filter(d => d.type && d.id);
    if (!items.length) return;
    v.lastDone.push(items);
    if (v.lastDone.length > MAX_UNDO) v.lastDone.shift();
  }

  async function undo(items) {
    const batch = items || v.lastDone.pop();
    if (!batch?.length) {
      showReply("Bekor qiladigan amal yo'q.");
      return false;
    }
    if (items) v.lastDone = v.lastDone.filter(b => b !== items && !b.every(x => items.some(y => y.type === x.type && y.id === x.id)));
    let ok = true;
    let message = '';
    for (const item of [...batch].reverse()) {
      try {
        const res = await fetch(`${API_BASE}/${item.type}/${item.id}/`, { method: 'DELETE' });
        if (!res.ok) {
          ok = false;
          message = (await res.json().catch(() => ({}))).error || '';
        }
      } catch (e) {
        ok = false;
        message = NETWORK_ERROR_MESSAGE;
      }
    }
    refreshAll();
    showToast(ok ? 'Bekor qilindi, qoldiq qaytarildi' : (message || "Bekor qilib bo'lmadi"), ok ? 'success' : 'error');
    return ok;
  }

  // ---------- Ilova ichidagi amallar (bo'lim ochish, mavzu, bekor qilish) ----------
  // Orbda ko'rsatiladigan matnni qaytarishi mumkin (masalan bekor qilish natijasi)

  async function runClientAction(action) {
    switch (action.action) {
      case 'navigate':
        navigate(action.target);
        break;
      case 'theme':
        setTheme(action.value);
        break;
      case 'balance':
        if ((action.value === 'hide') !== balanceHidden) $('btnToggleBalance')?.click();
        break;
      case 'undo':
        return (await undo()) ? 'Oxirgi amal bekor qilindi' : "Bekor qiladigan amal yo'q";
      case 'close':
        closeOrb();
        break;
    }
  }

  function navigate(target) {
    const settingsOpen = $('modalSettings')?.classList.contains('active');
    if (settingsOpen && target !== 'settings' && target !== 'help') closeModal('modalSettings');
    switch (target) {
      case 'stats': openTxPage('stats'); break;
      case 'incomes': openTxPage('transactions', 'incomes'); break;
      case 'expenses': openTxPage('transactions', 'expenses'); break;
      case 'debts': openDebtsPage(); break;
      case 'rates': openRatesPage(); break;
      case 'wallets': openWalletsPage(); break;
      case 'settings': openSettings(); break;
      case 'help': openSettings(); switchSettingsTab('help'); break;
      case 'home': closeTxPage(); break;
    }
  }

  // ---------- Yoqish / o'chirish ----------

  function setWake(on, { silent = false } = {}) {
    v.wake = !!on;
    storageSetSafe(WAKE_KEY, v.wake ? '1' : '0');
    if (wakeActive() && layer.hidden) startRecognition('wake');
    if (!v.wake && v.recMode === 'wake') stopRecognition();
    if (wakeActive()) holdMicForWake();
    else if (layer.hidden) releaseMicLater();
    setOrb(layer.hidden ? (wakeActive() ? 'wake' : 'off') : v.mode);
    if (!silent) showToast(v.wake ? `«Salom ${BRAND}» yoqildi — endi ovoz bilan chaqirishingiz mumkin` : `«Salom ${BRAND}» o'chirildi`);
    renderSettings();
  }

  // Fonda tinglash: foydalanuvchi yoqgan (standart) va mikrofonga ruxsat bergan bo'lsa
  function wakeActive() {
    return v.wake && v.started && v.micAllowed && (canListen || serverWake());
  }

  function beginWake() {
    v.micAllowed = true;
    if (!wakeActive()) return;
    if (layer.hidden) {
      startRecognition('wake');
      holdMicForWake();
      setOrb('wake');
    }
    renderSettings();
  }

  // Ruxsat allaqachon berilgan bo'lsa darhol tinglanadi; bo'lmasa — bir marta tugmali xabar bilan taklif qilinadi
  // (ruxsat oynasi foydalanuvchi bosgandagina chiqadi: sahifa ochilishi bilan kutilmagan so'rov chiqmasin)
  async function checkMicPermission() {
    let state = 'prompt';
    try {
      state = (await navigator.permissions.query({ name: 'microphone' })).state;
    } catch (e) { /* Safari/Firefox: so'rov API yo'q — taklif ko'rsatiladi */ }
    v.micDenied = state === 'denied';
    if (state === 'granted') beginWake();
    else if (state === 'prompt') offerWake();
    renderSettings();
  }

  const OFFER_KEY = 'moliyaVoiceWakeOffered';
  const OFFER_EVERY_MS = 3 * 24 * 3600 * 1000;  // rad etilsa — 3 kundan keyin yana eslatiladi

  function offerWake() {
    const last = Number(storageGetSafe(OFFER_KEY) || 0);
    if (Date.now() - last < OFFER_EVERY_MS) return;
    storageSetSafe(OFFER_KEY, String(Date.now()));
    showToast(`«Salom ${BRAND}» deb chaqirish uchun mikrofonga ruxsat bering`, 'success', {
      duration: 15000,
      action: { label: 'Ruxsat berish', onClick: () => askMic(true) },
    });
  }

  // Mikrofon ruxsati so'raladi (foydalanuvchi bosganda). Berilsa — «Salom Moliya» darhol ishlaydi
  async function askMic(announce) {
    try {
      await acquireMic();
    } catch (e) {
      showToast("Mikrofonga ruxsat berilmadi. Brauzer sozlamalarida mikrofonni yoqing.", 'error');
      renderSettings();
      return false;
    }
    v.micAllowed = true;
    if (!v.wake) setWake(true, { silent: true });
    beginWake();
    if (announce) showToast(`Tayyor! Endi «Salom ${BRAND}» deng`);
    return true;
  }

  // Kirgandan keyin (app.js: checkAuth) ishga tushadi; chiqishda sahifa qayta yuklanadi
  function start() {
    if (v.started) return;
    v.started = true;
    if (navBtn) navBtn.style.display = '';
    setOrb('off');
    if (v.wake && (canListen || serverStt())) checkMicPermission();
  }

  function stop() {
    v.started = false;
    if (navBtn) navBtn.style.display = 'none';
    stopRecognition();
    if (!layer.hidden) closeOrb();
    releaseMicNow();
  }

  // Yashirin varaqda brauzer mikrofonni baribir to'xtatadi; qaytganda qayta tinglanadi
  document.addEventListener('visibilitychange', () => {
    if (!v.started) return;
    if (document.hidden) {
      stopRecognition();
      // Boshqa varaqda mikrofon band qolmasin (brauzer belgisi ham o'chadi)
      if (layer.hidden) releaseMicNow();
    } else if (layer.hidden && wakeActive()) {
      startRecognition('wake');
      holdMicForWake();
    }
  });

  function toggleOrb() {
    if (!state.currentUser) return;
    if (!layer.hidden) closeOrb();
    else {
      listen();
      chime('listen');
    }
  }

  // ---------- Sozlamalar → Ovozli yordamchi ----------

  function renderSettings() {
    const toggle = $('voiceWakeToggle');
    const status = $('voiceSupportStatus');
    if (!toggle || !status) return;
    const convo = $('voiceConversationToggle');
    if (convo) convo.checked = v.conversation;
    const gender = voiceGender();
    document.querySelectorAll('[data-voice-gender]').forEach(btn => {
      const on = btn.dataset.voiceGender === gender;
      btn.classList.toggle('active', on);
      btn.setAttribute('aria-checked', on ? 'true' : 'false');
    });
    const ttsStatus = $('voiceTtsStatus');
    if (ttsStatus) {
      const hasUzVoice = v.voices.some(x => x.lang?.toLowerCase().startsWith('uz'));
      if (serverTts()) {
        ttsStatus.textContent = ['azure', 'voicelab'].includes(state.currentUser.voice_server_tts)
          ? "Javoblar haqiqiy o'zbekcha ovozda o'qiladi."
          : "Javoblar server ovozida o'qiladi. Ona tilidagidek ravon ovoz uchun administrator Azure Speech kalitini qo'shishi mumkin.";
        ttsStatus.className = 'settings-account-hint voice-status';
      } else if (hasUzVoice) {
        ttsStatus.textContent = "Javoblar brauzerning o'zbekcha ovozida o'qiladi.";
        ttsStatus.className = 'settings-account-hint voice-status';
      } else {
        ttsStatus.textContent = "Bu brauzerda o'zbekcha ovoz yo'q — javob boshqa tildagi ovozda o'qiladi va g'alati eshitilishi mumkin. Edge brauzerida oching yoki administrator server ovozini (Azure Speech) yoqsin.";
        ttsStatus.className = 'settings-account-hint voice-status is-warn';
      }
    }
    toggle.checked = v.wake;
    toggle.disabled = !canListen && !serverStt();
    const server = serverStt() ? ' Brauzer tanimasa — ovoz server orqali aniqroq taniladi.' : '';
    if (serverWake()) {
      status.textContent = v.wake && v.micAllowed
        ? `Yoqilgan: ilova ochiq turganda «Salom ${BRAND}» deyishingiz kifoya. Bu qurilmada gaplaringiz tanish uchun serverga yuboriladi.`
        : `Bu qurilmada «Salom ${BRAND}» server orqali eshitiladi: mikrofonga ruxsat bering. Mikrofon tugmasi ham ishlaydi.`;
      status.className = 'settings-account-hint voice-status';
    } else if (!canListen) {
      status.textContent = "Bu brauzer ovozni tanimaydi. Chrome, Edge yoki Safari'da oching — bu yerda esa buyruqni yozib yuborishingiz mumkin.";
      status.className = 'settings-account-hint voice-status is-warn';
    } else if (!window.isSecureContext) {
      status.textContent = "Mikrofon faqat xavfsiz (https://) manzilda ishlaydi.";
      status.className = 'settings-account-hint voice-status is-warn';
    } else {
      status.textContent = v.wake && v.micDenied && !v.micAllowed
        ? `Mikrofon brauzerda bloklangan — manzil satridagi qulf belgisidan mikrofonga ruxsat bering, so'ng sahifani yangilang.`
        : v.wake && !v.micAllowed
        ? `Yoqilgan, lekin mikrofonga ruxsat kerak — tugmani o'chirib-yoqing yoki mikrofon tugmasini bosing.`
        : v.wake
        ? `Yoqilgan: ilova ochiq turganda «Salom ${BRAND}» deyishingiz kifoya.`
        : `O'chiq. Mikrofon tugmasi yoki Alt + M bilan chaqirish mumkin.`;
      status.textContent += server;
      status.className = 'settings-account-hint voice-status';
    }
  }

  $('voiceWakeToggle')?.addEventListener('change', (e) => {
    const on = e.target.checked;
    if (!on) {
      setWake(false);
      return;
    }
    // Ruxsat oynasi foydalanuvchi bosganda chiqadi — keyin fonda tinglash shu ruxsat bilan ishlaydi
    askMic(false).then(ok => {
      if (ok) setWake(true);
      else e.target.checked = false;
    });
  });

  $('voiceConversationToggle')?.addEventListener('change', (e) => {
    v.conversation = e.target.checked;
    storageSetSafe(CONVO_KEY, v.conversation ? '1' : '0');
  });

  // Yordamchi ovozi: tanlansa namunaviy gap shu ovozda o'qiladi
  document.querySelectorAll('[data-voice-gender]').forEach(btn => btn.addEventListener('click', () => {
    storageSetSafe(GENDER_KEY, btn.dataset.voiceGender);
    renderSettings();
    const name = state.currentUser?.first_name || '';
    speak(`Assalomu alaykum${name ? `, ${name}` : ''}! Men ${BRAND} yordamchisiman. Buyruqlaringizni kutaman.`,
      () => setOrb(layer.hidden ? (wakeActive() ? 'wake' : 'off') : v.mode));
  }));

  $('btnVoiceTry')?.addEventListener('click', () => {
    closeModal('modalSettings');
    listen();
    chime('listen');
  });

  // ---------- Hodisalar ----------

  orb.addEventListener('click', () => {
    if (v.mode === 'listen' && v.capture?.vad) {
      // Server orqali tinglanmoqda: bosilsa — gap tugadi, yozuv darhol yuboriladi
      finishCapture(v.capture);
    } else if (v.mode === 'listen') {
      // Gapirib bo'lingan bo'lsa — eshitilgan matn darhol yuboriladi
      // Faqat tanilgan gap «...» ichida turadi; ruxsat yo'q kabi ogohlantirish buyruq sifatida yuborilmasin
      const text = (heardEl.textContent.match(/^«([\s\S]*)»$/) || [, ''])[1].trim();
      if (text) { stopRecognition(); submit(text); }
      else closeOrb();
    } else if (v.mode === 'speak') {
      v.skipSpeech?.();
    } else if (v.mode !== 'think') {
      listen();
    }
  });
  $('voiceClose')?.addEventListener('click', closeOrb);
  navBtn?.addEventListener('click', toggleOrb);

  // Yordamchi ochiq turganda sahifa ustida ko'rinmas parda turadi (CSS: .voice-backdrop): istalgan joyga tegilsa
  // faqat yordamchi yopiladi — ostidagi bo'lim ochilmaydi, sichqoncha ostidagi kartochkalar hover'da yonmaydi
  $('voiceBackdrop')?.addEventListener('click', closeOrb);

  typeInput.addEventListener('input', armIdle);

  typeForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = typeInput.value.trim();
    if (!text) return;
    typeInput.value = '';
    stopRecognition();
    stopCapture(true);
    submit(text);
  });

  // "Yozish" tugmasi: ovoz tanilmasa yoki shovqinli joyda buyruqni yozib yuborish
  $('voiceTypeToggle')?.addEventListener('click', () => {
    typeForm.hidden = !typeForm.hidden;
    if (!typeForm.hidden) {
      stopRecognition();
      stopCapture(true);
      clearTimeout(v.listenTimer);
      typeInput.focus();
    }
  });

  document.addEventListener('keydown', (e) => {
    if (e.altKey && !e.ctrlKey && !e.metaKey && (e.code === 'KeyM')) {
      e.preventDefault();
      toggleOrb();
      return;
    }
    if (e.key === 'Escape' && !layer.hidden) {
      e.preventDefault();
      e.stopPropagation();
      closeOrb();
    }
  }, true);

  setOrb('off');
  window.moliyaVoice = { start, stop, renderSettings, submit, listen, close: closeOrb, findWake };
})();
