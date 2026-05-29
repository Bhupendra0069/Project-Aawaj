/**
 * AAWAJ Report Page JS - Multi-step form, image upload, AI analysis, GPS, audio recording, location
 */

let currentStep = 1;
let uploadedFiles = [];
let mediaRecorder = null;
let audioChunks = [];
let audioBlob = null;
let recordingTimer = null;
let recordSeconds = 0;
let locationMap = null;
let locationMarker = null;
let searchTimeout = null;
let aiGeneratedText = '';  // Stores the AI-generated description
let isDescriptionAI = false; // Track whether current description is AI-generated

document.addEventListener('DOMContentLoaded', () => {
    initImageUpload();
    initLocationMap();
    initForm();
    initDescriptionTracking();
});

// ===== STEP NAVIGATION =====
function goToStep(step) {
    // Validate before advancing
    if (step > currentStep) {
        if (currentStep === 1 && uploadedFiles.length === 0) {
            document.getElementById('imageError').style.display = 'block'; return;
        }
        if (currentStep === 2) {
            const loc = document.getElementById('locationText').value;
            if (!loc) { document.getElementById('locationError').style.display = 'block'; return; }
        }
        if (currentStep === 3) {
            const desc = document.getElementById('description').value.trim();
            if (!desc && !audioBlob) { document.getElementById('detailError').style.display = 'block'; return; }
        }
    }

    document.querySelectorAll('.form-panel').forEach(p => p.classList.remove('active'));
    document.getElementById('step' + step).classList.add('active');

    document.querySelectorAll('.form-step-indicator').forEach(ind => {
        const s = parseInt(ind.dataset.step);
        ind.classList.remove('active', 'completed');
        if (s === step) ind.classList.add('active');
        else if (s < step) ind.classList.add('completed');
    });

    currentStep = step;
    if (step === 2 && locationMap) setTimeout(() => locationMap.invalidateSize(), 100);
    if (step === 4) buildReview();
}

// ===== IMAGE UPLOAD =====
function initImageUpload() {
    const zone = document.getElementById('uploadZone');
    const input = document.getElementById('imageInput');

    zone.addEventListener('click', () => input.click());
    zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
    zone.addEventListener('drop', e => {
        e.preventDefault(); zone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });
    input.addEventListener('change', () => handleFiles(input.files));
}

function handleFiles(files) {
    for (let f of files) {
        if (!f.type.startsWith('image/')) continue;
        if (uploadedFiles.length >= 5) { showToast('Maximum 5 images', 'warning'); break; }
        uploadedFiles.push(f);
    }
    renderPreviews();
    document.getElementById('imageError').style.display = 'none';

    // Show AI analysis section when images are uploaded
    if (uploadedFiles.length > 0) {
        document.getElementById('aiSection').classList.add('visible');
    }
}

function renderPreviews() {
    const preview = document.getElementById('imagePreview');
    preview.innerHTML = '';
    uploadedFiles.forEach((f, i) => {
        const url = URL.createObjectURL(f);
        const div = document.createElement('div');
        div.style.cssText = 'position:relative;';
        div.innerHTML = `<img src="${url}" class="upload-thumb"><button type="button" onclick="removeImage(${i})" style="position:absolute;top:-6px;right:-6px;background:var(--danger);color:#fff;border:none;border-radius:50%;width:22px;height:22px;cursor:pointer;font-size:0.7rem;">✕</button>`;
        preview.appendChild(div);
    });
}

function removeImage(index) {
    uploadedFiles.splice(index, 1);
    renderPreviews();

    // Hide AI section if no images left
    if (uploadedFiles.length === 0) {
        document.getElementById('aiSection').classList.remove('visible');
        document.getElementById('aiResultBox').classList.remove('visible');
        document.getElementById('aiError').style.display = 'none';
    }
}


