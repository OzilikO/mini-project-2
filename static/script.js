/**
 * Voice-Activated Library Management System - Frontend Controller
 * EE 471 Mini Project #2.
 * Connects directly to Flask REST API and Azure Speech Voice Services.
 */

// Application State
let libraryItems = [];
let currentTypeFilter = 'all';
let availableOnly = false;
let editingItemId = null;
let lastAudioUrl = null;
let librarianBannerTimeout = null;

// DOM Elements
const itemsGrid = document.getElementById('itemsGrid');
const emptyState = document.getElementById('emptyState');
const itemsCount = document.getElementById('itemsCount');
const availableToggle = document.getElementById('availableToggle');
const segmentBtns = document.querySelectorAll('.segment-btn');

// Alert Banner (Manual REST actions)
const alertBanner = document.getElementById('alertBanner');
const alertMessage = document.getElementById('alertMessage');
const dismissAlertBtn = document.getElementById('dismissAlertBtn');

// Modal Elements
const openAddModalBtn = document.getElementById('openAddModalBtn');
const emptyAddBtn = document.getElementById('emptyAddBtn');
const itemModal = document.getElementById('itemModal');
const closeModalBtn = document.getElementById('closeModalBtn');
const cancelModalBtn = document.getElementById('cancelModalBtn');
const itemForm = document.getElementById('itemForm');
const modalTitle = document.getElementById('modalTitle');
const modalItemId = document.getElementById('modalItemId');
const itemTitleInput = document.getElementById('itemTitleInput');
const itemAuthorInput = document.getElementById('itemAuthorInput');
const itemTypeSelect = document.getElementById('itemTypeSelect');
const dynamicFieldLabel = document.getElementById('dynamicFieldLabel');
const itemDynamicInput = document.getElementById('itemDynamicInput');

// Voice UI Elements
const voicePanel = document.getElementById('voicePanel');
const micBtn = document.getElementById('micBtn');
const voiceStatusBadge = document.getElementById('voiceStatusBadge');
const voiceStatusDetail = document.getElementById('voiceStatusDetail');
const voiceTranscript = document.getElementById('voiceTranscript');
const voiceTextInput = document.getElementById('voiceTextInput');
const voiceSendBtn = document.getElementById('voiceSendBtn');
const librarianAudioPlayer = document.getElementById('librarianAudioPlayer');

// Librarian Bottom Response Banner
const librarianBanner = document.getElementById('librarianBanner');
const librarianSpokenText = document.getElementById('librarianSpokenText');
const librarianReplayBtn = document.getElementById('librarianReplayBtn');
const dismissLibrarianBtn = document.getElementById('dismissLibrarianBtn');

// ==========================================================================
// 1. WAV Audio Recorder for Microphone Input (16-bit PCM WAV for Azure)
// ==========================================================================
class WavAudioRecorder {
  constructor() {
    this.audioContext = null;
    this.mediaStream = null;
    this.processorNode = null;
    this.audioInputNode = null;
    this.chunks = [];
    this.isRecording = false;
  }

  async start() {
    this.chunks = [];
    this.mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true
      }
    });
    this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    this.audioInputNode = this.audioContext.createMediaStreamSource(this.mediaStream);

    // Buffer size 4096, 1 input channel, 1 output channel
    this.processorNode = this.audioContext.createScriptProcessor(4096, 1, 1);
    this.processorNode.onaudioprocess = (e) => {
      if (!this.isRecording) return;
      const channelData = e.inputBuffer.getChannelData(0);
      this.chunks.push(new Float32Array(channelData));
    };

    this.audioInputNode.connect(this.processorNode);
    this.processorNode.connect(this.audioContext.destination);
    this.isRecording = true;
  }

  stop() {
    this.isRecording = false;
    if (this.processorNode) this.processorNode.disconnect();
    if (this.audioInputNode) this.audioInputNode.disconnect();
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
    }

    let totalLength = 0;
    for (const chunk of this.chunks) totalLength += chunk.length;
    const merged = new Float32Array(totalLength);
    let offset = 0;
    for (const chunk of this.chunks) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }

    const sampleRate = this.audioContext ? this.audioContext.sampleRate : 44100;
    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close();
    }

    return this.encodeWAV(merged, sampleRate);
  }

  encodeWAV(samples, sampleRate) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    function writeStr(offset, str) {
      for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
    }

    writeStr(0, 'RIFF');
    view.setUint32(4, 36 + samples.length * 2, true);
    writeStr(8, 'WAVE');
    writeStr(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true); // PCM format
    view.setUint16(22, 1, true); // Mono
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true); // 16 bits
    writeStr(36, 'data');
    view.setUint32(40, samples.length * 2, true);

    let offset = 44;
    for (let i = 0; i < samples.length; i++, offset += 2) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }

    return new Blob([view], { type: 'audio/wav' });
  }
}

