export const SESSION_COOKIE = 'dashboard_session';
export const SESSION_SECONDS = 60 * 60 * 12;

export function sameOrigin(request: Request): boolean {
	try {
		const origin = new URL(request.headers.get('origin') ?? '');
		return (
			['http:', 'https:'].includes(origin.protocol) && origin.host === request.headers.get('host')
		);
	} catch {
		return false;
	}
}