// ===== AI IMAGE ANALYSIS (GEMINI) =====
async function analyzeImageWithAI() {
    if (uploadedFiles.length === 0) {
        showToast('Please upload an image first', 'warning');
        return;
    }

    const btn = document.getElementById('aiAnalyzeBtn');
    const resultBox = document.getElementById('aiResultBox');
    const resultText = document.getElementById('aiResultText');
    const aiError = document.getElementById('aiError');

    // Set loading state
    btn.classList.add('loading');
    btn.disabled = true;
    btn.querySelector('.ai-btn-text').textContent = 'Analyzing...';
    resultBox.classList.remove('visible');
    aiError.style.display = 'none';

    try {
        const formData = new FormData();
        formData.append('image', uploadedFiles[0]); // Send first image for analysis

        // Include location if available for better context
        const locationText = document.getElementById('locationText').value ||
                             document.getElementById('locationSearch').value || '';
        if (locationText) {
            formData.append('location', locationText);
        }

        const response = await fetch('/api/ai/analyze-image/', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success && data.description) {
            aiGeneratedText = data.description;
            resultText.textContent = data.description;
            resultBox.classList.add('visible');
            showToast('AI analysis complete!', 'success');
        } else {
            // Show error or fallback message
            const msg = data.message || 'AI analysis could not generate a description. Please write one manually.';
            aiError.textContent = '⚠ ' + msg;
            aiError.style.display = 'block';
        }
    } catch (err) {
        aiError.textContent = '⚠ Network error. Please check your connection and try again.';
        aiError.style.display = 'block';
    } finally {
        // Reset button state
        btn.classList.remove('loading');
        btn.disabled = false;
        btn.querySelector('.ai-btn-text').textContent = 'Analyze with AI';
    }
}

function useAIDescription() {
    if (!aiGeneratedText) return;

    const desc = document.getElementById('description');
    desc.value = aiGeneratedText;
    isDescriptionAI = true;

    // Show AI badge and clear button on step 3
    document.getElementById('aiGeneratedBadge').classList.add('visible');
    document.getElementById('descriptionActions').style.display = 'block';

    showToast('AI description applied! You can edit it in Step 3.', 'success');

    // Auto-advance to step 2 for location
    goToStep(2);
}

function clearAIDescription() {
    aiGeneratedText = '';
    document.getElementById('aiResultBox').classList.remove('visible');
    document.getElementById('aiError').style.display = 'none';
    showToast('AI description cleared. Write your own in Step 3.', 'info');
}

function clearDescriptionAndWrite() {
    document.getElementById('description').value = '';
    document.getElementById('description').focus();
    isDescriptionAI = false;
    document.getElementById('aiGeneratedBadge').classList.remove('visible');
    document.getElementById('descriptionActions').style.display = 'none';
    showToast('Description cleared. Write your own now.', 'info');
}

function initDescriptionTracking() {
    // When user manually edits the AI-generated text, update the badge
    const desc = document.getElementById('description');
    desc.addEventListener('input', () => {
        if (isDescriptionAI && desc.value !== aiGeneratedText) {
            // User is editing AI text — keep badge but mark as edited
            document.getElementById('aiGeneratedBadge').textContent = '✨ AI + Edited';
        }
        if (desc.value.trim() === '') {
            isDescriptionAI = false;
            document.getElementById('aiGeneratedBadge').classList.remove('visible');
            document.getElementById('descriptionActions').style.display = 'none';
        }
        document.getElementById('detailError').style.display = 'none';
    });
}


// ===== GPS AUTO-LOCATION =====
function useMyGPSLocation() {
    const btn = document.getElementById('gpsBtn');
    const btnText = btn.querySelector('.gps-btn-text');

    if (!navigator.geolocation) {
        showToast('Geolocation is not supported by your browser', 'error');
        return;
    }

    // Set loading state
    btn.classList.add('locating');
    btn.disabled = true;
    btnText.textContent = 'Locating...';

    navigator.geolocation.getCurrentPosition(
        (position) => {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;

            // Validate within Kathmandu Valley
            if (!isInsideKathmanduValley(lat, lng)) {
                showToast('Your current location is outside Kathmandu Valley. AAWAJ only covers Kathmandu, Bhaktapur, and Lalitpur districts.', 'error');
                btn.classList.remove('locating');
                btn.disabled = false;
                btnText.textContent = 'Use My Current Location';
                return;
            }

            // Update map
            locationMarker.setLatLng([lat, lng]);
            locationMap.setView([lat, lng], 16);
            updateLocation(lat, lng);

            // Reverse geocode to get address
            reverseGeocode(lat, lng);

            // Reset button
            btn.classList.remove('locating');
            btn.disabled = false;
            btnText.textContent = 'Use My Current Location';

            showToast('Location detected via GPS!', 'success');
        },
        (error) => {
            let msg = 'Unable to get your location.';
            switch (error.code) {
                case error.PERMISSION_DENIED:
                    msg = 'Location permission denied. Please enable GPS and allow location access.';
                    break;
                case error.POSITION_UNAVAILABLE:
                    msg = 'Location information unavailable. Please try again.';
                    break;
                case error.TIMEOUT:
                    msg = 'Location request timed out. Please try again.';
                    break;
            }
            showToast(msg, 'error');

            // Reset button
            btn.classList.remove('locating');
            btn.disabled = false;
            btnText.textContent = 'Use My Current Location';
        },
        {
            enableHighAccuracy: true,
            timeout: 15000,
            maximumAge: 0
        }
    );
}


