const DATE_FORMAT = new Intl.DateTimeFormat('es', {
	dateStyle: 'medium',
	timeStyle: 'medium',
	timeZone: 'UTC'
});

export function clampAge(seconds: number | null | undefined): number | null {
	if (seconds === null || seconds === undefined) return null;
	return Math.max(0, seconds);
}

export function formatAge(seconds: number | null | undefined): string {
	const age = clampAge(seconds);
	if (age === null) return '—';
	if (age < 1) return '<1 s';
	if (age < 60) return `${Math.round(age)} s`;
	if (age < 3600) {
		const minutes = Math.floor(age / 60);
		const rest = Math.round(age % 60);
		return `${minutes} min ${rest} s`;
	}
	const hours = Math.floor(age / 3600);
	const minutes = Math.floor((age % 3600) / 60);
	return `${hours} h ${minutes} min`;
}

export function truncatePubkey(pubkey: string): string {
	if (pubkey.length <= 12) return pubkey;
	return `${pubkey.slice(0, 6)}…${pubkey.slice(-4)}`;
}

export function formatBytes(value: number): string {
	if (value < 1024) return `${value} B`;
	const units = ['KiB', 'MiB', 'GiB', 'TiB'];
	let size = value / 1024;
	let unit = 0;
	while (size >= 1024 && unit < units.length - 1) {
		size /= 1024;
		unit += 1;
	}
	return `${size.toFixed(1)} ${units[unit]}`;
}

export function formatDelta(current: number, previous: number | undefined): string {
	if (previous === undefined) return '—';
	if (current < previous) return '0 B (reinició)';
	return formatBytes(current - previous);
}

export function formatDateTime(value: string | null | undefined): string {
	if (!value) return '—';
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) return '—';
	return `${DATE_FORMAT.format(date)} UTC`;
}

export function formatRtt(rtt: number | null | undefined): string {
	if (rtt === null || rtt === undefined) return '—';
	return `${rtt.toFixed(1)} ms`;
}

export function isStale(reportedAt: string, now: number, offlineAfterS: number): boolean {
	const time = new Date(reportedAt).getTime();
	if (Number.isNaN(time)) return true;
	return now - time > offlineAfterS * 1000;
}

export function pairKey(reporter: string, peer: string): string {
	return `${reporter}:${peer}`;
}