const audioRecorder = new WavAudioRecorder();
let isRecordingActive = false;

// ==========================================================================
// 2. Audio Playback & Librarian Response Banner
// ==========================================================================
function playLibrarianAudio(url) {
  if (!url) return;
  lastAudioUrl = url;
  librarianAudioPlayer.src = url;
  librarianAudioPlayer.play().catch((err) => {
    console.warn('Audio auto-play prevented by browser policy:', err);
  });
}

function showLibrarianBanner(spokenMessage, isSuccess = true, audioUrl = null) {
  if (!spokenMessage) return;

  if (librarianBannerTimeout) {
    clearTimeout(librarianBannerTimeout);
  }

  librarianSpokenText.textContent = spokenMessage;
  librarianBanner.classList.toggle('error', !isSuccess);
  librarianBanner.style.display = 'block';

  if (audioUrl) {
    playLibrarianAudio(audioUrl);
  }

  // Auto-dismiss after 9 seconds
  librarianBannerTimeout = setTimeout(() => {
    hideLibrarianBanner();
  }, 9000);
}

function hideLibrarianBanner() {
  librarianBanner.style.display = 'none';
  if (librarianBannerTimeout) {
    clearTimeout(librarianBannerTimeout);
    librarianBannerTimeout = null;
  }
}

if (dismissLibrarianBtn) {
  dismissLibrarianBtn.addEventListener('click', hideLibrarianBanner);
}

if (librarianReplayBtn) {
  librarianReplayBtn.addEventListener('click', () => {
    if (lastAudioUrl) {
      librarianAudioPlayer.currentTime = 0;
      librarianAudioPlayer.play().catch((e) => console.log(e));
    }
  });
}

// ==========================================================================
// 3. Microphone & Voice Command Interaction
// ==========================================================================
async function startRecording() {
  try {
    await audioRecorder.start();
    isRecordingActive = true;

    // UI Updates
    micBtn.classList.add('recording');
    voicePanel.classList.add('recording');
    voicePanel.classList.remove('processing');
    voiceStatusBadge.className = 'voice-status-badge listening';
    voiceStatusBadge.textContent = 'Listening...';
    voiceStatusDetail.textContent = 'Speak your library command now...';
    voiceTranscript.textContent = "Listening... Try: 'Create item, type book...' or 'Check out item 3'";
  } catch (err) {
    console.error('Mic access error:', err);
    showAlert('Could not access microphone: ' + err.message);
  }
}

async function stopRecordingAndSubmit() {
  if (!isRecordingActive) return;
  isRecordingActive = false;

  // Set processing state
  micBtn.classList.remove('recording');
  micBtn.classList.add('processing');
  voicePanel.classList.remove('recording');
  voicePanel.classList.add('processing');
  voiceStatusBadge.className = 'voice-status-badge processing';
  voiceStatusBadge.textContent = 'Processing...';
  voiceStatusDetail.textContent = 'Azure Speech is transcribing and running action...';

  const audioBlob = audioRecorder.stop();
  await sendVoiceAudio(audioBlob);
}

async function sendVoiceAudio(blob) {
  try {
    const formData = new FormData();
    formData.append('audio', blob, 'command.wav');

    const res = await fetch('/api/voice-command', {
      method: 'POST',
      body: formData
    });

    const data = await res.json();
    handleVoiceResponse(res.ok, data);
  } catch (err) {
    console.error('Voice command error:', err);
    resetVoiceUI('Connection error: ' + err.message);
    showAlert('Failed to connect to voice endpoint: ' + err.message);
  }
}