// ===== KATHMANDU VALLEY BOUNDS =====
// Bounding box covering Kathmandu, Bhaktapur, and Lalitpur districts
const KTM_VALLEY_BOUNDS = L.latLngBounds(
    L.latLng(27.55, 85.15),  // Southwest corner
    L.latLng(27.82, 85.55)   // Northeast corner
);

function isInsideKathmanduValley(lat, lng) {
    return KTM_VALLEY_BOUNDS.contains(L.latLng(lat, lng));
}

// ===== LOCATION MAP =====
function initLocationMap() {
    locationMap = L.map('locationMap', {
        maxBounds: KTM_VALLEY_BOUNDS.pad(0.1),
        maxBoundsViscosity: 1.0,
        minZoom: 11
    }).setView([27.7172, 85.3240], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap'
    }).addTo(locationMap);

    locationMarker = L.marker([27.7172, 85.3240], { draggable: true }).addTo(locationMap);
    locationMarker.on('dragend', function () {
        const pos = locationMarker.getLatLng();
        if (!isInsideKathmanduValley(pos.lat, pos.lng)) {
            showToast('Location must be within Kathmandu Valley (Kathmandu, Bhaktapur, or Lalitpur)', 'error');
            locationMarker.setLatLng([27.7172, 85.3240]);
            locationMap.setView([27.7172, 85.3240], 13);
            return;
        }
        updateLocation(pos.lat, pos.lng);
        reverseGeocode(pos.lat, pos.lng);
    });

    locationMap.on('click', function (e) {
        if (!isInsideKathmanduValley(e.latlng.lat, e.latlng.lng)) {
            showToast('Location must be within Kathmandu Valley (Kathmandu, Bhaktapur, or Lalitpur)', 'error');
            return;
        }
        locationMarker.setLatLng(e.latlng);
        updateLocation(e.latlng.lat, e.latlng.lng);
        reverseGeocode(e.latlng.lat, e.latlng.lng);
    });

    // Search
    const searchInput = document.getElementById('locationSearch');
    const sugBox = document.getElementById('locationSuggestions');
    searchInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        const q = searchInput.value.trim();
        if (q.length < 3) { sugBox.style.display = 'none'; return; }
        searchTimeout = setTimeout(() => {
            fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(q)}&countrycodes=np&viewbox=85.15,27.55,85.55,27.82&bounded=1&limit=5`)
                .then(r => r.json())
                .then(results => {
                    if (!results.length) { sugBox.style.display = 'none'; return; }
                    sugBox.innerHTML = results.map(r => `<div style="padding:0.7rem 1rem;cursor:pointer;border-bottom:1px solid var(--border-glass);font-size:0.9rem;color:var(--text-secondary);transition:background 0.2s;" onmouseover="this.style.background='var(--bg-glass)'" onmouseout="this.style.background=''" onclick="selectLocation(${r.lat},${r.lon},'${r.display_name.replace(/'/g, "\\'")}')">${r.display_name}</div>`).join('');
                    sugBox.style.display = 'block';
                });
        }, 400);
    });
}

function selectLocation(lat, lng, name) {
    if (!isInsideKathmanduValley(lat, lng)) {
        showToast('This location is outside Kathmandu Valley. Please select a location within Kathmandu, Bhaktapur, or Lalitpur.', 'error');
        document.getElementById('locationSuggestions').style.display = 'none';
        return;
    }
    locationMarker.setLatLng([lat, lng]);
    locationMap.setView([lat, lng], 16);
    updateLocation(lat, lng);
    document.getElementById('locationText').value = name;
    document.getElementById('locationSearch').value = name;
    document.getElementById('selectedLocation').textContent = '📍 Selected: ' + name;
    document.getElementById('locationSuggestions').style.display = 'none';
    document.getElementById('locationError').style.display = 'none';
}

function updateLocation(lat, lng) {
    document.getElementById('latitude').value = lat;
    document.getElementById('longitude').value = lng;
}

