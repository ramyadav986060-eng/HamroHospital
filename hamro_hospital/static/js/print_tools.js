/**
 * TUH Print Tools
 * ----------------
 * Shared helpers used by every printable document (OPD ticket, patient card,
 * invoices, pharmacy/lab/radiology receipts, etc.) so that:
 *   - Print, Download PDF and Download JPG all render from the EXACT same
 *     on-screen DOM/CSS, so print output, the downloaded PDF and the
 *     downloaded JPG always look identical.
 *   - Output is captured at high resolution (scale 3) so the JPG is
 *     archive/share quality and the PDF is crisp when printed again.
 *
 * Depends on html2canvas + jsPDF (loaded from CDN, see print_actions include).
 */
(function (window) {
    'use strict';

    function loadScriptOnce(src) {
        return new Promise(function (resolve, reject) {
            var existing = document.querySelector('script[data-tuh-src="' + src + '"]');
            if (existing) {
                if (existing.dataset.loaded === 'true') return resolve();
                existing.addEventListener('load', resolve);
                existing.addEventListener('error', reject);
                return;
            }
            var script = document.createElement('script');
            script.src = src;
            script.dataset.tuhSrc = src;
            script.onload = function () {
                script.dataset.loaded = 'true';
                resolve();
            };
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    function ensureLibs() {
        return loadScriptOnce('https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js')
            .then(function () {
                return loadScriptOnce('https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js');
            });
    }

    function toggleBusy(triggerEl, busy) {
        if (!triggerEl) return;
        if (busy) {
            triggerEl.dataset.originalHtml = triggerEl.innerHTML;
            triggerEl.disabled = true;
            triggerEl.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Preparing...';
        } else {
            triggerEl.disabled = false;
            if (triggerEl.dataset.originalHtml) {
                triggerEl.innerHTML = triggerEl.dataset.originalHtml;
            }
        }
    }

    function captureElement(targetId) {
        var target = document.getElementById(targetId);
        if (!target) {
            return Promise.reject(new Error('TUH Print Tools: element #' + targetId + ' not found'));
        }
        return ensureLibs().then(function () {
            return window.html2canvas(target, {
                scale: 3,
                useCORS: true,
                backgroundColor: '#ffffff',
                logging: false
            });
        });
    }

    /** Download the given element as a high-resolution JPG. */
    window.tuhDownloadJPG = function (targetId, fileName, triggerEl) {
        toggleBusy(triggerEl, true);
        captureElement(targetId).then(function (canvas) {
            var link = document.createElement('a');
            link.download = (fileName || 'document') + '.jpg';
            link.href = canvas.toDataURL('image/jpeg', 0.97);
            link.click();
        }).catch(function (err) {
            console.error(err);
            alert('Could not generate the JPG. Please try again.');
        }).finally(function () {
            toggleBusy(triggerEl, false);
        });
    };

    /** Download the given element as a single, correctly-sized PDF page. */
    window.tuhDownloadPDF = function (targetId, fileName, triggerEl) {
        toggleBusy(triggerEl, true);
        captureElement(targetId).then(function (canvas) {
            var jsPDF = window.jspdf.jsPDF;
            var imgData = canvas.toDataURL('image/jpeg', 0.97);

            // Size the PDF page to the captured element itself (in mm) so the
            // document always fits a single page with no wasted blank space,
            // and looks identical to what is on screen / printed.
            var pxToMm = 0.264583;
            var widthMm = canvas.width * pxToMm / 3; // divide by capture scale
            var heightMm = canvas.height * pxToMm / 3;

            var orientation = widthMm > heightMm ? 'l' : 'p';
            var pdf = new jsPDF({
                orientation: orientation,
                unit: 'mm',
                format: [widthMm, heightMm]
            });
            pdf.addImage(imgData, 'JPEG', 0, 0, widthMm, heightMm, undefined, 'FAST');
            pdf.save((fileName || 'document') + '.pdf');
        }).catch(function (err) {
            console.error(err);
            alert('Could not generate the PDF. Please try again.');
        }).finally(function () {
            toggleBusy(triggerEl, false);
        });
    };
})(window);