async function sendVoiceText(text) {
  if (!text || !text.trim()) return;

  micBtn.classList.add('processing');
  voicePanel.classList.add('processing');
  voiceStatusBadge.className = 'voice-status-badge processing';
  voiceStatusBadge.textContent = 'Processing...';
  voiceStatusDetail.textContent = 'Executing command with Azure Speech...';
  voiceTranscript.textContent = `"${text}"`;

  try {
    const res = await fetch('/api/voice-command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text.trim() })
    });

    const data = await res.json();
    handleVoiceResponse(res.ok, data);
  } catch (err) {
    console.error('Voice simulation error:', err);
    resetVoiceUI('Error: ' + err.message);
    showAlert(err.message);
  }
}

function handleVoiceResponse(isHttpOk, data) {
  resetVoiceUI();

  if (!isHttpOk || data.error) {
    const errMsg = data.error || 'Voice command failed.';
    voiceTranscript.textContent = `Error: ${errMsg}`;
    showAlert(errMsg);
    showLibrarianBanner(errMsg, false);
    return;
  }

  // Update transcript display
  const recognized = data.recognized_text || 'Spoken Command';
  voiceTranscript.textContent = `"${recognized}"`;

  // Spoken feedback
  showLibrarianBanner(data.spoken_response, data.action_success, data.audio_url);

  // Apply action-specific DOM updates without full page refresh
  const action = data.action;

  if (action === 'create' && data.data && data.data.created_item) {
    const createdItem = data.data.created_item;
    // Visually pop the form modal briefly to show user verification
    popCreateVerification(createdItem);
    // Refresh catalog and highlight the new card
    fetchItems(createdItem.id);
  } else if (action === 'checkout' || action === 'return' || action === 'delete') {
    fetchItems(data.data ? data.data.item_id : null);
  } else if (action === 'list' && data.data && data.data.filter) {
    // Synchronize filters in toolbar
    const filter = data.data.filter;
    if (filter.available !== undefined && filter.available !== null) {
      availableOnly = filter.available;
      availableToggle.checked = availableOnly;
    } else {
      availableOnly = false;
      availableToggle.checked = false;
    }

    if (filter.type) {
      currentTypeFilter = filter.type;
    } else {
      currentTypeFilter = 'all';
    }

    segmentBtns.forEach((btn) => {
      btn.classList.toggle('active', btn.getAttribute('data-type') === currentTypeFilter);
    });

    if (data.data.items) {
      libraryItems = data.data.items;
      renderItems();
    } else {
      fetchItems();
    }
  } else {
    fetchItems();
  }
}

function popCreateVerification(item) {
  modalTitle.textContent = 'Voice Created Item';
  itemTitleInput.value = item.title || '';
  itemAuthorInput.value = item.author || '';
  itemTypeSelect.value = item.type || 'book';
  updateDynamicField(item.type, item.type === 'book' ? item.page_count : item.duration);
  modalItemId.value = item.id || '';

  // Pop modal
  itemModal.style.display = 'flex';

  // Automatically unpop after 1.8 seconds
  setTimeout(() => {
    closeModal();
  }, 1800);
}

function resetVoiceUI(customDetail = null) {
  micBtn.classList.remove('recording', 'processing');
  voicePanel.classList.remove('recording', 'processing');
  voiceStatusBadge.className = 'voice-status-badge idle';
  voiceStatusBadge.textContent = 'Ready';
  voiceStatusDetail.textContent = customDetail || 'Click mic or hold to speak';
}

// Mic Button Click / Toggle Handler
micBtn.addEventListener('click', async () => {
  if (!isRecordingActive) {
    await startRecording();
  } else {
    await stopRecordingAndSubmit();
  }
});

// Fallback Text Input & Send Button
if (voiceSendBtn && voiceTextInput) {
  voiceSendBtn.addEventListener('click', () => {
    const text = voiceTextInput.value.trim();
    if (text) {
      sendVoiceText(text);
      voiceTextInput.value = '';
    }
  });

  voiceTextInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const text = voiceTextInput.value.trim();
      if (text) {
        sendVoiceText(text);
        voiceTextInput.value = '';
      }
    }
  });
}

