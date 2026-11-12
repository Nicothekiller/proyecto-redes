import { DASHBOARD_API_KEY } from '$app/env/private';
import { createHash, createHmac, timingSafeEqual } from 'node:crypto';

export const SESSION_COOKIE = 'dashboard_session';
export const SESSION_SECONDS = 60 * 60 * 12;

export function validKey(value: string): boolean {
	const hash = (input: string) => createHash('sha256').update(input).digest();
	return Boolean(DASHBOARD_API_KEY) && timingSafeEqual(hash(value), hash(DASHBOARD_API_KEY));
}

export function sessionToken(): string {
	const expires = Math.floor(Date.now() / 1000) + SESSION_SECONDS;
	const signature = createHmac('sha256', DASHBOARD_API_KEY).update(String(expires)).digest('hex');
	return `${expires}.${signature}`;
}

export function validSession(value: string | undefined): boolean {
	if (!value || !DASHBOARD_API_KEY) return false;
	const [expires, signature, extra] = value.split('.');
	if (extra !== undefined || !/^\d+$/.test(expires) || !signature) return false;
	if (Number(expires) <= Date.now() / 1000) return false;
	const expected = createHmac('sha256', DASHBOARD_API_KEY).update(expires).digest();
	if (!/^[a-f0-9]{64}$/.test(signature)) return false;
	const actual = Buffer.from(signature, 'hex');
	return actual.length === expected.length && timingSafeEqual(actual, expected);
}
