// PedalPulse Bike Rental - Interactive UI Helpers

document.addEventListener('DOMContentLoaded', () => {
    // 1. Image fallback handler
    document.querySelectorAll('img').forEach(img => {
        img.addEventListener('error', function() {
            if (!this.getAttribute('data-fallback-applied')) {
                this.setAttribute('data-fallback-applied', 'true');
                this.src = '/static/images/placeholder.svg';
            }
        });
    });

    // 2. Booking Live Quote Calculation
    const startInput = document.getElementById('start_time');
    const endInput = document.getElementById('end_time');
    const bikeIdInput = document.getElementById('bike_id');
    const quoteContainer = document.getElementById('booking-quote-preview');
    const durationDisplay = document.getElementById('quote-duration');
    const totalDisplay = document.getElementById('quote-total');
    const quoteErrorDisplay = document.getElementById('quote-error');
    const submitBtn = document.getElementById('btn-confirm-booking');

    if (startInput && endInput && bikeIdInput && quoteContainer) {
        // Set default minimum datetime to now
        const now = new Date();
        now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
        const isoNow = now.toISOString().slice(0, 16);
        startInput.min = isoNow;
        endInput.min = isoNow;

        // If inputs are empty, set defaults: start = 1 hour from now, end = 3 hours from now
        if (!startInput.value) {
            const defaultStart = new Date(Date.now() + 60 * 60 * 1000);
            defaultStart.setMinutes(0, 0, 0);
            const defaultEnd = new Date(defaultStart.getTime() + 2 * 60 * 60 * 1000);
            
            const toLocalISO = (d) => {
                const tzOffset = d.getTimezoneOffset() * 60000;
                return (new Date(d.getTime() - tzOffset)).toISOString().slice(0, 16);
            };

            startInput.value = toLocalISO(defaultStart);
            endInput.value = toLocalISO(defaultEnd);
            fetchLiveQuote();
        }

        startInput.addEventListener('change', () => {
            endInput.min = startInput.value;
            fetchLiveQuote();
        });

        endInput.addEventListener('change', fetchLiveQuote);

        function fetchLiveQuote() {
            const startVal = startInput.value;
            const endVal = endInput.value;
            const bikeId = bikeIdInput.value;

            if (!startVal || !endVal) {
                quoteContainer.classList.add('d-none');
                return;
            }

            const startDate = new Date(startVal);
            const endDate = new Date(endVal);

            if (endDate <= startDate) {
                quoteContainer.classList.remove('d-none');
                if (quoteErrorDisplay) {
                    quoteErrorDisplay.textContent = "End time must be after start time.";
                    quoteErrorDisplay.classList.remove('d-none');
                }
                if (submitBtn) submitBtn.disabled = true;
                return;
            }

            // Call server quote API for real availability and price calculation
            const csrfTokenElement = document.querySelector('input[name="csrf_token"]');
            const csrfToken = csrfTokenElement ? csrfTokenElement.value : '';

            fetch('/bookings/api/quote', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    bike_id: parseInt(bikeId, 10),
                    start_time: startVal,
                    end_time: endVal
                })
            })
            .then(res => res.json())
            .then(data => {
                quoteContainer.classList.remove('d-none');

                if (data.valid) {
                    if (quoteErrorDisplay) quoteErrorDisplay.classList.add('d-none');
                    if (durationDisplay) durationDisplay.textContent = `${data.duration_hours} hrs`;
                    if (totalDisplay) totalDisplay.textContent = `$${data.total_amount.toFixed(2)}`;
                    if (submitBtn) submitBtn.disabled = false;
                } else {
                    if (quoteErrorDisplay) {
                        quoteErrorDisplay.textContent = data.error || "Time window unavailable.";
                        quoteErrorDisplay.classList.remove('d-none');
                    }
                    if (durationDisplay) durationDisplay.textContent = "--";
                    if (totalDisplay) totalDisplay.textContent = "--";
                    if (submitBtn) submitBtn.disabled = true;
                }
            })
            .catch(() => {
                // Client-side fallback calculation if network / API unavailable
                const diffHours = (endDate - startDate) / (1000 * 60 * 60);
                const hourlyRate = parseFloat(bikeIdInput.dataset.hourlyPrice || "0");
                const total = Math.max(0, diffHours * hourlyRate);

                if (quoteErrorDisplay) quoteErrorDisplay.classList.add('d-none');
                if (durationDisplay) durationDisplay.textContent = `${diffHours.toFixed(2)} hrs`;
                if (totalDisplay) totalDisplay.textContent = `$${total.toFixed(2)}`;
                if (submitBtn) submitBtn.disabled = false;
            });
        }
    }
});