// Quick Command Chips
document.querySelectorAll('.quick-chip').forEach((chip) => {
  chip.addEventListener('click', () => {
    const cmd = chip.getAttribute('data-cmd');
    if (cmd) {
      sendVoiceText(cmd);
    }
  });
});

// ==========================================================================
// 4. REST Error Alert & Dynamic Field Helpers
// ==========================================================================
function showAlert(message) {
  alertMessage.textContent = message || 'An unexpected error occurred.';
  alertBanner.style.display = 'flex';
}

function hideAlert() {
  alertBanner.style.display = 'none';
}

if (dismissAlertBtn) {
  dismissAlertBtn.addEventListener('click', hideAlert);
}

function updateDynamicField(type, value = '') {
  if (type === 'dvd') {
    dynamicFieldLabel.textContent = 'Duration (mins)';
    itemDynamicInput.placeholder = '148';
  } else {
    dynamicFieldLabel.textContent = 'Page Count';
    itemDynamicInput.placeholder = '220';
  }
  itemDynamicInput.value = value !== undefined && value !== null ? value : '';
}

// ==========================================================================
// 5. REST API CRUD Operations
// ==========================================================================
async function fetchItems(highlightId = null) {
  try {
    const params = new URLSearchParams();
    if (availableOnly) {
      params.append('available', 'true');
    }
    if (currentTypeFilter !== 'all') {
      params.append('type', currentTypeFilter);
    }

    const queryString = params.toString() ? `?${params.toString()}` : '';
    const response = await fetch(`/api/items${queryString}`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Failed to load items.');
    }

    libraryItems = data;
    renderItems(highlightId);
  } catch (err) {
    showAlert(err.message);
  }
}

async function handleCheckout(itemId) {
  try {
    const res = await fetch(`/api/items/${itemId}/checkout`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || 'Checkout failed.');
    }
    hideAlert();
    fetchItems(itemId);
  } catch (err) {
    showAlert(err.message);
  }
}

async function handleReturn(itemId) {
  try {
    const res = await fetch(`/api/items/${itemId}/return`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || 'Return failed.');
    }
    hideAlert();
    fetchItems(itemId);
  } catch (err) {
    showAlert(err.message);
  }
}

async function handleDelete(itemId) {
  try {
    const res = await fetch(`/api/items/${itemId}`, { method: 'DELETE' });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.error || 'Delete failed.');
    }
    hideAlert();
    fetchItems();
  } catch (err) {
    showAlert(err.message);
  }
}

function openEditModal(item) {
  editingItemId = item.id;
  modalTitle.textContent = 'Edit Item';
  modalItemId.value = item.id;
  itemTitleInput.value = item.title;
  itemAuthorInput.value = item.author;
  itemTypeSelect.value = item.type;
  itemTypeSelect.disabled = true; // Item type is immutable
  updateDynamicField(item.type, item.type === 'book' ? item.page_count : item.duration);
  itemModal.style.display = 'flex';
}

function openAddModal() {
  editingItemId = null;
  modalTitle.textContent = 'Add New Item';
  modalItemId.value = '';
  itemForm.reset();
  itemTypeSelect.value = 'book';
  itemTypeSelect.disabled = false;
  updateDynamicField('book');
  itemModal.style.display = 'flex';
}

function closeModal() {
  itemModal.style.display = 'none';
  itemForm.reset();
  editingItemId = null;
  itemTypeSelect.disabled = false;
}

