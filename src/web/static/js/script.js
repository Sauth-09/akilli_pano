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

            // Enhanced Status Update with Scrolling Classes
            const statusCard = document.querySelector('.status-card');
            if (statusCard) {
                // 1. Update Main Status Text
                let mainStatusEl = statusCard.querySelector('#current-status');
                if (!mainStatusEl) {
                    mainStatusEl = document.createElement('div');
                    mainStatusEl.id = 'current-status';
                    mainStatusEl.className = 'status-text';
                    statusCard.appendChild(mainStatusEl);
                }
                mainStatusEl.textContent = data.status;

                // 2. Update Class List (Scrolling)
                let detailContainer = document.getElementById('status-detail-container');
                if (!detailContainer) {
                    detailContainer = document.createElement('div');
                    detailContainer.id = 'status-detail-container';
                    detailContainer.style = 'margin-top: 10px; overflow: hidden; white-space: nowrap; height: 30px; position: relative; background: rgba(0,0,0,0.05); border-radius: 4px; display: flex; align-items: center;';
                    statusCard.appendChild(detailContainer);
                }

                if (data.class_statuses && data.class_statuses.length > 0) {
                    // Format: "9-A Matematik   10-B Fizik ..."
                    // Replace ':' with space for cleaner look or keep it? User said "9/A Türkçe"
                    const formattedList = data.class_statuses.map(s => s.replace(':', '')).join('   •   ');

                    // Check if content changed to avoid jitter
                    const currentText = detailContainer.getAttribute('data-content');
                    if (currentText !== formattedList) {
                        detailContainer.innerHTML = '';
                        detailContainer.setAttribute('data-content', formattedList);

                        const scrollingText = document.createElement('div');
                        scrollingText.textContent = formattedList;
                        scrollingText.style = 'display: inline-block; padding-left: 100%; animation: scroll-left 20s linear infinite; font-weight: 500; color: #555;';
                        detailContainer.appendChild(scrollingText);

                        // Add CSS animation keyframes if not exists
                        if (!document.getElementById('scroll-anim')) {
                            const style = document.createElement('style');
                            style.id = 'scroll-anim';
                            style.textContent = `
                                 @keyframes scroll-left {
                                     0% { transform: translateX(0); }
                                     100% { transform: translateX(-100%); }
                                 }
                             `;
                            document.head.appendChild(style);
                        }
                    }
                } else {
                    detailContainer.innerHTML = '<span style="padding: 5px; color: #888; width: 100%; text-align: center; display: block;">Ders yok</span>';
                }
            }

            dateEl.textContent = `${data.date} ${data.day}`;

            if (data.duty_teachers && data.duty_teachers.length > 0) {
                dutyList.innerHTML = '';
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
            // Only populate if container exists (rendered by layout)
            let classListContainer = document.getElementById('class-status-list');
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

            // --- BIRTHDAYS ---
            // Look for the hook created by layout
            const birthdayHook = document.getElementById('birthday-container-hook');

            if (data.birthdays && data.birthdays.length > 0) {
                // Determine target: hook or legacy fallback? 
                // Since we implemented layout, we rely on hook. If hook missing (hidden in layout), we don't show.
                if (birthdayHook) {
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
            }

            // Update daily message (random or first)
            if (data.messages && data.messages.length > 0) {
                // Pick a random one for variety every refresh
                const randomMsg = data.messages[Math.floor(Math.random() * data.messages.length)];
                dailyMessageEl.textContent = `"${randomMsg}"`;
            }

            // Update Countdown
            if (data.countdown) {
                updateCountdown(data.countdown);
            }

            // Update Slideshow Config
            if (data.slideshow) {
                slideshowConfig = data.slideshow;
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
                window.location.href = '/admin';
            });
        }
    }
});
