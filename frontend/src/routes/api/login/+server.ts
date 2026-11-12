import { SESSION_COOKIE, SESSION_SECONDS, sameOrigin } from '#lib/server/auth.ts';
import { BackendError, getRole } from '#lib/server/backend.ts';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ request, cookies }) => {
	if (!sameOrigin(request)) return new Response(null, { status: 403 });
	const body: unknown = await request.json().catch(() => null);
	const key = body && typeof body === 'object' && 'key' in body ? body.key : null;
	if (typeof key !== 'string' || !key || /[^\x21-\x7e]/.test(key)) {
		return Response.json({ error: 'Clave incorrecta' }, { status: 401 });
	}
	try {
		await getRole(key);
	} catch (error) {
		return Response.json(
			{ error: 'No se pudo iniciar sesión' },
			{ status: error instanceof BackendError && error.status === 401 ? 401 : 502 }
		);
	}
	cookies.set(SESSION_COOKIE, key, {
		path: '/',
		httpOnly: true,
		sameSite: 'strict',
		secure: new URL(request.headers.get('origin')!).protocol === 'https:',
		maxAge: SESSION_SECONDS
	});
	return new Response(null, { status: 204 });
};