// Form Submit (Manual Create / Update)
itemForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  hideAlert();

  const title = itemTitleInput.value.trim();
  const author = itemAuthorInput.value.trim();
  const type = itemTypeSelect.value;
  const dynamicVal = itemDynamicInput.value.trim();

  if (!title || !author) {
    showAlert('Title and Author are required.');
    return;
  }

  const payload = { title, author, type };
  if (type === 'book') {
    const pages = parseInt(dynamicVal, 10);
    if (isNaN(pages) || pages <= 0) {
      showAlert('Page count must be a positive number.');
      return;
    }
    payload.page_count = pages;
  } else {
    payload.duration = dynamicVal;
  }

  try {
    let res;
    if (editingItemId) {
      res = await fetch(`/api/items/${editingItemId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    } else {
      res = await fetch('/api/items', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    }

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || 'Failed to save item.');
    }

    closeModal();
    fetchItems(data.id);
  } catch (err) {
    showAlert(err.message);
  }
});

// ==========================================================================
// 6. Grid Rendering
// ==========================================================================
function renderItems(highlightId = null) {
  itemsGrid.innerHTML = '';
  itemsCount.textContent = `${libraryItems.length} item${libraryItems.length === 1 ? '' : 's'}`;

  if (libraryItems.length === 0) {
    emptyState.style.display = 'flex';
    itemsGrid.style.display = 'none';
    return;
  }

  emptyState.style.display = 'none';
  itemsGrid.style.display = 'grid';

  libraryItems.forEach((item) => {
    const card = document.createElement('article');
    card.className = `item-card ${item.id === highlightId ? 'highlight' : ''}`;
    card.setAttribute('data-id', item.id);

    const isAvailable = item.is_available;
    const detailLabel = item.type === 'book'
      ? `${item.page_count || 0} pages`
      : `${item.duration || 0} mins`;

    card.innerHTML = `
      <div class="card-top-row">
        <span class="type-pill">${item.type}</span>
        <span class="card-id">#${item.id}</span>
      </div>

      <h3 class="card-title">${escapeHtml(item.title)}</h3>
      <p class="card-author">${escapeHtml(item.author)}</p>

      <div class="card-meta-row">
        <span class="detail-text">${detailLabel}</span>
      </div>

      <div class="status-badge ${isAvailable ? 'available' : 'checked-out'}">
        <span class="status-dot"></span>
        <span>${isAvailable ? 'Available' : 'Checked Out'}</span>
      </div>

      <div class="card-actions">
        ${
          isAvailable
            ? `<button type="button" class="btn btn-checkout" data-action="checkout" data-id="${item.id}">Checkout</button>`
            : `<button type="button" class="btn btn-return" data-action="return" data-id="${item.id}">Return</button>`
        }
        <div class="icon-actions">
          <button type="button" class="btn-icon-action" data-action="edit" data-id="${item.id}" title="Edit Item" aria-label="Edit Item">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
            </svg>
          </button>
          <button type="button" class="btn-icon-action btn-icon-delete" data-action="delete" data-id="${item.id}" title="Delete Item" aria-label="Delete Item">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
        </div>
      </div>
    `;

    itemsGrid.appendChild(card);
  });
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// Card Action Delegation
itemsGrid.addEventListener('click', (e) => {
  const btn = e.target.closest('button');
  if (!btn) return;

  const action = btn.getAttribute('data-action');
  const id = parseInt(btn.getAttribute('data-id'), 10);
  if (!id) return;

  if (action === 'checkout') {
    handleCheckout(id);
  } else if (action === 'return') {
    handleReturn(id);
  } else if (action === 'delete') {
    handleDelete(id);
  } else if (action === 'edit') {
    const item = libraryItems.find((it) => it.id === id);
    if (item) openEditModal(item);
  }
});

// ==========================================================================
// 7. Event Listeners & Initialization
// ==========================================================================
availableToggle.addEventListener('change', () => {
  availableOnly = availableToggle.checked;
  fetchItems();
});

segmentBtns.forEach((btn) => {
  btn.addEventListener('click', () => {
    segmentBtns.forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    currentTypeFilter = btn.getAttribute('data-type');
    fetchItems();
  });
});

itemTypeSelect.addEventListener('change', () => {
  updateDynamicField(itemTypeSelect.value);
});

openAddModalBtn.addEventListener('click', openAddModal);
emptyAddBtn.addEventListener('click', openAddModal);
closeModalBtn.addEventListener('click', closeModal);
cancelModalBtn.addEventListener('click', closeModal);

// Close modal when clicking backdrop
itemModal.addEventListener('click', (e) => {
  if (e.target === itemModal) closeModal();
});

// Initial Load
document.addEventListener('DOMContentLoaded', () => {
  fetchItems();
});