function reverseGeocode(lat, lng) {
    fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`)
        .then(r => r.json())
        .then(data => {
            if (data.display_name) {
                document.getElementById('locationText').value = data.display_name;
                document.getElementById('locationSearch').value = data.display_name;
                document.getElementById('selectedLocation').textContent = '📍 Selected: ' + data.display_name;
                document.getElementById('locationError').style.display = 'none';
            }
        }).catch(() => {});
}

// ===== AUDIO RECORDING =====
function toggleRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        stopRecording();
    } else {
        startRecording();
    }
}

function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
            audioChunks = [];
            mediaRecorder = new MediaRecorder(stream);
            mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
            mediaRecorder.onstop = () => {
                audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                const url = URL.createObjectURL(audioBlob);
                const player = document.getElementById('audioPlayback');
                player.src = url;
                player.style.display = 'block';
                stream.getTracks().forEach(t => t.stop());
            };
            mediaRecorder.start();
            document.getElementById('recordBtn').classList.add('recording');
            document.getElementById('recordBtn').textContent = '⏹';
            document.getElementById('recordStatus').textContent = 'Recording...';
            recordSeconds = 0;
            recordingTimer = setInterval(() => {
                recordSeconds++;
                const m = String(Math.floor(recordSeconds / 60)).padStart(2, '0');
                const s = String(recordSeconds % 60).padStart(2, '0');
                document.getElementById('recordTime').textContent = m + ':' + s;
            }, 1000);
        })
        .catch(() => showToast('Microphone access denied', 'error'));
}

function stopRecording() {
    if (mediaRecorder) mediaRecorder.stop();
    clearInterval(recordingTimer);
    document.getElementById('recordBtn').classList.remove('recording');
    document.getElementById('recordBtn').textContent = '🎤';
    document.getElementById('recordStatus').textContent = 'Recording saved';
    document.getElementById('detailError').style.display = 'none';
}

// ===== REVIEW =====
function buildReview() {
    const loc = document.getElementById('locationText').value || document.getElementById('locationSearch').value;
    const desc = document.getElementById('description').value;
    let html = '<div style="display:flex;flex-direction:column;gap:1.2rem;">';
    // Images
    html += '<div><strong style="color:var(--text-secondary);">📸 Images (' + uploadedFiles.length + ')</strong><div class="upload-preview" style="margin-top:0.5rem;">';
    uploadedFiles.forEach(f => { html += `<img src="${URL.createObjectURL(f)}" class="upload-thumb">`; });
    html += '</div></div>';
    // Location
    html += `<div><strong style="color:var(--text-secondary);">📍 Location</strong><p style="margin-top:0.3rem;">${loc}</p></div>`;
    // Description
    if (desc) {
        const aiLabel = isDescriptionAI ? ' <span style="font-size:0.75rem;color:#a78bfa;background:rgba(124,58,237,0.15);padding:2px 8px;border-radius:4px;margin-left:6px;">✨ AI</span>' : '';
        html += `<div><strong style="color:var(--text-secondary);">📝 Description${aiLabel}</strong><p style="margin-top:0.3rem;">${desc}</p></div>`;
    }
    if (audioBlob) html += `<div><strong style="color:var(--text-secondary);">🎤 Audio</strong><p style="margin-top:0.3rem;color:var(--success);">✓ Audio recorded (${recordSeconds}s)</p></div>`;
    html += '</div>';
    document.getElementById('reviewContent').innerHTML = html;
}

// ===== FORM SUBMIT =====
function initForm() {
    document.getElementById('complaintForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = document.getElementById('submitBtn');
        btn.disabled = true;
        btn.textContent = '⏳ Submitting...';

        const formData = new FormData();
        uploadedFiles.forEach(f => formData.append('images', f));
        formData.append('location_text', document.getElementById('locationText').value || document.getElementById('locationSearch').value);
        formData.append('latitude', document.getElementById('latitude').value);
        formData.append('longitude', document.getElementById('longitude').value);
        formData.append('description', document.getElementById('description').value);
        if (audioBlob) formData.append('audio', audioBlob, 'recording.webm');

        try {
            const res = await fetch('/api/complaints/submit/', { method: 'POST', body: formData });
            const data = await res.json();
            if (data.success) {
                document.getElementById('complaintForm').style.display = 'none';
                document.getElementById('formSteps').style.display = 'none';
                document.getElementById('successScreen').style.display = 'block';
                document.getElementById('successCode').textContent = data.complaint_code;
                document.getElementById('successMessage').textContent = data.message;
                document.getElementById('trackLink').href = '/track/?code=' + data.complaint_code;
            } else {
                showToast(data.error || 'Submission failed', 'error');
                btn.disabled = false;
                btn.textContent = '🚀 Submit Complaint';
            }
        } catch (err) {
            showToast('Network error. Please try again.', 'error');
            btn.disabled = false;
            btn.textContent = '🚀 Submit Complaint';
        }
    });
}
