(function() {
    var scriptTag = document.currentScript || document.querySelector('script[src*="widget.js"]');
    if (!scriptTag) return;
    
    var userId = scriptTag.getAttribute('data-user-id');
    if (!userId) {
        console.error("MybaseAI: Missing data-user-id attribute on script tag.");
        return;
    }
    
    var srcParts = new URL(scriptTag.src);
    var host = srcParts.origin;
    var widgetUrl = host + "/widget/" + userId + "/";
    var iconUrl = host + "/static/MYbaseAI.png";
    
    var container = document.createElement('div');
    container.id = 'mybaseai-widget-container';
    container.style.position = 'fixed';
    container.style.bottom = '20px';
    container.style.right = '20px';
    container.style.zIndex = '999999';
    container.style.display = 'flex';
    container.style.flexDirection = 'column';
    container.style.alignItems = 'flex-end';
    
    var iframeWrapper = document.createElement('div');
    iframeWrapper.style.width = '400px';
    iframeWrapper.style.height = '600px';
    iframeWrapper.style.maxWidth = 'calc(100vw - 40px)';
    iframeWrapper.style.maxHeight = 'calc(100vh - 100px)';
    iframeWrapper.style.borderRadius = '16px';
    iframeWrapper.style.overflow = 'hidden';
    iframeWrapper.style.boxShadow = '0 10px 40px rgba(0,0,0,0.15)';
    iframeWrapper.style.border = '1px solid #e2e8f0';
    iframeWrapper.style.marginBottom = '15px';
    iframeWrapper.style.display = 'none';
    iframeWrapper.style.transition = 'all 0.3s ease';
    iframeWrapper.style.opacity = '0';
    iframeWrapper.style.transform = 'translateY(20px)';
    
    var iframe = document.createElement('iframe');
    iframe.src = widgetUrl;
    iframe.style.width = '100%';
    iframe.style.height = '100%';
    iframe.style.border = 'none';
    iframe.style.background = 'transparent';
    
    var btn = document.createElement('div');
    btn.style.width = '60px';
    btn.style.height = '60px';
    btn.style.borderRadius = '50%';
    btn.style.background = 'transparent';
    btn.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
    btn.style.cursor = 'pointer';
    btn.style.display = 'flex';
    btn.style.alignItems = 'center';
    btn.style.justifyContent = 'center';
    btn.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
    btn.style.overflow = 'hidden';
    
    var icon = document.createElement('img');
    icon.src = iconUrl;
    icon.style.width = '100%';
    icon.style.height = '100%';
    icon.style.objectFit = 'cover';
    icon.style.transform = 'scale(1.4)';
    icon.style.transition = 'all 0.3s ease';
    
    var closeIcon = document.createElement('div');
    closeIcon.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="white" width="30" height="30"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>';
    closeIcon.style.display = 'none';
    closeIcon.style.transition = 'all 0.3s ease';
    
    btn.appendChild(icon);
    btn.appendChild(closeIcon);
    iframeWrapper.appendChild(iframe);
    container.appendChild(iframeWrapper);
    container.appendChild(btn);
    document.body.appendChild(container);
    
    var isDragging = false;
    var hasDragged = false;
    var initialX, initialY, currentX = 0, currentY = 0;

    btn.addEventListener('mousedown', function(e) {
        isDragging = true;
        hasDragged = false;
        initialX = e.clientX - currentX;
        initialY = e.clientY - currentY;
    });

    document.addEventListener('mousemove', function(e) {
        if (!isDragging) return;
        hasDragged = true;
        currentX = e.clientX - initialX;
        currentY = e.clientY - initialY;
        container.style.transform = 'translate(' + currentX + 'px, ' + currentY + 'px)';
    });

    document.addEventListener('mouseup', function() {
        isDragging = false;
    });
    
    btn.addEventListener('touchstart', function(e) {
        isDragging = true;
        hasDragged = false;
        initialX = e.touches[0].clientX - currentX;
        initialY = e.touches[0].clientY - currentY;
    }, {passive: true});

    document.addEventListener('touchmove', function(e) {
        if (!isDragging) return;
        hasDragged = true;
        currentX = e.touches[0].clientX - initialX;
        currentY = e.touches[0].clientY - initialY;
        container.style.transform = 'translate(' + currentX + 'px, ' + currentY + 'px)';
    }, {passive: true});

    document.addEventListener('touchend', function() {
        isDragging = false;
    });
    
    var isOpen = false;
    btn.addEventListener('click', function() {
        if (hasDragged) {
            hasDragged = false;
            return;
        }
        isOpen = !isOpen;
        if(isOpen) {
            btn.style.background = 'linear-gradient(135deg, #4f46e5 0%, #0ea5e9 100%)';
            iframeWrapper.style.display = 'block';
            setTimeout(() => {
                iframeWrapper.style.opacity = '1';
                iframeWrapper.style.transform = 'translateY(0)';
            }, 10);
            icon.style.display = 'none';
            closeIcon.style.display = 'block';
            btn.style.transform = 'rotate(90deg)';
        } else {
            btn.style.background = 'transparent';
            iframeWrapper.style.opacity = '0';
            iframeWrapper.style.transform = 'translateY(20px)';
            setTimeout(() => {
                iframeWrapper.style.display = 'none';
            }, 300);
            icon.style.display = 'block';
            closeIcon.style.display = 'none';
            btn.style.transform = 'rotate(0deg)';
        }
    });
})();
