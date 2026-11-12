import { SESSION_COOKIE, SESSION_SECONDS, sessionToken, validKey } from '#lib/server/auth.ts';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ request, cookies }) => {
	const origin = request.headers.get('origin');
	let url: URL;
	try {
		url = new URL(origin ?? '');
	} catch {
		return new Response(null, { status: 403 });
	}
	if (!['http:', 'https:'].includes(url.protocol) || url.host !== request.headers.get('host')) {
		return new Response(null, { status: 403 });
	}
	const body: unknown = await request.json().catch(() => null);
	const key = body && typeof body === 'object' && 'key' in body ? body.key : null;
	if (typeof key !== 'string' || !validKey(key)) {
		return Response.json({ error: 'Clave incorrecta' }, { status: 401 });
	}
	cookies.set(SESSION_COOKIE, sessionToken(), {
		path: '/',
		httpOnly: true,
		sameSite: 'strict',
		secure: url.protocol === 'https:',
		maxAge: SESSION_SECONDS
	});
	return new Response(null, { status: 204 });
};
