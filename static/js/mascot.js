/**
 * mascot.js - Bot linh vật đáng yêu cho Hoa quả Sơn
 * - Đứng yên góc dưới bên phải màn hình, kéo chuột mới di chuyển
 * - Chỉ có đúng 2 câu thoại: "Chào mừng đến Hoa quả Sơn!" và "Hôm nay bạn muốn dùng gì?"
 * - Mặc định BẬT ở khu khách, mặc định TẮT ở khu quản lý (có nút bật/tắt)
 * - Dùng đúng file ảnh static/img/mascot.png
 */
(function () {
    'use strict';

    // ĐÚNG 2 CÂU THOẠI DUY NHẤT
    const QUOTES = [
        "Chào mừng đến Hoa quả Sơn!",
        "Hôm nay bạn muốn dùng gì?"
    ];

    // Xác định khu vực hiện tại: Quản lý hay Khách hàng
    const isManagerArea = window.location.pathname.startsWith('/quan-ly') || 
                          (document.body && document.body.getAttribute('data-area') === 'manager');

    // Mặc định: Khu khách bật (true), Khu quản lý tắt (false)
    let isEnabled = !isManagerArea;
    const storageKey = isManagerArea ? 'mascot_manager_enabled' : 'mascot_client_enabled';

    if (!isManagerArea) {
        try {
            const savedState = localStorage.getItem(storageKey);
            if (savedState !== null) {
                isEnabled = (savedState === 'true');
            }
        } catch (e) {
            console.warn('Không thể truy cập localStorage:', e);
        }
    }

    let currentX = 0;
    let currentY = 0;
    let facingDirection = -1; // -1: quay mặt vào trong màn hình
    let currentQuoteIndex = 0;
    let bubbleTimeout = null;

    // Trạng thái kéo thả
    let isDragging = false;
    let dragStartX = 0;
    let dragStartY = 0;
    let botStartX = 0;
    let botStartY = 0;
    let hasMovedSignificantly = false;

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    let container, wrapper, bodyElem, imgElem, shadowElem, bubbleElem, toggleBtn;

    function getBotSize() {
        return window.innerWidth <= 768 ? 60 : 80;
    }

    function initMascotDOM() {
        container = document.getElementById('mascot-container');
        toggleBtn = document.getElementById('mascot-toggle-btn');

        if (!container) return;

        wrapper = container.querySelector('.mascot-wrapper');
        bodyElem = container.querySelector('.mascot-body');
        imgElem = container.querySelector('.mascot-img');
        shadowElem = container.querySelector('.mascot-shadow');
        bubbleElem = container.querySelector('.mascot-bubble');

        setBottomRightPosition(false);
        setIdleState();
        applyEnabledState();

        // Lời chào mừng phiên mới
        checkSessionWelcome();

        registerDragAndClickEvents();
    }

    function setBottomRightPosition(animated = false) {
        const size = getBotSize();
        const targetX = Math.max(15, window.innerWidth - size - 25);
        const targetY = Math.max(80, window.innerHeight - size - 25);
        facingDirection = -1;
        updatePosition(targetX, targetY, animated);
    }

    function checkSessionWelcome() {
        if (!isEnabled) return;
        try {
            const hasWelcomed = sessionStorage.getItem('mascot_welcomed');
            if (!hasWelcomed) {
                showSpeech(QUOTES[0], 4000);
                sessionStorage.setItem('mascot_welcomed', 'true');
            }
        } catch (e) {
            showSpeech(QUOTES[0], 4000);
        }
    }

    function showSpeech(text, duration = 3000) {
        if (!bubbleElem || !isEnabled) return;
        bubbleElem.textContent = text;
        bubbleElem.classList.add('show');

        if (bubbleTimeout) clearTimeout(bubbleTimeout);
        bubbleTimeout = setTimeout(() => {
            bubbleElem.classList.remove('show');
        }, duration);
    }

    function updatePosition(x, y, animated = false) {
        if (!wrapper) return;
        currentX = x;
        currentY = y;

        if (!animated || isDragging || prefersReducedMotion) {
            wrapper.style.transition = 'none';
        } else {
            wrapper.style.transition = 'transform 0.4s cubic-bezier(0.25, 1, 0.5, 1)';
        }

        wrapper.style.transform = `translate3d(${x}px, ${y}px, 0)`;
        if (imgElem) {
            imgElem.style.transform = `scaleX(${facingDirection})`;
        }
    }

    function setIdleState() {
        if (wrapper) {
            wrapper.classList.remove('mascot-moving');
            wrapper.classList.add('mascot-idle');
        }
    }

    function setMovingState() {
        if (wrapper) {
            wrapper.classList.remove('mascot-idle');
            wrapper.classList.add('mascot-moving');
        }
    }

    function handleBotClick() {
        if (!bodyElem) return;

        bodyElem.classList.remove('mascot-jump');
        void bodyElem.offsetWidth;
        bodyElem.classList.add('mascot-jump');

        // Luân phiên giữa 2 câu thoại
        currentQuoteIndex = (currentQuoteIndex + 1) % QUOTES.length;
        showSpeech(QUOTES[currentQuoteIndex], 3500);

        setTimeout(() => {
            bodyElem.classList.remove('mascot-jump');
        }, 500);
    }

    function registerDragAndClickEvents() {
        if (!bodyElem) return;

        function onPointerDown(e) {
            if (!isEnabled) return;
            if (e.type === 'mousedown' && e.button !== 0) return;

            const clientX = e.type.startsWith('touch') ? e.touches[0].clientX : e.clientX;
            const clientY = e.type.startsWith('touch') ? e.touches[0].clientY : e.clientY;

            isDragging = true;
            hasMovedSignificantly = false;
            dragStartX = clientX;
            dragStartY = clientY;
            botStartX = currentX;
            botStartY = currentY;

            document.body.classList.add('mascot-dragging');
            setMovingState();

            if (e.type === 'mousedown') {
                document.addEventListener('mousemove', onPointerMove);
                document.addEventListener('mouseup', onPointerUp);
            } else {
                document.addEventListener('touchmove', onPointerMove, { passive: false });
                document.addEventListener('touchend', onPointerUp);
                document.addEventListener('touchcancel', onPointerUp);
            }

            e.preventDefault();
        }

        function onPointerMove(e) {
            if (!isDragging) return;

            const clientX = e.type.startsWith('touch') ? e.touches[0].clientX : e.clientX;
            const clientY = e.type.startsWith('touch') ? e.touches[0].clientY : e.clientY;

            const deltaX = clientX - dragStartX;
            const deltaY = clientY - dragStartY;

            if (Math.hypot(deltaX, deltaY) > 4) {
                hasMovedSignificantly = true;
            }

            let newX = botStartX + deltaX;
            let newY = botStartY + deltaY;

            const size = getBotSize();
            const minX = 15;
            const maxX = Math.max(minX, window.innerWidth - size - 15);
            const minY = 80;
            const maxY = Math.max(minY, window.innerHeight - size - 15);

            newX = Math.min(Math.max(newX, minX), maxX);
            newY = Math.min(Math.max(newY, minY), maxY);

            if (deltaX !== 0) {
                facingDirection = deltaX > 0 ? 1 : -1;
            }

            updatePosition(newX, newY, false);

            if (e.type === 'touchmove') {
                e.preventDefault();
            }
        }

        function onPointerUp(e) {
            if (!isDragging) return;
            isDragging = false;

            document.body.classList.remove('mascot-dragging');
            setIdleState();

            document.removeEventListener('mousemove', onPointerMove);
            document.removeEventListener('mouseup', onPointerUp);
            document.removeEventListener('touchmove', onPointerMove);
            document.removeEventListener('touchend', onPointerUp);
            document.removeEventListener('touchcancel', onPointerUp);

            if (!hasMovedSignificantly) {
                handleBotClick();
            }
        }

        bodyElem.addEventListener('mousedown', onPointerDown);
        bodyElem.addEventListener('touchstart', onPointerDown, { passive: false });

        window.addEventListener('resize', function () {
            const size = getBotSize();
            const maxX = Math.max(15, window.innerWidth - size - 15);
            const maxY = Math.max(80, window.innerHeight - size - 15);

            if (currentX > maxX || currentY > maxY) {
                updatePosition(Math.min(currentX, maxX), Math.min(currentY, maxY), false);
            }
        });

        if (toggleBtn) {
            toggleBtn.addEventListener('click', function (e) {
                e.stopPropagation();
                isEnabled = !isEnabled;

                if (!isManagerArea) {
                    try {
                        localStorage.setItem(storageKey, isEnabled.toString());
                    } catch (err) {
                        console.warn(err);
                    }
                }

                applyEnabledState();

                if (isEnabled) {
                    showSpeech(QUOTES[1], 2500);
                } else {
                    if (bubbleTimeout) clearTimeout(bubbleTimeout);
                }
            });
        }
    }

    function applyEnabledState() {
        if (!container || !toggleBtn) return;

        if (isEnabled) {
            container.style.display = 'block';
            toggleBtn.innerHTML = '<i class="bi bi-eye-slash me-1"></i> Tắt bé Bot';
            toggleBtn.title = "Bấm để ẩn linh vật";
        } else {
            container.style.display = 'none';
            toggleBtn.innerHTML = '<i class="bi bi-emoji-smile me-1"></i> Bật bé Bot';
            toggleBtn.title = "Bấm để hiện linh vật";
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initMascotDOM);
    } else {
        initMascotDOM();
    }
})();
