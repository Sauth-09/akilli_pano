document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const slideImg = document.getElementById('slide-img');
    const slideVideo = document.getElementById('slide-video');
    const loadingMessage = document.getElementById('loading-message');
    const statusText = document.getElementById('current-status');
    const dutyList = document.getElementById('duty-list');
    const clockEl = document.getElementById('clock');
    const dateEl = document.getElementById('date');
    const dailyMessageEl = document.getElementById('daily-message');
    const countdownEl = document.getElementById('countdown');

    // State
    let slideQueue = [];
    let currentSlideIndex = -1;
    let slideTimer = null;

    // --- CLOCK & DATE ---
    function updateClock() {
        const now = new Date();
        clockEl.textContent = now.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' });
        // The date is updated via API mostly, but local update is good for seconds
        // Actually DATE is updated via API response to handle locale better server-side if needed, 
        // but let's do local valid date as well.
        // dateEl.textContent = now.toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', year: 'numeric', weekday: 'long' });
    }
    setInterval(updateClock, 1000);
    updateClock();

    // --- DATA UPDATES (Status, Teachers, Schedule) ---
    async function fetchStatus() {
        try {
            const response = await fetch('/api/get_status');
            const data = await response.json();

            statusText.textContent = data.status;
            dateEl.textContent = `${data.date} ${data.day}`;

            if (data.duty_teachers && data.duty_teachers.length > 0) {
                data.duty_teachers.forEach(item => {
                    const li = document.createElement('li');
                    // Item format is "Location: Teacher" or just "Teacher" if fallback
                    if (item.includes(':')) {
                        const parts = item.split(':');
                        li.innerHTML = `<strong>${parts[0]}:</strong> ${parts[1]}`;
                    } else {
                        li.textContent = item;
                    }
                    dutyList.appendChild(li);
                });
            } else {
                dutyList.innerHTML = '<li>Nöbetçi bulunamadı.</li>';
            }

            // --- CLASS STATUSES ---
            // Find or create container
            let classListContainer = document.getElementById('class-status-list');
            if (!classListContainer) {
                // Determine where to add it. Sidebar seems appropriate.
                const sidebar = document.querySelector('.sidebar');
                if (sidebar) {
                    const h2 = document.createElement('h2');
                    h2.textContent = '🏫 Sınıf Durumları';
                    h2.style.marginTop = '20px';
                    h2.style.borderBottom = '2px solid #fff';
                    sidebar.appendChild(h2);

                    classListContainer = document.createElement('ul');
                    classListContainer.id = 'class-status-list';
                    classListContainer.className = 'info-list';
                    sidebar.appendChild(classListContainer);
                }
            }

            if (classListContainer) {
                classListContainer.innerHTML = '';
                if (data.class_statuses && data.class_statuses.length > 0) {
                    data.class_statuses.forEach(status => {
                        const li = document.createElement('li');
                        // Format: "9-A: MAT"
                        const parts = status.split(':');
                        if (parts.length === 2) {
                            li.innerHTML = `<strong>${parts[0]}:</strong> ${parts[1]}`;
                        } else {
                            li.textContent = status;
                        }
                        classListContainer.appendChild(li);
                    });
                } else {
                    const li = document.createElement('li');
                    li.textContent = 'Ders yok.';
                    classListContainer.appendChild(li);
                }
            }

            // Update daily message (random or first)
            if (data.messages && data.messages.length > 0) {
                // Pick a random one for variety every refresh
                const randomMsg = data.messages[Math.floor(Math.random() * data.messages.length)];
                const randomMsg = data.messages[Math.floor(Math.random() * data.messages.length)];
                dailyMessageEl.textContent = `"${randomMsg}"`;
            }

            // Update Countdown
            if (data.countdown) {
                updateCountdown(data.countdown);
            }

        } catch (error) {
            console.error('Status fetch error:', error);
        }
    }
    // Update status every 30 seconds
    setInterval(fetchStatus, 30000);
    fetchStatus();

    // --- COUNTDOWN ---
    function updateCountdown(countdownData) {
        if (!countdownData || !countdownData.target_date) {
            countdownEl.textContent = "...";
            return;
        }

        // Update label if exists (we might need to add label element in HTML or just replace text content)
        // For now let's assume the previous card header is static "YKS'ye Kalan" or we update it.
        // Let's find the header h2 in the countdown card if we want to change label details.
        const countdownCard = document.querySelector('.countdown-card h2');
        if (countdownCard && countdownData.label) {
            countdownCard.textContent = `⏳ ${countdownData.label}`;
        }

        const targetDate = new Date(countdownData.target_date);
        const now = new Date();
        const diff = targetDate - now;

        if (diff > 0) {
            const days = Math.floor(diff / (1000 * 60 * 60 * 24));
            countdownEl.textContent = `${days} Gün Kaldı`;
        } else {
            countdownEl.textContent = "Süre Doldu!";
        }
    }

    // --- SLIDESHOW LOGIC ---
    async function fetchSlides() {
        try {
            const response = await fetch('/api/get_slides');
            const newQueue = await response.json();

            // If queue changed significantly or is empty, logic might need adjustment
            // For simplicity, we just replace the queue. Ideally we diff.
            // If we are currently playing, we let it finish.

            if (newQueue.length === 0) {
                slideQueue = [];
                showNoSlides();
            } else {
                // Check if queue content is different to avoid restarting if same
                const isDifferent = JSON.stringify(slideQueue) !== JSON.stringify(newQueue);
                if (isDifferent) {
                    slideQueue = newQueue;
                    // If not currently playing (e.g. was empty), start
                    if (currentSlideIndex === -1 && slideQueue.length > 0) {
                        playNextSlide();
                    }
                }
            }
        } catch (error) {
            console.error('Slide fetch error:', error);
        }
    }

    // Check for new slides every 15 seconds
    setInterval(fetchSlides, 15000);
    fetchSlides();

    function showNoSlides() {
        slideImg.style.display = 'none';
        slideVideo.style.display = 'none';
        slideVideo.pause();
        loadingMessage.style.display = 'block';
        loadingMessage.textContent = "Slayt bulunamadı. Bot üzerinden gönderim yapınız.";
    }

    function playNextSlide() {
        if (slideQueue.length === 0) {
            showNoSlides();
            currentSlideIndex = -1;
            return;
        }

        loadingMessage.style.display = 'none';

        currentSlideIndex = (currentSlideIndex + 1) % slideQueue.length;
        const filename = slideQueue[currentSlideIndex];
        const url = `/static/slideshow/${filename}`;
        const ext = filename.split('.').pop().toLowerCase();

        if (['jpg', 'jpeg', 'png', 'gif'].includes(ext)) {
            // IMAGE
            slideVideo.style.display = 'none';
            slideVideo.pause();

            slideImg.onload = () => {
                slideImg.style.display = 'block';
                // Wait 10 seconds then next
                clearTimeout(slideTimer);
                slideTimer = setTimeout(playNextSlide, 10000);
            };
            slideImg.onerror = () => {
                console.error("Image failed to load:", url);
                playNextSlide();
            };
            slideImg.src = url;

        } else if (['mp4', 'webm'].includes(ext)) {
            // VIDEO
            slideImg.style.display = 'none';

            slideVideo.src = url;
            slideVideo.style.display = 'block';
            slideVideo.load();
            slideVideo.play().catch(e => {
                console.log("Autoplay prevented or error:", e);
                playNextSlide();
            });

            slideVideo.onended = () => {
                playNextSlide();
            };
            slideVideo.onerror = () => {
                console.error("Video failed to load:", url);
                playNextSlide();
            };
            // Fallback safety: move on after 60s if video gets stuck? 
            // Better to trust onended.
        } else {
            // Unknown type, skip
            playNextSlide();
        }
    }
});
