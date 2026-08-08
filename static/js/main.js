console.log('Tatto Mark Investment static files loaded.');

function setupMobileNav() {
	const toggle = document.getElementById('navToggle');
	const nav = document.getElementById('siteNav');
	if (!toggle || !nav) return;
	toggle.addEventListener('click', () => {
		const open = nav.classList.toggle('open');
		toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
	});
	nav.addEventListener('click', (e) => {
		if (e.target.closest('a')) {
			nav.classList.remove('open');
			toggle.setAttribute('aria-expanded', 'false');
		}
	});
	document.addEventListener('click', (e) => {
		if (!nav.contains(e.target) && !toggle.contains(e.target)) {
			nav.classList.remove('open');
			toggle.setAttribute('aria-expanded', 'false');
		}
	});
}

document.addEventListener('DOMContentLoaded', setupMobileNav);

function setupReferralShare() {
	const copyBtn = document.getElementById('copyReferral');
	const shareBtn = document.getElementById('shareReferral');
	const waBtn = document.getElementById('waShare');
	const input = document.getElementById('referralLink');
	if (!input) return;
	const link = input.value;
	if (copyBtn) {
		copyBtn.addEventListener('click', () => {
			input.select();
			try {
				document.execCommand('copy');
				copyBtn.textContent = 'Copied';
				setTimeout(() => copyBtn.textContent = 'Copy', 2000);
			} catch (e) {
				alert('Copy failed. Please select and copy manually.');
			}
		});
	}
	if (shareBtn && navigator.share) {
		shareBtn.addEventListener('click', async () => {
			try {
				await navigator.share({ title: 'Join Tatto Mark Investment', text: 'Join Tatto Mark Investment', url: link });
			} catch (err) {
				console.warn('Share failed', err);
			}
		});
	} else if (shareBtn) {
		shareBtn.style.display = 'none';
	}
	if (waBtn) {
		waBtn.href = `https://wa.me/?text=${encodeURIComponent(link)}`;
	}
}

document.addEventListener('DOMContentLoaded', setupReferralShare);

const EYE_ICON = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8Z"/><circle cx="12" cy="12" r="3"/></svg>';
const EYE_OFF_ICON = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19M6.61 6.61A18.5 18.5 0 0 0 1 12s4 8 11 8a9.26 9.26 0 0 0 5.39-1.61M14.12 14.12a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';

function setupPasswordToggles() {
	const pwdInputs = document.querySelectorAll('input[type="password"]');
	pwdInputs.forEach((input) => {
		if (input.dataset.pwtAttached) return;
		input.dataset.pwtAttached = '1';

		// Wrap the input so the eye icon can sit inside it, right-aligned.
		const wrap = document.createElement('div');
		wrap.className = 'password-field';
		input.insertAdjacentElement('beforebegin', wrap);
		wrap.appendChild(input);

		const btn = document.createElement('button');
		btn.type = 'button';
		btn.className = 'password-toggle';
		btn.setAttribute('aria-label', 'Show password');
		btn.setAttribute('aria-pressed', 'false');
		btn.innerHTML = EYE_ICON;
		btn.addEventListener('click', () => {
			const nowVisible = input.type === 'password';
			input.type = nowVisible ? 'text' : 'password';
			btn.innerHTML = nowVisible ? EYE_OFF_ICON : EYE_ICON;
			btn.setAttribute('aria-label', nowVisible ? 'Hide password' : 'Show password');
			btn.setAttribute('aria-pressed', nowVisible ? 'true' : 'false');
			input.focus();
		});
		wrap.appendChild(btn);
	});
}

document.addEventListener('DOMContentLoaded', setupPasswordToggles);
