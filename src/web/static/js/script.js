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
    let slideshowConfig = {
        duration: 10000,
        transition: 'fade',
        fit_mode: 'contain'
    };

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

            // Update Basic Status
            // statusText.textContent = data.status; // Old simple update

            // Enhanced Merged Status + Class Card
            const statusCard = document.querySelector('.status-card');
            if (statusCard) {
                const statusEl = document.getElementById('current-status');
                const classList = document.getElementById('class-list');

                if (data.is_lesson) {
                    // DURING LESSON
                    statusEl.innerHTML = `<span class="status-icon">📚</span> Şuan: <strong>${data.lesson_number}. Dersteyiz</strong>`;
                    statusEl.className = 'status-text lesson-active';

                    // Show current class lessons
                    classList.innerHTML = '';
                    if (data.class_statuses && data.class_statuses.length > 0) {
                        data.class_statuses.forEach(status => {
                            const li = document.createElement('li');
                            const parts = status.split(':');
                            if (parts.length === 2) {
                                li.innerHTML = `<span class="class-name">${parts[0]}</span><span class="class-lesson">${parts[1]}</span>`;
                            } else {
                                li.textContent = status;
                            }
                            classList.appendChild(li);
                        });
                    } else {
                        classList.innerHTML = '<li class="no-data">Sınıf programı yüklenmemiş</li>';
                    }
                } else {
                    // DURING BREAK / OFF HOURS
                    let statusLabel = data.status;
                    if (statusLabel.toLowerCase().includes('teneffüs') || statusLabel.toLowerCase().includes('ara')) {
                        statusEl.innerHTML = `<span class="status-icon">☕</span> Şuan: <strong>Teneffüsteyiz</strong>`;
                    } else {
                        statusEl.innerHTML = `<span class="status-icon">🔔</span> ${statusLabel}`;
                    }
                    statusEl.className = 'status-text break-active';

                    // Show next class lessons
                    classList.innerHTML = '';
                    if (data.next_class_statuses && data.next_class_statuses.length > 0) {
                        const headerLi = document.createElement('li');
                        headerLi.className = 'next-header';
                        headerLi.textContent = '📋 Sonraki Dersler:';
                        classList.appendChild(headerLi);

                        data.next_class_statuses.forEach(status => {
                            const li = document.createElement('li');
                            const parts = status.split(':');
                            if (parts.length === 2) {
                                li.innerHTML = `<span class="class-name">${parts[0]}</span><span class="class-lesson">${parts[1]}</span>`;
                            } else {
                                li.textContent = status;
                            }
                            classList.appendChild(li);
                        });
                    } else {
                        classList.innerHTML = '<li class="no-data">Sonraki ders yok</li>';
                    }
                }

                // Auto-scroll if content overflows
                const container = document.getElementById('class-list-container');
                if (container && classList.scrollHeight > container.clientHeight) {
                    // Start scroll animation
                    if (!classList.classList.contains('auto-scroll')) {
                        classList.classList.add('auto-scroll');
                        const scrollDuration = Math.max(10, classList.children.length * 3);
                        classList.style.animationDuration = scrollDuration + 's';
                    }
                } else if (classList.classList.contains('auto-scroll')) {
                    classList.classList.remove('auto-scroll');
                }
            }

            dateEl.textContent = `${data.date} ${data.day}`;

            if (data.duty_teachers && data.duty_teachers.length > 0) {
                dutyList.innerHTML = '';
                data.duty_teachers.forEach(item => {
                    const li = document.createElement('li');
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

            // --- BIRTHDAYS ---
            // Look for the hook created by layout
            const birthdayHook = document.getElementById('birthday-container-hook');

            if (data.birthdays && data.birthdays.length > 0) {
                // Determine target: hook or legacy fallback? 
                // Since we implemented layout, we rely on hook. If hook missing (hidden in layout), we don't show.
                if (birthdayHook) {
                    // Show parent wrapper
                    if (birthdayHook.parentElement) {
                        birthdayHook.parentElement.style.display = 'block';
                    }

                    let birthdayContainer = document.getElementById('birthday-special-card');
                    if (!birthdayContainer) {
                        birthdayContainer = document.createElement('div');
                        birthdayContainer.id = 'birthday-special-card';
                        birthdayContainer.style = 'background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 99%, #fecfef 100%); color: #fff; padding: 15px; border-radius: 10px; margin-bottom: 20px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.2); animation: pulse 2s infinite;';

                        // Use title from hook data or default
                        const title = birthdayHook.getAttribute('data-title') || 'İyi ki Doğdun!';

                        birthdayContainer.innerHTML = `
                            <h3 style="margin: 0; font-size: 1.2rem;">🎂 ${title}</h3>
                            <div id="birthday-names" style="font-weight: bold; font-size: 1.1rem; margin-top: 5px; color: #d63384;"></div>
                        `;
                        birthdayHook.appendChild(birthdayContainer);

                        // Add pulse animation style if not exists
                        if (!document.getElementById('anim-style')) {
                            const style = document.createElement('style');
                            style.id = 'anim-style';
                            style.textContent = `
                                @keyframes pulse {
                                    0% { transform: scale(1); }
                                    50% { transform: scale(1.02); }
                                    100% { transform: scale(1); }
                                }
                            `;
                            document.head.appendChild(style);
                        }
                    }
                    const namesEl = document.getElementById('birthday-names');
                    if (namesEl) namesEl.textContent = data.birthdays.join(', ');
                }
            } else {
                // If birthdays empty, remove the card if exists
                const birthdayContainer = document.getElementById('birthday-special-card');
                if (birthdayContainer) birthdayContainer.remove();

                // Also hide parent wrapper to remove margin space
                if (birthdayHook && birthdayHook.parentElement) {
                    birthdayHook.parentElement.style.display = 'none';
                }
            }

            // Update daily message (random or first)
            // Now uses 'quotes' array instead of 'messages'
            if (data.quotes && data.quotes.length > 0) {
                const randomQuote = data.quotes[Math.floor(Math.random() * data.quotes.length)];
                dailyMessageEl.textContent = `"${randomQuote}"`;
            } else if (data.messages && data.messages.length > 0) {
                // Fallback if no quotes defined but messages exist (legacy support)
                // remove this if strict separation desired, but good for transition
                // dailyMessageEl.textContent = `"${data.messages[0]}"`; 
                dailyMessageEl.textContent = "...";
            } else {
                dailyMessageEl.textContent = "...";
            }

            // Update Countdown
            if (data.countdown) {
                updateCountdown(data.countdown);
            }

            // Update Slideshow Config
            if (data.slideshow) {
                slideshowConfig = data.slideshow;
            }

            // Update Marquee Content
            const marqueeEl = document.getElementById('footer-marquee');
            if (marqueeEl && data.messages) {
                const newText = data.messages.length > 0 ? data.messages.join('   •   ') : 'Akıllı Okul Panosu Sistemine Hoşgeldiniz';
                if (marqueeEl.textContent !== newText) {
                    marqueeEl.textContent = newText;
                }

                // Update Marquee Style if needed (optional, but good for full sync)
                if (data.marquee) {
                    if (data.marquee.duration) marqueeEl.style.animationDuration = data.marquee.duration + 's';
                    if (data.marquee.font_size) marqueeEl.style.fontSize = data.marquee.font_size + 'rem';
                    if (data.marquee.color) marqueeEl.style.color = data.marquee.color;
                    if (data.marquee.font_family) marqueeEl.style.fontFamily = data.marquee.font_family;
                }
            }

        } catch (error) {
            console.error('Status fetch error:', error);
        }
    }
    // Update status every 60 seconds (1 minute)
    setInterval(fetchStatus, 60000);
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

            if (newQueue.length === 0) {
                slideQueue = [];
                showNoSlides();
            } else {
                // If queue changed significantly or is empty, logic might need adjustment
                const isDifferent = JSON.stringify(slideQueue) !== JSON.stringify(newQueue);
                if (isDifferent) {
                    slideQueue = newQueue;
                    // Fix: Reset index if out of bounds, or start if stopped
                    if (currentSlideIndex >= slideQueue.length) {
                        currentSlideIndex = -1;
                    }

                    if (currentSlideIndex === -1 && slideQueue.length > 0) {
                        playNextSlide();
                    }
                }
            }
        } catch (error) {
            console.error('Slide fetch error:', error);
        }
    }

    // Capture config from status update to keep it synced
    // We modify fetchStatus to update local variable `slideshowConfig`
    // However, fetchStatus is above. Let's add a small hook there or just poll it here if endpoint supported it.
    // Better: Update `data` object in fetchStatus is local to that function. 
    // We should make `slideshowConfig` global or update it from `fetchStatus`.

    // Check for new slides every 60 seconds (1 minute) to reduce load
    setInterval(fetchSlides, 60000);
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

        // Loop Logic
        currentSlideIndex = (currentSlideIndex + 1) % slideQueue.length;
        const filename = slideQueue[currentSlideIndex];
        const url = `/static/slideshow/${filename}`;
        const ext = filename.split('.').pop().toLowerCase();

        // Apply Fit Mode
        const fitClass = slideshowConfig.fit_mode === 'cover' ? 'fit-cover' : 'fit-contain';
        slideImg.className = fitClass;
        slideVideo.className = fitClass;

        // Transition Effect Logic
        let effect = slideshowConfig.transition || 'fade';

        if (effect === 'random') {
            const effects = ['fade', 'slide', 'zoom', 'flip', 'blur', 'rotate', 'slide-up', 'slide-down'];
            effect = effects[Math.floor(Math.random() * effects.length)];
        }

        // Force reflow
        void slideImg.offsetWidth;

        // Set Exit Class (Initial State)
        const exitClasses = {
            'fade': 'fade-out',
            'slide': 'slide-out-left',
            'zoom': 'zoom-out',
            'flip': 'flip-out',
            'blur': 'blur-out',
            'rotate': 'rotate-out',
            'slide-up': 'slide-up-out',
            'slide-down': 'slide-down-out'
        };

        if (exitClasses[effect]) {
            slideImg.classList.add(exitClasses[effect]);
        } else {
            slideImg.classList.add('fade-out'); // Fallback
        }

        // Wait for exit animation (1s) before changing source
        setTimeout(() => {
            if (['jpg', 'jpeg', 'png', 'gif'].includes(ext)) {
                // IMAGE
                slideVideo.style.display = 'none';
                slideVideo.pause();

                slideImg.onload = () => {
                    slideImg.style.display = 'block';

                    // Trigger Entry Animation: Remove 'out' classes
                    slideImg.className = fitClass; // Reset classes to just fit mode

                    // Add 'in' classes for animation
                    const animationMap = {
                        'slide': 'slide-in-right',
                        'zoom': 'zoom-in',
                        'flip': 'flip-in',
                        'blur': 'blur-in',
                        'rotate': 'rotate-in',
                        'slide-up': 'slide-up-in',
                        'slide-down': 'slide-down-in'
                    };

                    if (animationMap[effect]) {
                        slideImg.classList.add(animationMap[effect]);
                    } else {
                        // For fade, we just removed fade-out, so opacity goes back to 1 via transition
                        // No specific animation class needed if we rely on base transition
                    }

                    // Cleanup classes after animation ends
                    setTimeout(() => {
                        if (animationMap[effect]) {
                            slideImg.classList.remove(animationMap[effect]);
                        }
                    }, 1000);

                    clearTimeout(slideTimer);
                    slideTimer = setTimeout(playNextSlide, slideshowConfig.duration);
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
            } else {
                playNextSlide();
            }
        }, 1000); // Wait 1s for exit animation
    }

    // Hook to update config from fetchStatus (we need to modify fetchStatus slightly to expose data or write to global)
    // To avoid modifying fetchStatus again in this tool call (complexity), let's assume fetchStatus writes to global `slideshowConfig` if we declare it at top.
    // I will use another replace to inject logic into fetchStatus.
    // --- RIDDLE SLIDESHOW LOGIC ---
    let riddleQueue = [];
    let currentRiddleIndex = -1;
    let riddleTimer = null;
    const riddleImg = document.getElementById('riddle-img');
    const riddleVideo = document.getElementById('riddle-video');
    const riddleLoading = document.getElementById('riddle-loading');
    const riddleEmpty = document.getElementById('riddle-empty');

    async function fetchRiddles() {
        if (!document.getElementById('riddle-container')) return; // Exit if card not present
        try {
            const response = await fetch('/api/riddles');
            const newQueue = await response.json();

            if (newQueue.length === 0) {
                riddleQueue = [];
                showNoRiddles();
            } else {
                const isDifferent = JSON.stringify(riddleQueue) !== JSON.stringify(newQueue);
                if (isDifferent) {
                    riddleQueue = newQueue;
                    if (currentRiddleIndex >= riddleQueue.length) currentRiddleIndex = -1;
                    if (currentRiddleIndex === -1 && riddleQueue.length > 0) {
                        playNextRiddle();
                    }
                }
            }
        } catch (error) { console.error('Riddle fetch error:', error); }
    }

    function showNoRiddles() {
        if (riddleImg) riddleImg.style.display = 'none';
        if (riddleVideo) { riddleVideo.style.display = 'none'; riddleVideo.pause(); }
        if (riddleLoading) riddleLoading.style.display = 'none';
        if (riddleEmpty) riddleEmpty.style.display = 'block';
    }

    function playNextRiddle() {
        if (riddleQueue.length === 0) {
            showNoRiddles();
            return;
        }

        if (riddleLoading) riddleLoading.style.display = 'none';
        if (riddleEmpty) riddleEmpty.style.display = 'none';

        currentRiddleIndex = (currentRiddleIndex + 1) % riddleQueue.length;
        const url = riddleQueue[currentRiddleIndex];
        const ext = url.split('.').pop().toLowerCase();

        // Standard fade effect for riddles
        if (riddleImg) {
            riddleImg.style.opacity = 0;
            riddleImg.style.transition = 'opacity 0.5s';
        }

        setTimeout(() => {
            if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) {
                if (riddleVideo) { riddleVideo.style.display = 'none'; riddleVideo.pause(); }
                if (riddleImg) {
                    riddleImg.onload = () => {
                        riddleImg.style.display = 'block';
                        setTimeout(() => riddleImg.style.opacity = 1, 50);
                        clearTimeout(riddleTimer);
                        riddleTimer = setTimeout(playNextRiddle, 10000); // 10s per riddle
                    };
                    riddleImg.src = url;
                }
            } else if (['mp4', 'webm'].includes(ext)) {
                if (riddleImg) riddleImg.style.display = 'none';
                if (riddleVideo) {
                    riddleVideo.src = url;
                    riddleVideo.style.display = 'block';
                    riddleVideo.play().catch(e => { playNextRiddle(); });
                    riddleVideo.onended = () => playNextRiddle();
                } else playNextRiddle();
            } else playNextRiddle();
        }, 500);
    }

    // Init Riddle Fetch
    setInterval(fetchRiddles, 30000); // Check every 30s
    fetchRiddles();

    // --- CONTEXT MENU LOGIC ---
    const contextMenu = document.getElementById('custom-context-menu');
    const menuFullscreen = document.getElementById('menu-fullscreen');
    const menuSettings = document.getElementById('menu-settings');

    if (contextMenu) {
        // Prevent default context menu and show custom one
        document.addEventListener('contextmenu', (e) => {
            e.preventDefault();

            // Calculate Position
            let x = e.clientX;
            let y = e.clientY;

            // Boundary checks
            const winWidth = window.innerWidth;
            const winHeight = window.innerHeight;
            const menuWidth = 200; // Approx
            const menuHeight = 100; // Approx

            if (x + menuWidth > winWidth) x = winWidth - menuWidth;
            if (y + menuHeight > winHeight) y = winHeight - menuHeight;

            contextMenu.style.left = `${x}px`;
            contextMenu.style.top = `${y}px`;
            contextMenu.style.display = 'block';
        });

        // Close menu on click anywhere
        document.addEventListener('click', () => {
            contextMenu.style.display = 'none';
        });

        // Full Screen Toggle
        if (menuFullscreen) {
            menuFullscreen.addEventListener('click', () => {
                if (!document.fullscreenElement) {
                    document.documentElement.requestFullscreen().catch(err => {
                        console.error(`Error attempting to enable full-screen mode: ${err.message} (${err.name})`);
                    });
                    menuFullscreen.innerHTML = '<i class="fas fa-compress"></i> Tam Ekrandan Çık';
                } else {
                    if (document.exitFullscreen) {
                        document.exitFullscreen();
                        menuFullscreen.innerHTML = '<i class="fas fa-expand"></i> Tam Ekran';
                    }
                }
            });
        }

        // Settings Redirect
        if (menuSettings) {
            menuSettings.addEventListener('click', () => {
                window.open('/admin', '_blank');
            });
        }
    }
});
